"""Content-addressed cache of deterministic emulator runs.

An emulator run is fully determined by the emulator build, its configuration,
the ROM bytes and the Lua script text (RAM power-on state is fixed to zeros), so
a run whose inputs are byte-identical to an earlier successful run returns that
run's recorded output instead of emulating again. The calling test still builds
its ROM and evaluates every assertion on the returned output: only emulation of
an unchanged ROM is skipped.

Scripts that read or write files, use time or randomness, or take savestates are never cached. PNG screenshots encoded in stdout are retained with the log. Only runs that completed as the caller expected
are stored, never failures or timeouts.

ZICC_RUN_CACHE=0 disables the cache (make check CHECK_NO_CACHE=1).
ZICC_RUN_CACHE_DIR overrides build/run-cache.
ZICC_RUN_CACHE_LOG names a file that receives one 'hit'/'miss'/'bypass' line
per run, so verification evidence records which results were reused.
The verification runner uses one SQLite file for counts across child processes.
"""
import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
# Bump to invalidate every entry when the key or stored format changes
VERSION = 1
UNCACHEABLE = re.compile(r"\b(?:io\s*\.|os\s*\.|math\s*\.\s*random\b|dofile\b|require\b|loadfile\b|\w*Savestate\w*)")
_hashes = {}
_lock = threading.Lock()


def enabled():
    return os.environ.get('ZICC_RUN_CACHE', '1') != '0'


def directory():
    return Path(os.environ.get('ZICC_RUN_CACHE_DIR', ROOT / 'build/run-cache'))


def file_sha256(path):
    path = Path(path).resolve()
    stat = path.stat()
    marker = (str(path), stat.st_mtime_ns, stat.st_size)
    with _lock:
        if marker not in _hashes:
            _hashes[marker] = hashlib.sha256(path.read_bytes()).hexdigest()
        return _hashes[marker]


def cacheable_script(text):
    # Prompt screenshots are returned as PNG hex in the cached stdout itself;
    # the caller recreates and validates every image on both hits and misses
    if 'takeScreenshot' in text and not ("print('PNG '" in text and "png:gsub" in text):return False
    return UNCACHEABLE.search(text) is None


def key(**parts):
    return hashlib.sha256(json.dumps(dict(parts, version=VERSION), sort_keys=True).encode()).hexdigest()


def record(kind, label, digest=''):
    database = os.environ.get('ZICC_CACHE_EVENT_DB')
    if database:
        job = os.environ['ZICC_CACHE_EVENT_JOB']
        with closing(sqlite3.connect(database, timeout=60)) as connection, connection:
            connection.execute(
                'INSERT INTO counts VALUES (?, ?, 1) '
                'ON CONFLICT(job, kind) DO UPDATE SET count = count + 1',
                (job, kind))
            if os.environ.get('ZICC_CACHE_TRACE') == '1':
                connection.execute('INSERT INTO events VALUES (?, ?, ?, ?)',
                                   (job, kind, digest, label))
        return
    log = os.environ.get('ZICC_RUN_CACHE_LOG')
    if log:
        with _lock, open(log, 'a', encoding='utf-8') as stream:
            stream.write(f'{kind} {digest[:16]} {label}\n')


def get(digest, label):
    path = directory() / digest[:2] / (digest + '.json')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        record('miss', label, digest)
        return None
    record('hit', label, digest)
    return value


def put(digest, value):
    folder = directory() / digest[:2]
    folder.mkdir(parents=True, exist_ok=True)
    # Atomic: concurrent workers may store the same entry
    handle, temporary = tempfile.mkstemp(dir=folder, suffix='.tmp')
    with os.fdopen(handle, 'w', encoding='utf-8') as stream:
        json.dump(value, stream)
    os.replace(temporary, folder / (digest + '.json'))
