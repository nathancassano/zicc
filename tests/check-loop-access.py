"""Build the standalone loop access sample and check its result in Mesen."""
import os
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
if support.OUT == Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'compiler-check':
    support.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'loop-access-check'


def main():
    raw = support.OUT / 'loop_access.raw'
    rom = raw.with_suffix('.sfc')
    support.run([sys.executable, ROOT / 'tools/build-rom.py', ROOT / 'samples/loop_access.c',
                 '-o', raw], timeout=90, binary64=False)
    support.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
    labels = {name.removeprefix('_'): int(address, 16)
              for address, name in re.findall(r'^al (\w+) \.(\S+)$',
                                              raw.with_suffix('.labels').read_text(), re.M)}
    support.emulate(rom, labels, expected_return=0)
    allocation = json.loads(raw.with_suffix('.allocation.json').read_text())
    assembly = (Path(allocation['evidence']) / f"stage{allocation['stage']}" / '0_loop_access.s').read_text()
    # These kernels run against all four storage sources. Check each lowering
    # separately so a fast loop cannot hide a fallback elsewhere in the sample
    byte_body = assembly.split('_loop_access__check_bytes:\n', 1)[1].split('__size_loop_access__check_bytes', 1)[0]
    word_body = assembly.split('_loop_access__check_words:\n', 1)[1].split('__size_loop_access__check_words', 1)[0]
    assert '; unrolled indexed far doubling sum: 3 elements' in byte_body
    assert '; unrolled far pointer doubling sum: 3 elements' in byte_body
    assert word_body.count('; far load through updated cursor') == 3
    print('PASS: byte and word loop access in ROM, static RAM, stack and heap')


if __name__ == '__main__':
    main()
