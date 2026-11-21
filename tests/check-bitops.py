"""Check both the folded bit builtins and their callable 65816 implementations."""
import os
import importlib.util
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler', ROOT / 'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'bitops-check'
c.OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(65816)

constant = c.OUT / 'constants.c'
constant.write_text('''
enum { first = __builtin_ffsll(1LL << 53),
       zeros = __builtin_clzl(1UL << 19),
       count = __builtin_popcountll((1ULL << 63) + 3ULL),
       odd = __builtin_parityl(~1UL),
       empty = __builtin_ffs(0), negative = __builtin_ffs(-32768L) };
int main(void) {
    return first != 54 || zeros != 12 || count != 3 || odd != 1 ||
           empty != 0 || negative != 16;
}
''')
asm = constant.with_suffix('.s')
c.run([ROOT / 'build/zicc.exe', constant, '-o', asm])
assert '__builtin_' not in asm.read_text()

parts = ['#include <bitops.h>']
checks = []
total = 0
for width, unsigned, signed, suffix, fn_suffix in (
    (16, 'unsigned', 'int', 'U', ''),
    (32, 'unsigned long', 'long', 'UL', 'l'),
    (64, 'unsigned long long', 'long long', 'ULL', 'll'),
):
    values = [0, (1 << width)-1, *[1 << bit for bit in range(width)]]
    values += [rng.getrandbits(width) for _ in range(32)]
    total += len(values)
    rows = []
    for value in values:
        first = (value & -value).bit_length()
        zeros = width - value.bit_length()
        rows.append(f'{{0x{value:x}{suffix},{first},{zeros},{value.bit_count()}}}')
    parts.append(f'''
struct Vector{width} {{ {unsigned} value; int first, zeros, count; }};
static const struct Vector{width} vectors{width}[] = {{{','.join(rows)}}};
static volatile {unsigned} input{width};
int (*volatile ffs{width}_ptr)({signed}) = ffs{fn_suffix};
int (*volatile builtin{width}_ptr)({signed}) = __builtin_ffs{fn_suffix};
''')
    checks.append(f'''
    for (i=0; i<{len(values)}; ++i) {{
        int first=vectors{width}[i].first, zeros=vectors{width}[i].zeros, count=vectors{width}[i].count;
        input{width}=vectors{width}[i].value;
        if (__builtin_ffs{fn_suffix}(input{width})!=first || ffs{width}_ptr(input{width})!=first ||
            builtin{width}_ptr(input{width})!=first) return {width+1};
        if (input{width} && __builtin_clz{fn_suffix}(input{width})!=zeros) return {width+2};
        if (clz{fn_suffix}(input{width})!=zeros) return {width+3};
        if (__builtin_popcount{fn_suffix}(input{width})!=count || popcount{fn_suffix}(input{width})!=count) return {width+4};
        if (__builtin_parity{fn_suffix}(input{width})!=(count&1) || parity{fn_suffix}(input{width})!=(count&1)) return {width+5};
    }}
''')
source = c.OUT / 'vectors.c'
source.write_text('\n'.join(parts) + '\nint main(void) { unsigned i;\n' + '\n'.join(checks) + 'return 0; }\n')

for case, stage in [(constant, 1), (source, 1), (source, 4)]:
    raw = c.OUT / f'{case.stem}-stage{stage}.raw'
    c.run([sys.executable, ROOT / 'tools/build-rom.py', case, '--stage', str(stage), '-o', raw], timeout=180)
    rom = raw.with_suffix('.sfc')
    c.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
    labels = {name.removeprefix('_'): int(address, 16) for address, name in
              re.findall(r'^al (\w+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
    c.emulate(rom, labels, 0)
print(f'PASS constant folding and {total} runtime vectors in near and long ROM call layouts')
