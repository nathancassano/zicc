"""Reuse an MSVC test program when its compiler, build options and header contents match."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import run_cache

ROOT=Path(__file__).resolve().parents[1]

def prepare(command,cwd):
    args=list(map(str,command))
    indexes=[i for i,a in enumerate(args) if Path(a).name.lower()=='msvc.cmd']
    if not indexes or os.environ.get('ZICC_HOST_CACHE','1')=='0':return None
    start=indexes[0]+1
    flags=args[start:]
    sources=[Path(a) if Path(a).is_absolute() else Path(cwd)/a for a in flags if a.lower().endswith(('.c','.cpp')) and Path(a).is_file()]
    targets=[a[3:] for a in flags if a.lower().startswith('/fe')]
    # Keep multi-source and unusual invocations live; only cache successful link products
    if len(sources)!=1 or len(targets)!=1:return None
    compiler=shutil.which('cl.exe')
    if not compiler:return None
    source=sources[0].resolve();target=Path(targets[0])
    if not target.is_absolute():target=Path(cwd)/target
    normalized=[a for a in flags if not a.lower().startswith(('/fe','/fo','/implib:'))]
    identity=dict(source=str(source),source_hash=hashlib.sha256(source.read_bytes()).hexdigest(),
        compiler=hashlib.sha256(Path(compiler).read_bytes()).hexdigest(),
        toolchain_version=os.environ.get('VCToolsVersion',''),
        wrapper=hashlib.sha256((ROOT/'tools/msvc.cmd').read_bytes()).hexdigest(),flags=normalized,
        cwd=str(cwd),include=os.environ.get('INCLUDE',''),cl=os.environ.get('CL',''),
        underscore_cl=os.environ.get('_CL_',''),lib=os.environ.get('LIB',''))
    digest=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    folder=ROOT/'build/host-cache'/digest
    try:
        metadata=json.loads((folder/'metadata.json').read_text())
        valid=all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==value for path,value in metadata['headers'].items())
        if valid:
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(folder/'binary',target)
            record('hit',source)
            return dict(hit=subprocess.CompletedProcess(args,0,metadata['stdout'],metadata['stderr']))
    except (OSError,ValueError,KeyError):pass
    record('miss',source)
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,path=tempfile.mkstemp(prefix='host-deps-',suffix='.json',dir=target.parent);os.close(fd)
    # /sourceDependencies must precede /link, otherwise link.exe consumes it
    insert=next((i for i,a in enumerate(args) if a.lower()=='/link'),len(args))
    args[insert:insert]=['/sourceDependencies',path]
    return dict(command=args,dependency=Path(path),folder=folder,target=target)

def record(kind,source):
    run_cache.record(f'host-{kind}', source.name)

def store(plan,result):
    try:
        if result.returncode:return
        deps=json.loads(plan['dependency'].read_text(encoding='utf-8-sig'))['Data']['Includes']
        headers={str(Path(p).resolve()):hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in deps}
        folder=plan['folder'];folder.parent.mkdir(parents=True,exist_ok=True)
        temporary=Path(tempfile.mkdtemp(dir=folder.parent))
        shutil.copyfile(plan['target'],temporary/'binary')
        (temporary/'metadata.json').write_text(json.dumps(dict(headers=headers,stdout=result.stdout,stderr=result.stderr)))
        try:temporary.rename(folder)
        except FileExistsError:
            # A source with changed transitive headers gets a new dependency record
            # Atomic file publication also tolerates two concurrent identical builds
            for name in ('binary','metadata.json'):os.replace(temporary/name,folder/name)
            temporary.rmdir()
    finally:plan['dependency'].unlink(missing_ok=True)
