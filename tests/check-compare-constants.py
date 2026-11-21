"""Signed word comparisons against integer constants (zero, positive, negative,
both extremes) for every relational operator, over boundary inputs. Each
comparison is a separate function so the constant reaches the immediate path,
and the result is used both as a branch and as a value. The SNES ROM and an
MSVC host build must produce the same checksum."""
import importlib.util
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'compare-constants-check'
spec = importlib.util.spec_from_file_location('checks', ROOT/'tests/check-strength.py')
checks = importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)
checks.OUT = OUT
support = checks.support
COMPILER = Path(os.environ.get('ZICC_COMPILER', ROOT/'build/zicc.exe'))
CONSTANTS = [0, 1, 2, 100, 32766, 32767, -1, -2, -100, -32767, -32768]
INPUTS = [0, 1, -1, 2, -2, 99, 100, 101, -99, -100, -101, 32765, 32766, 32767, -32766, -32767, -32768, 12345, -12345]
OPS = {'lt': '<', 'le': '<=', 'gt': '>', 'ge': '>='}


def source():
    lines = ['int inputs[%d]={%s};' % (len(INPUTS), ','.join(f'({v})' if v != -32768 else '(-32767-1)' for v in INPUTS))]
    calls = []
    for c in CONSTANTS:
        lit = f'({c})' if c != -32768 else '(-32767-1)'
        tag = str(c).replace('-', 'm')
        for name, op in OPS.items():
            lines.append(f'int b_{name}_{tag}(int x){{if(x{op}{lit})return 3;return 5;}}')
            lines.append(f'int v_{name}_{tag}(int x){{int y=x+0;while(y{op}{lit})return 7;return 11;}}')
            calls.append(f'b_{name}_{tag}(x)')
            calls.append(f'v_{name}_{tag}(x)')
    lines.append('unsigned int check(void){unsigned int h=0;int i;for(i=0;i<%d;i++){int x=inputs[i];' % len(INPUTS))
    for call in calls:
        lines.append(f' h=h*31u+(unsigned int){call};')
    lines.append('}return h;}')
    return '\n'.join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    body = source()
    host = OUT/'host.c'
    host.write_text(body + '\n#include <stdio.h>\nint main(void){printf("%u\\n",check()&0xFFFFu);return 0;}\n', encoding='ascii')
    exe = host.with_suffix('.exe')
    support.run([ROOT/'tools/msvc.cmd', '/nologo', '/std:c17', '/O2', '/Fo' + str(host.with_suffix('.obj')), '/Fe' + str(exe), host])
    expected = int(subprocess.run([str(exe)], capture_output=True, text=True, timeout=5).stdout)
    result = checks.build('compare_constants', body + f'\nint main(void){{return check()!={expected}u;}}\n', True, compiler=COMPILER)
    print(f'PASS compare constants: {len(CONSTANTS)} constants x {len(OPS)} operators x 2 forms x {len(INPUTS)} inputs, '
          f'checksum {expected}, {result["master_clocks"]} clocks')


if __name__ == '__main__':
    main()
