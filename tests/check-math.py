"""Check 32-bit floating-point math, including special values and calls across banks."""
import os
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'math-check'
c.OUT.mkdir(parents=True, exist_ok=True)


def bits(value):
    try:
        return struct.unpack('<I', struct.pack('<f', value))[0]
    except OverflowError:
        return 0xff800000 if value < 0 else 0x7f800000


def value(raw):
    return struct.unpack('<f', struct.pack('<I', raw))[0]


def reference(name, raw):
    x = value(raw)
    if math.isnan(x):
        return 0x7fc00000
    if name == 'log' and x == 0:
        return 0xff800000
    try:
        return bits(getattr(math, name)(x))
    except ValueError:
        return 0x7fc00000
    except OverflowError:
        return 0x7f800000


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--stage', type=int, action='append')
parser.add_argument('--quick', action='store_true')
args = parser.parse_args()
rng = random.Random(65816)
common = [0, 0x80000000, 1, 0x80000001, 0x007fffff, 0x00800000,
          0x7f7fffff, 0xff7fffff, 0x7f800000, 0xff800000, 0x7fc12345,
          *[bits(x) for x in (0.1, -0.1, 0.5, -0.5, 1, -1, 2, -2, 3, -3,
                              math.pi/4, math.pi/2, math.pi, 10, -10,
                              88.7, 88.72, 88.73, -103.97, -104, 1e10, 1e30)]]
if not args.quick:
    common += [rng.getrandbits(32) for _ in range(192)]
    common += [1 << bit for bit in range(23)]
    common += [0x00800000 + delta for delta in (-2, -1, 1, 2)]
cases = [(name, raw, reference(name, raw))
         for name in ('sqrt', 'log', 'exp', 'atan', 'sin', 'cos') for raw in common]
source = '#include <math.h>\nvolatile unsigned long input;\nvolatile unsigned long result['+str(len(cases))+'];\n'
source += 'const unsigned long vectors[]={'+','.join(f'0x{x:08x}UL' for x in common)+'};\n'
source += 'int main(void){float x,y;unsigned long *p;unsigned i,j;\n'
for group, name in enumerate(('sqrt', 'log', 'exp', 'atan', 'sin', 'cos')):
    source += f'for(i=0;i<{len(common)};++i){{input=vectors[i];p=(unsigned long *)&x;*p=input;y={name}(x);p=(unsigned long *)&y;result[i+{group*len(common)}]=*p;}}\n'
source += 'return 0;}\n'
src = c.OUT/'vectors.c'
src.write_text(source)
report = {'cases': len(cases), 'stages': {}}
for stage in args.stage or (1, 4):
    raw = c.OUT/f'stage{stage}.raw'
    c.run(['python', ROOT/'tools/build-rom.py', src, '-o', raw, '--stage', str(stage)], timeout=180)
    rom = raw.with_suffix('.sfc')
    c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
    labels = {n.removeprefix('_'): int(a, 16) for a, n in
              re.findall(r'^al (\w+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
    address = labels['result']
    lua = f'''emu.addMemoryCallback(function()
if done then return end
for i=0,{len(cases)-1} do
 local v=0
 for j=0,3 do v=v | (emu.read({address}+i*4+j,emu.memType.snesMemory,false) << (j*8)) end
 print(string.format('MATH %d %08x',i,v))
end
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})\n'''
    output = c.emulate(rom, labels, 0, extra_checks=lua, timeout_seconds=60)
    actual = {int(i): int(v, 16) for i, v in re.findall(r'MATH (\d+) ([0-9a-f]+)', output)}
    assert len(actual) == len(cases), (len(actual), len(cases), output)
    maximum = {}
    failures = []
    for index, (name, raw, expected) in enumerate(cases):
        got = actual[index]
        if expected & 0x7fffffff > 0x7f800000:
            error = 0 if got & 0x7fffffff > 0x7f800000 else 0xffffffff
        elif expected & 0x7fffffff in (0, 0x7f800000):
            error = 0 if got == expected else 0xffffffff
        else:
            error = abs(got-expected) if got >> 31 == expected >> 31 else 0xffffffff
        maximum[name] = max(maximum.get(name, 0), error)
        if error > (0 if name == 'sqrt' else 4):
            failures.append(dict(function=name, input=f'{raw:08x}', expected=f'{expected:08x}',
                                 actual=f'{got:08x}', ulp=error))
    report['stages'][stage] = dict(maximum_ulp=maximum, failures=failures, rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest())
    print('stage', stage, maximum, 'failures', len(failures), flush=True)
    (c.OUT/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    assert not failures, failures[:20]
report['hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [ROOT/'build/zicc.exe', *sorted((ROOT/'runtime/math').glob('*.s')), ROOT/'runtime/fabs.s', ROOT/'runtime/fabsf.s', ROOT/'runtime/ldexp.s', ROOT/'runtime/ldexpf.s', ROOT/'runtime/math-two-over-pi.inc',
                              *sorted((ROOT/'runtime/ieee32').glob('*.s')),
                              *sorted((ROOT/'runtime/ieee64').glob('*.s')),
                              ROOT/'runtime/ieee64/trig-two-over-pi.inc', ROOT/'include/math.h']}
(c.OUT/'results.json').write_text(json.dumps(report, indent=2)+'\n')

def check_exact_rom(name, source, binary64):
    src = c.OUT/f'{name}.c'
    src.write_text(source)
    for stage in args.stage or (1, 4):
        raw = c.OUT/f'{name}-stage{stage}.raw'
        c.run(['python', ROOT/'tools/build-rom.py', src, '-o', raw, '--stage', str(stage)],
              timeout=180, binary64=binary64)
        rom = raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
        labels = {n.removeprefix('_'): int(a, 16) for a, n in
                  re.findall(r'^al (\w+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        c.emulate(rom, labels, 0)
        print(f'{name} stage {stage}: pass', flush=True)


# Volatile inputs keep equal operands in the runtime addition path
add_vectors = [(raw, raw) for raw in (0, 0x80000000, 1, 0x0000ffff, 0x00400000,
                                     0x807fffff, 0x00800000,
                                     0x3fc01234, 0xbfc01234, 0x7effffff, 0x7f7fffff,
                                     0x7f800000, 0x7fc12345)]
add_vectors += [(0x3f800000, 0x3f800003), (0x3fc01234, 0xbfc01234)]
add_checks = []
for index, (a, b) in enumerate(add_vectors, 1):
    expected = 0x7fc00000 if math.isnan(value(a)) else bits(value(a)+value(b))
    add_checks.append(f'a.bits=0x{a:08x}UL; b.bits=0x{b:08x}UL; result.real=a.real+b.real; '
                      f'if(result.bits!=0x{expected:08x}UL)return {index};\n')
check_exact_rom('binary32-add', 'volatile union {float real; unsigned long bits;} a,b,result;\n'
                'int main(void){\n'+''.join(add_checks)+'return 0;}\n', False)

# Exercise actual library calls with all result bits observable
check_exact_rom('elementary-abi32', r'''
double sqrt(double),log(double),exp(double),atan(double),sin(double),cos(double);
double (*volatile indirect)(double)=sqrt;
volatile double zero=0.0,one=1.0,four=4.0;
int main(void){
    if(sqrt(four)!=2.0||indirect(four)!=2.0)return 1;
    return log(one)!=0.0||exp(zero)!=1.0||atan(zero)!=0.0||
           sin(zero)!=0.0||cos(zero)!=1.0;
}
''', False)
vectors32 = [0, 0x80000000, 0x80000001, 0xbf800000, 0xff800000, 0xff812345, 0x7fc12345]
vectors64 = [0, 0x8000000000000000, 0x8000000000000001, 0xbff0000000000000,
             0xfff0000000000000, 0xfff0123456789abc, 0x7ff8123456789abc]
for function, binary64 in [('fabs', False), ('fabs', True), ('fabsf', False), ('fabsf', True)]:
    wide = function == 'fabs' and binary64
    width, integer, suffix, vectors = ((64, 'unsigned long long', 'ULL', vectors64) if wide else
                                        (32, 'unsigned long', 'UL', vectors32))
    real = 'float' if function == 'fabsf' else 'double'
    abi = 64 if binary64 else 32
    checks = ''.join(
        f'input.bits=0x{raw:x}{suffix}; result.real={function}(input.real); '
        f'if(result.bits!=0x{raw & ((1 << (width-1))-1):x}{suffix}) return {index};\n'
        for index, raw in enumerate(vectors, 1)
    )
    check_exact_rom(f'{function}-abi{abi}', '#include <math.h>\n'
                    f'volatile union {{{real} real; {integer} bits;}} input, result;\n'
                    'int main(void){\n' + checks + 'return 0;}\n', binary64)

for function, binary64 in [('ldexp', False), ('ldexp', True), ('ldexpf', False), ('ldexpf', True)]:
    wide = function == 'ldexp' and binary64
    real = 'float' if function == 'ldexpf' else 'double'
    width, fraction, bias, integer, suffix = ((64, 52, 1023, 'unsigned long long', 'ULL') if wide else
                                               (32, 23, 127, 'unsigned long', 'UL'))
    sign = 1 << (width-1)
    tiny = 1 << fraction
    one = bias << fraction
    inf = ((bias << 1)+1) << fraction
    quiet = 1 << (fraction-1)
    # Input bits, power, expected bits, errno, flags, rounding mode
    vectors = [
        (0, 32767, 0, 0, 0, 0),
        (sign, -32768, sign, 0, 0, 0),
        (inf, -32768, inf, 0, 0, 0),
        (sign|inf|quiet|5, 32767, sign|inf|quiet|5, 0, 0, 0),
        (inf|7, 0, inf|quiet|7, 0, 1, 0),
        (one|5, -1, (one-tiny)|5, 0, 0, 0),
        (sign|one, 2, sign|(one+2*tiny), 0, 0, 0),
        (1, fraction, tiny, 0, 0, 0),
        (tiny, -fraction, 1, 0, 0, 0),
        (tiny|1, -1, tiny//2, 34, 24, 0),
        (tiny|3, -1, tiny//2+2, 34, 24, 0),
        (2*tiny-1, -1, tiny, 0, 16, 0),
        (tiny, -fraction-1, 0, 34, 24, 0),
        (sign|tiny|1, -fraction-1, sign|1, 34, 24, 0),
        (one, 32767, inf, 34, 20, 0),
        (sign|one, -32768, sign, 34, 24, 0),
    ]
    if wide:
        vectors += [
            (sign|one, -32768, sign|1, 34, 24, 1),
            (one, -32768, 1, 34, 24, 2),
            (one, 32767, inf-1, 34, 20, 1),
            (sign|one, 32767, sign|inf, 34, 20, 1),
            (sign|one, 32767, sign|(inf-1), 34, 20, 2),
            (tiny|3, -1, tiny//2+1, 34, 24, 3),
        ]
    checks = []
    for index, (raw, shift, expected, error, flags, mode) in enumerate(vectors, 1):
        if wide:
            checks.append(f'fesetround({mode}); feclearexcept(FE_ALL_EXCEPT);')
        checks.append(f'errno=0; input.bits=0x{raw:x}{suffix}; exponent={shift}; '
                      f'result.real={function}(input.real,exponent); '
                      f'if(result.bits!=0x{expected:x}{suffix} || errno!={error}) return {index};')
        if wide:
            checks.append(f'if(fetestexcept(FE_ALL_EXCEPT)!={flags}) return {index+100};')
    check_exact_rom(f'{function}-abi{64 if binary64 else 32}',
                    '#include <math.h>\n#include <errno.h>\n#include <fenv.h>\n'
                    f'volatile union {{{real} real; {integer} bits;}} input, result;\n'
                    'volatile int exponent;\nint main(void){\n' +
                    '\n'.join(checks) + '\nreturn 0;}\n', binary64)
