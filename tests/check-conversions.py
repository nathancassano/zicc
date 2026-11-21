"""Check integer/binary32 conversions against rounded host reference values."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'conversions-check'
c.OUT.mkdir(parents=True, exist_ok=True)


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


rng = random.Random(65816)
inputs = sorted({0, 0x1000001, 0x1000003, 0xfffffffe, 0xffffffff} |
                {(1 << bit)+delta for bit in range(32) for delta in (-1, 0, 1)})
inputs += [rng.getrandbits(32) for _ in range(24)]
checks = []
for integer in (1, 2, 7, 31):
    for op, expected in [('+', 0.75+integer), ('-',0.75-integer),
                         ('*',0.75*integer), ('/',0.75/integer)]:
        checks.append(f'input={integer}UL;v=input;f=0.75f {op} v;p=(unsigned long *)&f;if(*p!=0x{bits(expected):08x}UL)return 3;')
for raw in inputs:
    for typename, width, signed in [('long',32,True), ('unsigned long',32,False),
                                     ('int',16,True), ('unsigned',16,False),
                                     ('signed char',8,True), ('unsigned char',8,False)]:
        integer = raw & ((1 << width)-1)
        if signed and integer & (1 << (width-1)):
            integer -= 1 << width
        checks.append(f'input=0x{raw:08x}UL;v=({typename})input;f=({typename})v;p=(unsigned long *)&f;if(*p!=0x{bits(integer):08x}UL)return 1;')
for x in [-2147483648, -16777216, -65535.75, -32768, -129.75, -128, -1.9,
          -0.999, -0.0, 0.0, 0.999, 1.9, 127.9, 128.9, 255.9, 32767.9,
          65535.9, 16777216, 2147483520, 4294967040]:
    raw = bits(x)
    rounded = struct.unpack('<f', struct.pack('<I', raw))[0]
    for typename, width, signed in [('long',32,True), ('unsigned long',32,False),
                                     ('int',16,True), ('unsigned',16,False),
                                     ('signed char',8,True), ('unsigned char',8,False)]:
        result = int(rounded)
        lo = -(1 << (width-1)) if signed else 0
        hi = (1 << (width-int(signed)))-1
        if lo <= result <= hi:
            expected = result & 0xffffffff
            checks.append(f'input=0x{raw:08x}UL;p=(unsigned long *)&f;*p=input;v=({typename})f;if(v!=0x{expected:08x}UL)return 2;')
# Split the generated checks to keep individual bank allocations bounded
source = 'volatile unsigned long input;\n'
for index in range(0, len(checks), 40):
    source += f'int test{index}(void){{unsigned long v;float f;unsigned long *p;'+'\n'.join(checks[index:index+40])+'return 0;}\n'
shift_values = [(1 + 0x6cad75 / (1 << 23)) * (1 << exponent) for exponent in range(24)]
source += 'static const unsigned long shift_inputs[]={' + ','.join(f'0x{bits(value):08x}UL' for value in shift_values) + '};\n'
source += 'static const long shift_results[]={' + ','.join(f'{int(value)}L' for value in shift_values) + '};\n'
source += '''int test_shifts(void){
    union { unsigned long raw; float value; } sample;
    for(unsigned i=0;i<24;++i){
        unsigned long raw=shift_inputs[i];
        long expected=shift_results[i];
        sample.raw=raw;if((long)sample.value!=expected)return 4;
        sample.raw=raw|0x80000000UL;if((long)sample.value!=-expected)return 5;
    }
    return 0;
}
'''
source += 'static const unsigned long small_words[]={' + ','.join(f'0x{bits(i):08x}UL' for i in range(33)) + '};\n'
source += '''int test_small_words(void){
    union { unsigned long raw; float value; } sample;
    for(unsigned i=0;i<=32;++i){
        unsigned long expected=small_words[i];
        input=i;sample.value=(unsigned)input;if(sample.raw!=expected)return 6;
        sample.value=(int)input;if(sample.raw!=expected)return 7;
        input=-(long)i;sample.value=(int)input;
        if(sample.raw!=(expected|(i ? 0x80000000UL : 0)))return 8;
    }
    return 0;
}
'''
source += 'int main(void){int r;'+''.join(f'r=test{i}();if(r)return r;' for i in range(0,len(checks),40))+'r=test_shifts();return r?r:test_small_words();}\n'
src = c.OUT/'vectors.c'
src.write_text(source)
report = {'cases': len(checks)+2*len(shift_values)+3*33, 'stages': {}}
for stage in (1, 4):
    raw = c.OUT/f'stage{stage}.raw'
    c.run(['python', ROOT/'tools/build-rom.py', src, '-o', raw, '--stage', str(stage), '--no-inline'], timeout=180)
    rom = raw.with_suffix('.sfc')
    c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
    labels = {n.removeprefix('_'): int(a, 16) for a, n in
              re.findall(r'^al (\w+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
    assert {'_sfloat16', '_ufloat16', '_sfloat32', '_ufloat32'} <= labels.keys()
    report['stages'][stage] = c.emulate(rom, labels, 0)
    print(f'PASS {report["cases"]} conversions stage {stage}', flush=True)
report['hashes'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [ROOT/'build/zicc.exe', *sorted((ROOT/'runtime/conversions').glob('*.s')), ROOT/'src/codegen/codegen.inc']}
literal_source = '''
int folded(void) {
    signed char a=-128.75f;
    unsigned char b=255.75f;
    int c=-32768.75f;
    unsigned d=65535.75f;
    long e=-2147483648.0f;
    unsigned long f=4294967040.0f;
    return a==-128 && b==255 && c==-32768 && d==65535u &&
           e==(-2147483647L-1) && f==4294967040UL && (unsigned)-0.75f==0;
}
int main(void) {return !folded();}
'''
path, rom, labels = c.compile_case('literal_conversions', literal_source)
assert '__fix32' not in path.with_suffix('.s').read_text()
c.emulate(rom, labels, 0)
(c.OUT/'results.json').write_text(json.dumps(report, indent=2)+'\n')
