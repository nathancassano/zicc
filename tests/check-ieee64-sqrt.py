"""Check binary64 square roots against values computed with exact integer arithmetic."""
import os
import importlib.util
import math
from pathlib import Path
import random
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-sqrt-check';c.OUT.mkdir(parents=True,exist_ok=True)
SIGN=1<<63; INF=0x7ff0000000000000; FRAC=(1<<52)-1; NAN=0x7ff8000000000000
CASES=[0,SIGN,1,2,3,FRAC,1<<52,(1<<52)+1,
       0x3ff0000000000000,0x4000000000000000,0x4010000000000000,
       0x7fefffffffffffff,INF,SIGN|1,SIGN|INF,0x7ff8000000000123,0xfff0000000000001]
rng=random.Random(0x645a2716)
CASES += [rng.getrandbits(63) for _ in range(100)]

def reference(raw):
    magnitude=raw&~SIGN
    if magnitude==0:return raw
    if raw&SIGN:return NAN
    if magnitude>=INF:return INF if magnitude==INF else NAN
    field=(raw>>52)&2047;mantissa=raw&FRAC
    if field:
        mantissa|=1<<52;exponent=field-1023
    else:
        exponent=-1022
        while mantissa < (1<<52):mantissa<<=1;exponent-=1
    if exponent&1:mantissa<<=1;exponent-=1
    n=mantissa<<52;root=math.isqrt(n);remainder=n-root*root
    if remainder>root:root+=1
    biased=exponent//2+1023
    if root==1<<53:root>>=1;biased+=1
    return (biased<<52)|(root&FRAC)

def main():
    source=c.OUT/'main.c';source.write_text('int sqrt_probe(void);int main(void){return sqrt_probe();}\n')
    for stage in (1,2,3,4):
        call='jsr .loword(__dsqrt)' if stage in (1,2) else 'jsl __dsqrt'
        ret='rtl' if stage==4 else 'rts'
        for batch in range((len(CASES)+39)//40):
            rows=CASES[batch*40:(batch+1)*40]
            lines=['.setcpu "65816"','.a16','.i16','.importzp __arith_lhs',
                   '.import __dsqrt','.export _sqrt_probe, _sqrt_after', '.segment "CODE"', '_sqrt_probe:', 'phy']
            for value in rows:
                for offset in (0,2,4,6):lines += [f'lda #${(value>>(offset*8))&65535:04x}',f'sta z:__arith_lhs+{offset}']
                lines += ['ldx #$1234','ldy #$5aa5',call,'jsr .loword(_sqrt_after)']
            lines += ['lda #0','ply',ret,'_sqrt_after:','rts']
            driver=c.OUT/f'driver-{stage}-{batch}.s';driver.write_text('\n'.join(lines)+'\n')
            raw=c.OUT/f'sqrt-{stage}-{batch}.raw'
            c.run([sys.executable,ROOT/'tools/build-rom.py',source,'--assembly',driver,'--stage',str(stage),'-o',raw],timeout=300)
            sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
            rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
            expected=','.join(f'0x{reference(x):016x}' for x in rows)
            checks=f'''
local expected={{{expected}}};local calls=0
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState()
 local function w(a)return emu.read16(a,emu.memType.snesWorkRam,false)end
 local got=w(0x02)|(w(0x04)<<16)|(w(0x06)<<32)|(w(0x08)<<48)
 require_value(s['cpu.x']==0x1234 and s['cpu.y']==0x5aa5 and got==expected[calls],
  'sqrt '..calls..' got '..got..' expected '..tostring(expected[calls]))
end,emu.callbackType.exec,{sy['sqrt_after']},{sy['sqrt_after']})
emu.addMemoryCallback(function()require_value(calls=={len(rows)},'sqrt call count')end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
            c.emulate(rom,sy,0,extra_checks=checks,timeout_seconds=20)
    public=c.OUT/'public.c'
    public.write_text(r'''
#include <math.h>
union Bits { double d; unsigned long long u; } value;
typedef double (*Sqrt)(double);
Sqrt volatile callback=sqrt;
volatile double input=2.0;
volatile float narrow=9.0F;
int main(void){
 value.d=sqrt(input);if(value.u!=0x3ff6a09e667f3bcdULL)return 1;
 value.d=callback(input);if(value.u!=0x3ff6a09e667f3bcdULL)return 2;
 return sqrtf(narrow)!=3.0F;
}
''')
    narrow=c.OUT/'narrow.c'
    narrow.write_text('#include <math.h>\nvolatile float x=4.0F;int main(void){return sqrtf(x)!=2.0F;}\n')
    for stage in (1,2,3,4):
        for name,path in (('public',public),('narrow',narrow)):
            raw=c.OUT/f'{name}-{stage}.raw'
            c.run([sys.executable,ROOT/'tools/build-rom.py',path,'--stage',str(stage),'-o',raw],timeout=300)
            sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
            if name=='public':assert '_dsqrt' in sy and 'sqrt' in sy
            else:assert '_dsqrt' not in sy and 'sqrt' not in sy
            rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
            c.emulate(rom,sy,0)
    print(f'PASS: {len(CASES)} exact binary64 square roots, stages 1/2/3/4')

if __name__=='__main__':main()
