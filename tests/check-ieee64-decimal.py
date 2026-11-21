"""Check exact assembly binary64-to-decimal expansion against Python integers."""
import os
import importlib.util
from pathlib import Path
import random
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-decimal-check';c.OUT.mkdir(parents=True,exist_ok=True)
MASK=(1<<52)-1
CASES=[0,1<<63,1,2,0x000fffffffffffff,0x0010000000000000,
       0x3ff0000000000000,0x3ff8000000000000,0xbff8000000000000,
       0x3fb999999999999a,0x7fefffffffffffff,0x7ff0000000000000,
       0xfff0000000000000,0x7ff0000000000001,0xfff8000000001234]
CASES += [1<<bit for bit in (15,16,31,32,47,48)]
rng=random.Random(0xdeca164)
CASES += [(rng.randrange(1,2047)<<52)|rng.getrandbits(52) for _ in range(12)]

def expected(bits):
    exponent=(bits>>52)&0x7ff;fraction=bits&MASK
    if exponent==0x7ff:return (2 if fraction else 1,0,'')
    mantissa=(fraction|(1<<52)) if exponent else fraction
    if not mantissa:return (0,0,'0')
    power=exponent-1075 if exponent else -1074
    while power<0 and not (mantissa&1):mantissa>>=1;power+=1
    if power<0:scale=-power;integer=mantissa*5**scale
    else:scale=0;integer=mantissa<<power
    return (0,scale,str(integer)[::-1])

def main():
    _,plain,_=c.compile_case('plain','int main(void){return 0;}')
    _,archive,labels=c.compile_case('archive','int main(void){return 0;}',extra_objects=[ROOT/'build/libc.a'])
    assert plain.read_bytes()==archive.read_bytes()
    assert 'ieee64_dec_digits' not in labels and '_ieee64_decimal' not in labels
    source=c.OUT/'main.c';source.write_text('int decimal_probe(void);int main(void){return decimal_probe();}\n')
    rows=[expected(x) for x in CASES]
    for stage in (1,3,4):
        call='jsr .loword(__ieee64_decimal)' if stage==1 else 'jsl __ieee64_decimal'
        ret='rtl' if stage==4 else 'rts'
        lines=['.setcpu "65816"','.a16','.i16','.importzp __arith_lhs',
               '.import __ieee64_decimal, _decimal__dec_n','.export _decimal_probe, _decimal_after',
               '.segment "BSS"','index: .res 2','.segment "CODE"',
               '_decimal_probe:','phy','lda #$1234','sta f:_decimal__dec_n','stz a:index','loop:','ldx a:index']
        for offset in range(0,8,2):lines += [f'lda f:table+{offset},x',f'sta z:__arith_lhs+{offset}']
        lines += ['ldy #$5aa5',call,'_decimal_after:','lda a:index','clc','adc #8',
                  'sta a:index',f'cmp #{len(CASES)*8}','bne loop','lda #0','ply',ret,
                  '.segment "RODATA"','table:']
        for value in CASES:lines.append('.word '+','.join(f'${(value>>n)&65535:04x}' for n in (0,16,32,48)))
        driver=c.OUT/f'driver-{stage}.s';driver.write_text('\n'.join(lines)+'\n')
        raw=c.OUT/f'decimal-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',source,'--assembly',driver,'--stage',str(stage),'-o',raw],timeout=120)
        sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        entries=','.join('{%d,%d,"%s"}'%(status,scale,digits) for status,scale,digits in rows)
        checks=f'''
local expected={{{entries}}}
local calls=0
emu.addMemoryCallback(function()
 calls=calls+1;local e=expected[calls];local s=emu.getState()
 require_value(e~=nil and s['cpu.a']==e[1] and s['cpu.y']==0x5aa5,'decimal status/Y '..calls)
 require_value(emu.read16({sy['decimal__dec_n']&0x1ffff},emu.memType.snesWorkRam,false)==0x1234,'binary32 decimal workspace changed')
 if e[1]==0 then
  local n=emu.read16({sy['ieee64_dec_n']&0x1ffff},emu.memType.snesWorkRam,false)
  local scale=emu.read16({sy['ieee64_dec_scale']&0x1ffff},emu.memType.snesWorkRam,false)
  require_value(n==#e[3] and scale==e[2],'decimal count/scale '..calls)
  for i=1,#e[3] do require_value(emu.read({sy['ieee64_dec_digits']&0x1ffff}+i-1,emu.memType.snesWorkRam,false)==tonumber(e[3]:sub(i,i)),'decimal digit '..calls..':'..i) end
 end
end,emu.callbackType.exec,{sy['decimal_after']},{sy['decimal_after']})
emu.addMemoryCallback(function() require_value(calls=={len(CASES)},'decimal call count') end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
        c.emulate(rom,sy,0,extra_checks=checks,timeout_seconds=30)
    print(f'PASS: {len(CASES)} exact binary64 decimal expansions, LoROM and banked stages 3/4')

if __name__=='__main__':main()
