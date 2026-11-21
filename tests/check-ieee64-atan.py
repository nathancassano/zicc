"""Check binary64 atan against an independent high-precision Decimal series."""
import os
import argparse
from decimal import Decimal, localcontext
import importlib.util
from pathlib import Path
import random
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-atan-check';c.OUT.mkdir(parents=True,exist_ok=True)
SIGN=1<<63;INF=0x7ff0000000000000;NAN=0x7ff8000000000000
CASES=[0,SIGN,1,SIGN|1,(1<<52)-1,1<<52,INF,SIGN|INF,0x7ff8000000001234]
for base in (0x3fdc000000000000,0x3ff0000000000000,0x7fefffffffffffff):
    CASES += [sign | (base+delta) for sign in (0,SIGN) for delta in (-2,-1,0,1) if 0 < base+delta < INF]
rng=random.Random(0xa7a64)
CASES += [rng.randrange(0,INF)|(rng.randrange(2)*SIGN) for _ in range(140)]

def series(x):
    term=x; total=x; square=x*x; k=1
    while abs(term)>Decimal('1e-150'):
        term *= -square
        total += term/(2*k+1)
        k+=1
    return total

def reference(raw):
    magnitude=raw&~SIGN
    if magnitude>INF:return NAN
    if magnitude==0:return raw
    with localcontext() as ctx:
        ctx.prec=160
        pi=16*series(Decimal(1)/5)-4*series(Decimal(1)/239)
        if magnitude==INF:
            result=pi/2
        else:
            x=Decimal.from_float(struct.unpack('<d',magnitude.to_bytes(8,'little'))[0])
            inverse=x>1
            if inverse:x=1/x
            factor=1
            while x>Decimal('0.125'):
                x=x/(1+(1+x*x).sqrt())
                factor*=2
            result=factor*series(x)
            if inverse:result=pi/2-result
        if raw&SIGN:result=-result
        value=float(result)
    return int.from_bytes(struct.pack('<d',value),'little')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',type=int,choices=(1,2,3,4));args=parser.parse_args()
    source=c.OUT/'main.c';source.write_text('int atan_probe(void);int main(void){return atan_probe();}\n')
    max_observed=0
    for stage in ((args.stage,) if args.stage else (1,2,3,4)):
        call='jsr .loword(__datan)' if stage in (1,2) else 'jsl __datan'
        ret='rtl' if stage==4 else 'rts'
        for batch in range((len(CASES)+95)//96):
            rows=CASES[batch*96:(batch+1)*96]
            lines=['.setcpu "65816"','.a16','.i16','.importzp __arith_lhs',
                   '.import __datan','.export _atan_probe, _atan_after','.segment "CODE"','_atan_probe:','phy']
            for value in rows:
                for off in (0,2,4,6):lines += [f'lda #${(value>>(off*8))&65535:04x}',f'sta z:__arith_lhs+{off}']
                lines += ['ldy #$5aa5',call,'jsr .loword(_atan_after)']
            lines += ['lda #0','ply',ret,'_atan_after:','rts']
            driver=c.OUT/f'driver-{stage}-{batch}.s';driver.write_text('\n'.join(lines)+'\n')
            raw=c.OUT/f'atan-{stage}-{batch}.raw'
            c.run([sys.executable,ROOT/'tools/build-rom.py',source,'--assembly',driver,'--stage',str(stage),'-o',raw],timeout=300)
            sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
            rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
            expected=','.join(f'0x{reference(x):016x}' for x in rows)
            checks=f'''
local expected={{{expected}}};local calls=0;local maximum=0;local reported=false
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState()
 local function w(a)return emu.read16(a,emu.memType.snesWorkRam,false)end
 local got=w(0x02)|(w(0x04)<<16)|(w(0x06)<<32)|(w(0x08)<<48);local e=expected[calls]
 local special=((e&0x7ff0000000000000)==0x7ff0000000000000) or (e&0x7fffffffffffffff)==0
 if not special and ((got~e)&0x8000000000000000)==0 then maximum=math.max(maximum,math.abs(got-e)) end
 require_value(s['cpu.y']==0x5aa5 and ((special and got==e) or (not special and ((got~e)&0x8000000000000000)==0 and math.abs(got-e)<=4)),
 'atan '..calls..' got '..got..' expected '..tostring(e))
end,emu.callbackType.exec,{sy['atan_after']},{sy['atan_after']})
emu.addMemoryCallback(function()require_value(calls=={len(rows)},'atan call count');if not reported then print('MAX_ULP '..maximum);reported=true end end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
            output=c.emulate(rom,sy,0,extra_checks=checks,timeout_seconds=60)
            max_observed=max(max_observed,int(re.search(r'MAX_ULP (\d+)',output)[1]))
    public=c.OUT/'public.c'
    public.write_text(r'''
#include <math.h>
union Bits { double d; unsigned long long u; } value;
typedef double (*Atan)(double);
Atan volatile callback=atan;
volatile double input=1.0;
volatile float narrow=0.0F;
int main(void){
 value.d=atan(input);if(value.u<0x3fe921fb54442d16ULL||value.u>0x3fe921fb54442d1aULL)return 1;
 value.d=callback(input);if(value.u<0x3fe921fb54442d16ULL||value.u>0x3fe921fb54442d1aULL)return 2;
 return atanf(narrow)!=0.0F;
}
''')
    narrow=c.OUT/'narrow.c'
    narrow.write_text('#include <math.h>\nvolatile float x=0.0F;int main(void){return atanf(x)!=0.0F;}\n')
    for stage in ((args.stage,) if args.stage else (1,2,3,4)):
        for name,path in (('public',public),('narrow',narrow)):
            raw=c.OUT/f'{name}-{stage}.raw'
            c.run([sys.executable,ROOT/'tools/build-rom.py',path,'--stage',str(stage),'-o',raw],timeout=300)
            sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
            if name=='public':assert '_datan' in sy and 'atan' in sy
            else:assert '_datan' not in sy and 'atan' not in sy
            rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
            c.emulate(rom,sy,0)
    print(f'PASS: {len(CASES)} binary64 atans, max {max_observed} ULP, '+(f'stage {args.stage}' if args.stage else 'stages 1/2/3/4'))

if __name__=='__main__':main()
