"""Front-end integer constant folding: folded literals equal run-time results.

Each vector evaluates one operator twice: on literal operands, which the
front end folds, and on volatile copies, which execute at run time. Both are
stored through a volatile and compared with a host model of the target's C
semantics (16-bit int, 32-bit long). Undefined operations are excluded; the
folder leaves them to run time and does not diagnose them.
"""
import os
import importlib.util
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'constant-folding-check'
SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT

TYPES = {'signed char': (8, True), 'unsigned char': (8, False), 'int': (16, True), 'unsigned int': (16, False), 'long': (32, True), 'unsigned long': (32, False)}
NAMES = {'signed char': 'sc', 'unsigned char': 'uc', 'int': 'i', 'unsigned int': 'u', 'long': 'l', 'unsigned long': 'ul'}
VALUES = {
    'signed char': (-128, -1, 0, 1, 5, 127),
    'unsigned char': (0, 1, 7, 128, 255),
    'int': (-32768, -32767, -7, -1, 0, 1, 2, 7, 255, 256, 32767),
    'unsigned int': (0, 1, 3, 255, 256, 0x7FFF, 0x8000, 0xFFFE, 0xFFFF),
    'long': (-2147483648, -65536, -7, -1, 0, 1, 7, 65535, 65536, 2147483647),
    'unsigned long': (0, 1, 7, 0xFFFF, 0x10000, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF),
}
OPS = ('+', '-', '*', '/', '%', '&', '|', '^', '<<', '>>', '==', '!=', '<', '>', '<=', '>=', '&&', '||')


def norm(value, name):
    bits, signed = TYPES[name]
    value &= (1 << bits) - 1
    return value - (1 << bits) if signed and value >= 1 << (bits - 1) else value


def promote(name):
    return 'int' if 'char' in name else name


def common(a, b):
    a, b = promote(a), promote(b)
    if 'unsigned long' in (a, b):
        return 'unsigned long'
    if 'long' in (a, b):
        return 'long'
    return 'unsigned int' if 'unsigned int' in (a, b) else 'int'


def evaluate(op, ta, a, tb, b):
    """Return (result type, value) or None for undefined behaviour."""
    if op in ('&&', '||'):
        return 'int', int((a != 0 and b != 0) if op == '&&' else (a != 0 or b != 0))
    kind = promote(ta) if op in ('<<', '>>') else common(ta, tb)
    bits, signed = TYPES[kind]
    x = norm(a, kind)
    if op in ('<<', '>>'):
        count = b
        if count < 0 or count >= bits:
            return None
        if op == '>>':
            return kind, norm(x >> count, kind)
        if signed and x < 0:
            return None
        z = x << count
    else:
        y = norm(b, kind)
        if op in ('==', '!=', '<', '>', '<=', '>='):
            return 'int', int({'==': x == y, '!=': x != y, '<': x < y, '>': x > y, '<=': x <= y, '>=': x >= y}[op])
        if op in ('&', '|', '^'):
            mask = (1 << bits) - 1
            return kind, norm({'&': (x & mask) & (y & mask), '|': (x & mask) | (y & mask),
                               '^': (x & mask) ^ (y & mask)}[op], kind)
        if op in ('/', '%'):
            if y == 0 or (signed and x == -(1 << (bits - 1)) and y == -1):
                return None
            q = abs(x) // abs(y) * (-1 if (x < 0) != (y < 0) else 1)
            z = q if op == '/' else x - q * y
        else:
            z = {'+': x + y, '-': x - y, '*': x * y}[op]
    if signed and not -(1 << (bits - 1)) <= z < 1 << (bits - 1):
        return None
    return kind, norm(z, kind)


def literal(name, value):
    return f'(({name})0x{value & 0xFFFFFFFF:X}UL)'


def vectors():
    rng = random.Random(1997)
    cases = []
    names = list(TYPES)
    for op in OPS:
        for ta in names:
            for tb in names:
                pairs = [(a, b) for a in VALUES[ta] for b in VALUES[tb]]
                if op in ('<<', '>>'):
                    pairs = [(a, b) for a in VALUES[ta] for b in (0, 1, 7, 15, 16, 31)
                             if b in VALUES[tb] or tb in ('int', 'long')]
                rng.shuffle(pairs)
                taken = 0
                for a, b in pairs:
                    result = evaluate(op, ta, a, tb, b)
                    if result is None:
                        continue
                    cases.append((op, ta, a, tb, b) + result)
                    taken += 1
                    if taken == (6 if ta == tb else 2):
                        break
    return cases


def source(cases):
    lines = [f'volatile {t} va_{n}, vb_{n}, vr_{n};' for t, n in NAMES.items()]
    chunk = 40
    for start in range(0, len(cases), chunk):
        lines.append(f'int chunk{start // chunk}(void){{')
        for index, (op, ta, a, tb, b, kind, value) in enumerate(cases[start:start + chunk], start):
            la, lb, lr = literal(ta, a), literal(tb, b), literal(kind, value)
            r = 'vr_' + NAMES[kind]
            code = 2 * index + 1
            lines.append(f' va_{NAMES[ta]}={la};vb_{NAMES[tb]}={lb};'
                         f'{r}=va_{NAMES[ta]} {op} vb_{NAMES[tb]};if({r}!={lr})return {code};')
            lines.append(f' {r}={la} {op} {lb};if({r}!={lr})return {code + 1};')
        lines.append(' return 0;}')
    count = (len(cases) + chunk - 1) // chunk
    lines.append('int pure(void){return (-32767-1)/(1+1)+(int)(3UL<<4)+(5>3&&2)+~(0x0F0F^0x00FF);}')
    lines.append('long pure_long(void){return -2147483647L-1L+(long)(65535U*1U)+(0xFFFFFFFFUL>>4);}')
    lines.append('int main(void){int r;')
    lines += [f' if((r=chunk{i}()))return r;' for i in range(count)]
    lines.append(' if(pure()!=-16384+48+1+~(0x0F0F^0x00FF))return 32001;')
    lines.append(' if(pure_long()!=(long)(-2147483647L-1L+65535L+0x0FFFFFFFL))return 32002;')
    lines.append(' return 0;}')
    return '\n'.join(lines) + '\n'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    _, rom, labels = support.compile_case('unary_signed_literals', '''
int main(void) {
    return ~(-1L >> 7) != 0L || -(-1) != 1 || +(-1L) != -1L;
}
''')
    support.emulate(rom, labels, 0)
    cases = vectors()
    assert len({c[0] for c in cases}) == len(OPS) and 2 * len(cases) < 32000, len(cases)
    batch = 200  # one 32 KB image holds about 250 vectors
    for first in range(0, len(cases), batch):
        name = f'folding{first // batch}'
        _, rom, labels = support.compile_case(name, source(cases[first:first + batch]), extra_objects=[
            ROOT / 'build' / (n + '.o') for n in ('arithmetic', 'integers', 'ieee_engine')])
        support.emulate(rom, labels, 0)
    assembly = (OUT / 'folding0.s').read_text()
    for name in ('pure', 'pure_long'):
        body = assembly.split('_' + name + ':\n', 1)[1].split('__size_' + name, 1)[0]
        instructions = [line.split()[0] for line in body.splitlines()
                        if line.startswith('    ') and not line.lstrip().startswith(';')]
        assert set(instructions) <= {'lda', 'ldx', 'rts'} and not re.search(r'__\w+(?:32|16)', body), body
    print(f'PASS: {len(cases)} folded/run-time operator vectors over {len(OPS)} operators; constant-only bodies')


if __name__ == '__main__':
    main()
