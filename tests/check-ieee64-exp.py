"""Check binary64 exponential against Python Decimal at high precision."""
import os
import argparse
from decimal import Decimal, localcontext
import importlib.util
import math
from pathlib import Path
import random
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-exp-check';c.OUT.mkdir(parents=True,exist_ok=True)
SIGN=1<<63;INF=0x7ff0000000000000;NAN=0x7ff8000000000000
def raw(x):return int.from_bytes(struct.pack('<d',x),'little')
CASES=[0,SIGN,1,SIGN|1,INF,SIGN|INF,0x7ff8000000001234,0xfff0000000000001]
CASES += [raw(x) for x in (-1024.,-1000.,-746.,-745.2,-745.1332191019411,-745.,-744.,
                            -710.,-709.,-100.,-1.,-0.5,-1e-16,1e-16,0.5,1.,100.,
                            709.,709.78,709.782712893384,710.,1024.)]
rng=random.Random(0xe0642026)
CASES += [raw(rng.uniform(-746,711)) for _ in range(160)]
for n in (-1075,-1074,-1022,-1000,-1,0,1,100,1023,1024):
    center=n*math.log(2)
    CASES += [raw(math.nextafter(center,-math.inf)),raw(center),raw(math.nextafter(center,math.inf))]

def reference(bits):
    magnitude=bits&~SIGN
    if magnitude>=INF:
        if magnitude>INF:return NAN
        return 0 if bits&SIGN else INF
    value=struct.unpack('<d',bits.to_bytes(8,'little'))[0]
    if value>1024:return INF
    if value< -1024:return 0
    with localcontext() as ctx:
        ctx.prec=120
        result=float(Decimal.from_float(value).exp())
    return raw(result)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',type=int,choices=(1,2,3,4));args=parser.parse_args()
    source=c.OUT/'main.c';source.write_text('int exp_probe(void);int main(void){return exp_probe();}\n')
    maximum=0
    for stage in ((args.stage,) if args.stage else (1,2,3,4)):
        call='jsr .loword(__dexp)' if stage in (1,2) else 'jsl __dexp'
        ret='rtl' if stage==4 else 'rts'
        lines=['.setcpu "65816"','.a16','.i16','.importzp __arith_lhs',
               '.import __dexp','.export _exp_probe, _exp_after','.segment "CODE"','_exp_probe:','phy']
        for value in CASES:
            for off in (0,2,4,6):lines += [f'lda #${(value>>(off*8))&65535:04x}',f'sta z:__arith_lhs+{off}']
            lines += ['ldy #$5aa5',call,'jsr .loword(_exp_after)']
        lines += ['lda #0','ply',ret,'_exp_after:','rts']
        driver=c.OUT/f'driver-{stage}.s';driver.write_text('\n'.join(lines)+'\n')
        output=c.OUT/f'exp-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',source,'--assembly',driver,'--stage',str(stage),'-o',output],timeout=300)
        sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',output.with_suffix('.labels').read_text(),re.M)}
        rom=output.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',output,rom,ROOT/'tests/title.txt'])
        expected=','.join(f'0x{reference(x):016x}' for x in CASES)
        checks=f'''
local expected={{{expected}}};local calls=0;local maximum=0;local reported=false
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState()
 local function w(a)return emu.read16(a,emu.memType.snesWorkRam,false)end
 local got=w(0x02)|(w(0x04)<<16)|(w(0x06)<<32)|(w(0x08)<<48);local e=expected[calls]
 local special=((e&0x7ff0000000000000)==0x7ff0000000000000) or e==0
 if not special and got>=0 then maximum=math.max(maximum,math.abs(got-e)) end
 require_value(s['cpu.y']==0x5aa5 and ((special and got==e) or (not special and got>=0 and math.abs(got-e)<=4)),
 'exp '..calls..' got '..got..' expected '..tostring(e))
end,emu.callbackType.exec,{sy['exp_after']},{sy['exp_after']})
emu.addMemoryCallback(function()require_value(calls=={len(CASES)},'exp call count');if not reported then print('MAX_ULP '..maximum);reported=true end end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
        log=c.emulate(rom,sy,0,extra_checks=checks,timeout_seconds=60)
        maximum=max(maximum,int(re.search(r'MAX_ULP (\d+)',log)[1]))
    public=c.OUT/'public.c'
    public.write_text(r'''
#include <math.h>
union Bits { double d; unsigned long long u; } value;
typedef double (*Exp)(double);
Exp volatile callback=exp;
volatile double input=1.0;
volatile float narrow=0.0F;
int main(void){
 value.d=exp(input);if(value.u<0x4005bf0a8b145767ULL||value.u>0x4005bf0a8b14576bULL)return 1;
 value.d=callback(input);if(value.u<0x4005bf0a8b145767ULL||value.u>0x4005bf0a8b14576bULL)return 2;
 return expf(narrow)!=1.0F;
}
''')
    narrow=c.OUT/'narrow.c';narrow.write_text('#include <math.h>\nvolatile float x=0.0F;int main(void){return expf(x)!=1.0F;}\n')
    for stage in ((args.stage,) if args.stage else (1,2,3,4)):
        for name,path in (('public',public),('narrow',narrow)):
            output=c.OUT/f'{name}-{stage}.raw'
            c.run([sys.executable,ROOT/'tools/build-rom.py',path,'--stage',str(stage),'-o',output],timeout=300)
            sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',output.with_suffix('.labels').read_text(),re.M)}
            if name=='public':assert '_dexp' in sy and 'exp' in sy
            else:assert '_dexp' not in sy and 'exp' not in sy
            rom=output.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',output,rom,ROOT/'tests/title.txt'])
            c.emulate(rom,sy,0)
    print(f'PASS: {len(CASES)} binary64 exponentials, max {maximum} ULP, '+(f'stage {args.stage}' if args.stage else 'stages 1/2/3/4'))

if __name__=='__main__':main()
