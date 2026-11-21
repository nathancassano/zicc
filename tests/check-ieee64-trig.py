"""Test binary64 sine and cosine against independent Decimal range reduction."""
import os
import argparse
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import importlib.util
from pathlib import Path
import random
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT / 'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-trig-check'
c.OUT.mkdir(parents=True, exist_ok=True)
SIGN = 1 << 63
INF = 0x7ff0000000000000
NAN = 0x7ff8000000000000
CASES = [0, SIGN, 1, SIGN | 1, (1 << 52)-1, 1 << 52, INF, SIGN | INF, NAN | 123]
for base in (0x3fe0000000000000, 0x3fe921fb54442d18, 0x3ff921fb54442d18,
             0x400921fb54442d18, 0x7fefffffffffffff):
    CASES += [sign | (base + d) for sign in (0, SIGN) for d in (-2, -1, 0, 1, 2)
              if 0 < base + d < INF]
rng = random.Random(0x51c064)
CASES += [rng.randrange(1, INF) | (rng.randrange(2) * SIGN) for _ in range(120)]

def atan_series(x):
    term = total = x
    k = 1
    while abs(term) > Decimal('1e-445'):
        term *= -x*x
        total += term / (2*k+1)
        k += 1
    return total

with localcontext() as ctx:
    ctx.prec = 460
    PI = +(16*atan_series(Decimal(1)/5) - 4*atan_series(Decimal(1)/239))

def reference(raw, name):
    mag = raw & ~SIGN
    if mag >= INF:
        return NAN
    if mag == 0:
        return raw if name == 'sin' else 0x3ff0000000000000
    with localcontext() as ctx:
        ctx.prec = 450
        x = Decimal.from_float(struct.unpack('<d', mag.to_bytes(8, 'little'))[0])
        half = PI/2
        q = int((x/half).to_integral_value(rounding=ROUND_HALF_EVEN))
        r = x - q*half
        sine = r
        cosine = Decimal(1)
        st = r
        ct = Decimal(1)
        for k in range(1, 180):
            st *= -r*r / ((2*k)*(2*k+1))
            ct *= -r*r / ((2*k-1)*(2*k))
            sine += st
            cosine += ct
            if abs(st) < Decimal('1e-440') and abs(ct) < Decimal('1e-440'):
                break
        result = (sine, cosine, -sine, -cosine)[q % 4] if name == 'sin' else (cosine, -sine, -cosine, sine)[q % 4]
        if name == 'sin' and raw & SIGN:
            result = -result
        return int.from_bytes(struct.pack('<d', float(result)), 'little')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=int, choices=(1, 2, 3, 4))
    args = parser.parse_args()
    source = c.OUT / 'main.c'
    source.write_text('int trig_probe(void);int main(void){return trig_probe();}\n')
    maximum = 0
    for stage in ((args.stage,) if args.stage else (1, 2, 3, 4)):
        for name in ('sin', 'cos'):
            call = f'jsr .loword(__d{name})' if stage in (1, 2) else f'jsl __d{name}'
            ret = 'rtl' if stage == 4 else 'rts'
            for batch in range((len(CASES)+63)//64):
                rows = CASES[batch*64:(batch+1)*64]
                lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                         f'.import __d{name}', '.export _trig_probe, _trig_after',
                         '.segment "CODE"', '_trig_probe:', 'phy']
                for value in rows:
                    for off in (0, 2, 4, 6):
                        lines += [f'lda #${(value >> (off*8)) & 65535:04x}', f'sta z:__arith_lhs+{off}']
                    lines += ['ldy #$5aa5', call, 'jsr .loword(_trig_after)']
                lines += ['lda #0', 'ply', ret, '_trig_after:', 'rts']
                driver = c.OUT / f'{name}-driver-{stage}-{batch}.s'
                driver.write_text('\n'.join(lines)+'\n')
                raw = c.OUT / f'{name}-{stage}-{batch}.raw'
                c.run([sys.executable, ROOT/'tools/build-rom.py', source, '--assembly', driver,
                       '--stage', str(stage), '-o', raw], timeout=300)
                sy = {n.removeprefix('_'): int(a, 16) for a, n in
                      re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
                rom = raw.with_suffix('.sfc')
                c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
                expected = ','.join(f'0x{reference(x,name):016x}' for x in rows)
                checks = f"""
local expected={{{expected}}};local calls=0;local maximum=0;local reported=false
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState()
 local function w(a)return emu.read16(a,emu.memType.snesWorkRam,false)end
 local got=w(0x02)|(w(0x04)<<16)|(w(0x06)<<32)|(w(0x08)<<48);local e=expected[calls]
 local special=((e&0x7ff0000000000000)==0x7ff0000000000000) or (e&0x7fffffffffffffff)==0
 if not special and ((got~e)&0x8000000000000000)==0 then maximum=math.max(maximum,math.abs(got-e)) end
 require_value(s['cpu.y']==0x5aa5 and ((special and got==e) or (not special and ((got~e)&0x8000000000000000)==0 and math.abs(got-e)<=4)),
 '{name} '..calls..' got '..got..' expected '..tostring(e))
end,emu.callbackType.exec,{sy['trig_after']},{sy['trig_after']})
emu.addMemoryCallback(function()require_value(calls=={len(rows)},'trig call count');if not reported then print('MAX_ULP '..maximum);reported=true end end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
"""
                output = c.emulate(rom, sy, 0, extra_checks=checks, timeout_seconds=90)
                maximum = max(maximum, int(re.search(r'MAX_ULP (\d+)', output)[1]))
    public = c.OUT / 'public.c'
    public.write_text(r'''
#include <math.h>
typedef double (*Trig)(double);
Trig volatile s=sin,c=cos;
volatile double x=0.0;
int main(void){return sin(x)!=0.0||cos(x)!=1.0||s(x)!=0.0||c(x)!=1.0;}
''')
    narrow = c.OUT / 'narrow.c'
    narrow.write_text('#include <math.h>\nvolatile float x=0.0F;int main(void){return sinf(x)!=0.0F||cosf(x)!=1.0F;}\n')
    for stage in ((args.stage,) if args.stage else (1, 2, 3, 4)):
        for name, path in (('public', public), ('narrow', narrow)):
            raw = c.OUT / f'{name}-{stage}.raw'
            c.run([sys.executable, ROOT/'tools/build-rom.py', path, '--stage', str(stage), '-o', raw], timeout=300)
            sy = {n.removeprefix('_'): int(a, 16) for a, n in
                  re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
            if name == 'public':
                assert '_dsin' in sy and '_dcos' in sy and 'sin' in sy and 'cos' in sy
            else:
                assert '_dsin' not in sy and '_dcos' not in sy and 'sin' not in sy and 'cos' not in sy
            rom = raw.with_suffix('.sfc')
            c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
            c.emulate(rom, sy, 0)
    print(f'PASS: {len(CASES)} values for each trig function, max {maximum} ULP, ' +
          (f'stage {args.stage}' if args.stage else 'stages 1/2/3/4'))

if __name__ == '__main__':
    main()
