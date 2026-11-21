"""Run conversions between integers and 32-bit floating-point values on the SNES."""
import os
import importlib.util
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'int64-float-check'
c.OUT.mkdir(parents=True, exist_ok=True)
MASK = (1 << 64)-1
rng = random.Random(0x64f10a7)
VALUES = [0, 1, 2, (1<<24)-1, 1<<24, (1<<24)+1, (1<<24)+3,
          (1<<32)-1, 1<<32, (1<<62)+(1<<38)-1, (1<<62)+(1<<38),
          (1<<62)+(1<<38)+1, (1<<63)-1, 1<<63,
          (1<<63)+(1<<39)-1, (1<<63)+(1<<39), (1<<63)+(1<<39)+1, MASK]
VALUES += [rng.getrandbits(64) for _ in range(100)]

obj = c.OUT/'fromint64-to-float.o'
archive = c.OUT/'conversion.a'
c.run([c.CC65/'ca65.exe','--cpu','65816','-o',obj,ROOT/'runtime/ieee64/fromint64-to-float.s'])
archive.unlink(missing_ok=True)
c.run([c.CC65/'ar65.exe','a',archive,obj])
_, baseline, _ = c.compile_case('baseline','int main(void){return 0;}')
_, linked, labels = c.compile_case('baseline-archive','int main(void){return 0;}',extra_objects=[archive])
assert baseline.read_bytes() == linked.read_bytes()
assert '_sfloat32_64' not in labels and '_ufloat32_64' not in labels

def reference(raw, signed):
    negative = signed and bool(raw & (1<<63))
    n = ((-raw)&MASK) if negative else raw
    if not n:
        return 0
    exponent = n.bit_length()-1
    shift = max(0, exponent-23)
    if shift:
        top, rest = divmod(n, 1<<shift)
        half = 1<<(shift-1)
        if rest > half or (rest == half and top & 1):
            top += 1
        if top == 1<<24:
            top >>= 1
            exponent += 1
    else:
        top = n << (23-exponent)
    return (int(negative)<<31) | ((exponent+127)<<23) | (top&0x7fffff)

source = c.OUT/'main.c'
source.write_text('int conversion_probe(void);int main(void){return conversion_probe();}\n')
for stage in (1, 2, 3, 4):
    for signed in (False, True):
        name = '__sfloat32_64' if signed else '__ufloat32_64'
        call = f'jsr .loword({name})' if stage in (1,2) else f'jsl {name}'
        ret = 'rtl' if stage == 4 else 'rts'
        for batch in range((len(VALUES)+63)//64):
            rows = VALUES[batch*64:(batch+1)*64]
            lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                     f'.import {name}', '.export _conversion_probe, _conversion_after',
                     '.segment "CODE"', '_conversion_probe:', 'phy']
            for value in rows:
                for off in (0,2,4,6):
                    lines += [f'lda #${(value>>(8*off))&65535:04x}', f'sta z:__arith_lhs+{off}']
                lines += ['ldy #$5aa5', 'ldx #$a55a', call, 'jsr .loword(_conversion_after)']
            lines += ['lda #0', 'ply', ret, '_conversion_after:', 'rts']
            driver = c.OUT/f'driver-{stage}-{signed}-{batch}.s'
            driver.write_text('\n'.join(lines)+'\n')
            raw = c.OUT/f'convert-{stage}-{signed}-{batch}.raw'
            c.run([sys.executable,ROOT/'tools/build-rom.py',source,'--assembly',driver,
                   '--stage',str(stage),'-o',raw],timeout=300)
            sy = {n.removeprefix('_'):int(a,16) for a,n in
                  re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
            rom = raw.with_suffix('.sfc')
            c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
            expected = ','.join(f'0x{reference(x,signed):08x}' for x in rows)
            checks = f"""
local expected={{{expected}}};local calls=0
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState()
 local got=emu.read16(0x02,emu.memType.snesWorkRam,false)|(emu.read16(0x04,emu.memType.snesWorkRam,false)<<16)
 require_value(got==expected[calls] and s['cpu.x']==0xa55a and s['cpu.y']==0x5aa5,'integer-to-float case '..calls)
end,emu.callbackType.exec,{sy['conversion_after']},{sy['conversion_after']})
emu.addMemoryCallback(function()require_value(calls=={len(rows)},'conversion count')end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
"""
            c.emulate(rom,sy,0,extra_checks=checks,timeout_seconds=60)

public = c.OUT/'public.c'
public.write_text(r'''
union Bits {float f;unsigned long u;} result;
volatile unsigned long long u=0x4000004000000001ULL;
volatile long long s=-16777219LL;
volatile long long small=123;
volatile float f=-12345.75F, large=4294967296.0F;
volatile double fraction=2.75;
volatile long long compound=5;
volatile unsigned long long unsigned_compound=10ULL;
volatile unsigned visits;
volatile int narrow=7;
volatile unsigned unsigned_narrow=65535U;
volatile long narrow_long=100L;
volatile unsigned long long wide_delta=2ULL;
volatile int shift_value=3;
volatile int negative_shift=-8;
volatile long shift_long=3L;
float static_rounded=(float)0x4000004000000001ULL;
float static_implicit=0x4000004000000001ULL;
float static_unsigned_high=0x8000008000000001ULL;
float static_sum=0.5F+123LL;
float static_choice=(1ULL<<40)?3.0F:1.0F/0.0F;
int static_compare=123LL>122.5F;
int static_logic=1.0F&&(1ULL<<40);
int static_short=0.0F&&(1ULL/0ULL);
long long static_logical_wide=0.0F||(1ULL<<40);
long long static_integer=-12345.75F;
long long static_cast=(long long)12345.75F;
volatile long long *compound_pointer(void){visits++;return &compound;}
int main(void){
    float local;
    result.f=(float)u;if(result.u!=0x5e800001UL)return 1;
    result.f=s;if(result.u!=0xcb800002UL)return 2;
    if((long long)f!=-12345LL)return 3;
    if((unsigned long long)large!=4294967296ULL)return 4;
    result.f=0.5F+small;if(result.u!=0x42f70000UL)return 5;
    result.f=small+0.5F;if(result.u!=0x42f70000UL)return 6;
    local=0.5F;local+=small;result.f=local;if(result.u!=0x42f70000UL)return 7;
    if(!(small>122.5F)||small<122.5F)return 8;
    compound+=fraction;if(compound!=7LL)return 9;
    *compound_pointer()-=0.5F;if(compound!=6LL||visits!=1)return 10;
    *compound_pointer()+=fraction;if(compound!=8LL||visits!=2)return 11;
    unsigned_compound+=fraction;if(unsigned_compound!=12ULL)return 12;
    unsigned_compound-=0.5F;if(unsigned_compound!=11ULL)return 13;
    s=f;unsigned_compound=large;
    if(s!=-12345LL||unsigned_compound!=4294967296ULL)return 14;
    result.f=static_rounded;if(result.u!=0x5e800001UL)return 15;
    result.f=static_implicit;if(result.u!=0x5e800001UL)return 16;
    if(static_integer!=-12345LL||static_cast!=12345LL)return 17;
    result.f=static_sum;if(result.u!=0x42f70000UL||!static_compare)return 18;
    result.f=static_unsigned_high;if(result.u!=0x5f000001UL)return 19;
    if(static_logic!=1||static_short!=0||static_logical_wide!=1LL)return 20;
    result.f=static_choice;if(result.u!=0x40400000UL)return 21;
    narrow+=wide_delta;if(narrow!=9)return 22;
    unsigned_narrow+=wide_delta;if(unsigned_narrow!=1U)return 23;
    narrow_long/=wide_delta;if(narrow_long!=50L)return 24;
    narrow+=fraction;if(narrow!=11)return 25;
    shift_value<<=wide_delta;if(shift_value!=12||(shift_value>>wide_delta)!=3)return 26;
    shift_long<<=wide_delta;if(shift_long!=12L||(shift_long>>wide_delta)!=3L)return 27;
    negative_shift>>=wide_delta;if(negative_shift!=-2)return 28;
    return 0;
}
''')
for stage in (1,2,3,4):
    raw=c.OUT/f'public-{stage}.raw'
    c.run([sys.executable,ROOT/'tools/build-rom.py',public,'--stage',str(stage),'-o',raw],timeout=300)
    sy={n.removeprefix('_'):int(a,16) for a,n in
        re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
    rom=raw.with_suffix('.sfc')
    c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
    c.emulate(rom,sy,0,timeout_seconds=60)
print(f'PASS: {len(VALUES)} signed and unsigned integer-to-float vectors and C conversions, stages 1/2/3/4')
