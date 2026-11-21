"""Require real NMIs to preserve live wide scratch and the S-CPU arithmetic unit."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'wide-interrupt-live-check'
c.OUT.mkdir(parents=True, exist_ok=True)
source = c.OUT/'live.c'
source.write_text(r'''
volatile double numerator=7.0,denominator=3.0000000000000004,quotient;
volatile double irq_left=1.5,irq_right=2.0,irq_product,irq_ratio;
volatile double mul_left=1.0000000000000002,mul_right=1.0000000000000002,product;
volatile unsigned long long irq_dividend=27,irq_divisor=5,irq_quotient;
volatile unsigned long long dividend=0xfedcba9876543210ULL,divisor=3,wide_quotient;
volatile unsigned irq_count;
__interrupt(nmi) void live_nmi(void){
    unsigned char acknowledge=*(volatile unsigned char * __far)0x4210UL;
    irq_product=irq_left*irq_right;
    irq_ratio=irq_left/irq_right;
    irq_quotient=irq_dividend/irq_divisor;
    irq_count++;
}
int main(void){
    unsigned i;
    unsigned char acknowledge=*(volatile unsigned char * __far)0x4210UL;
    *(volatile unsigned char * __far)0x4200UL=0x80;
    for(i=0;i<500;i++){
        quotient=numerator/denominator;
        if(quotient!=2.333333333333333)return 1;
    }
    for(i=0;i<500;i++){
        product=mul_left*mul_right;
        wide_quotient=dividend/divisor;
        if(product!=1.0000000000000004||wide_quotient!=0x54f43e32d21c10b0ULL)return 3;
    }
    *(volatile unsigned char * __far)0x4200UL=0;
    if(irq_count==0||irq_product!=3.0||irq_ratio!=0.75||irq_quotient!=5)return 2;
    return 0;
}
''')
for stage in (1, 2, 3, 4):
    raw=c.OUT/f'live-{stage}.raw'
    c.run([sys.executable,ROOT/'tools/build-rom.py',source,'--stage',str(stage),'-o',raw],timeout=300)
    sy={n.removeprefix('_'):int(a,16) for a,n in
        re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
    rom=raw.with_suffix('.sfc')
    c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
    checks=f"""
local overlaps,restored,nmis,divisions=0,0,0,0
local mul_soft,div_soft,fdiv_soft,busy_nmis=0,0,0,0
local pending=false
emu.addMemoryCallback(function() pending=true end,emu.callbackType.write,0x4203,0x4203)
emu.addMemoryCallback(function() pending=true end,emu.callbackType.write,0x4206,0x4206)
emu.addMemoryCallback(function() pending=false end,emu.callbackType.read,0x4216,0x4216)
emu.addMemoryCallback(function() mul_soft=mul_soft+1 end,emu.callbackType.exec,{sy['_dmul_soft']},{sy['_dmul_soft']})
emu.addMemoryCallback(function() div_soft=div_soft+1 end,emu.callbackType.exec,{sy['_udiv64_soft']},{sy['_udiv64_soft']})
emu.addMemoryCallback(function() fdiv_soft=fdiv_soft+1 end,emu.callbackType.exec,{sy['_ddiv_soft']},{sy['_ddiv_soft']})
local function word(a)return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false)end
emu.addMemoryCallback(function()divisions=divisions+1 end,emu.callbackType.exec,{sy['_ddiv']},{sy['_ddiv']})
emu.addMemoryCallback(function()
 nmis=nmis+1
 if pending then busy_nmis=busy_nmis+1 end
 local s=emu.getState();local sp=s['cpu.sp']
 local target=(emu.read((sp+4)&0x1ffff,emu.memType.snesWorkRam,false)<<16)|word(sp+2)
 if target>={sy['div64_compute']} and target<{sy['div64_pack']} then
  overlaps=overlaps+1
  local ps=emu.read((sp+1)&0x1ffff,emu.memType.snesWorkRam,false)
  local saved={{}};for i=0,15 do saved[i]=word(0x02+i*2)end
  local done=false
  emu.addMemoryCallback(function()
   if done then return end
   local t=emu.getState()
   if t['cpu.sp']~=sp+4 then return end
   done=true;restored=restored+1
   for _,k in ipairs({{'a','x','y','d','dbr'}}) do
    require_value(t['cpu.'..k]==s['cpu.'..k],'live NMI register '..k)
   end
   require_value(t['cpu.ps']==ps,'live NMI status')
   for i=0,15 do require_value(word(0x02+i*2)==saved[i],'live NMI scratch '..i)end
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{sy['live_nmi']},{sy['live_nmi']})
emu.addMemoryCallback(function()
 require_value(divisions==500,'division call count')
 require_value(nmis>0 and overlaps>0 and restored==overlaps,'NMI must interrupt division and restore it')
 require_value(mul_soft==nmis and div_soft==nmis and fdiv_soft==nmis,'each interrupt must use the software entries')
 require_value(busy_nmis>0,'NMI must overlap a hardware arithmetic operation')
 print('LIVE_NMI divisions='..divisions..' total='..nmis..' overlaps='..overlaps..' restored='..restored..' hardware='..busy_nmis)
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
"""
    output=c.emulate(rom,sy,0,extra_checks=checks,timeout_seconds=90)
    print(f'stage {stage}: '+re.search(r'LIVE_NMI .*',output)[0],flush=True)
print('PASS: live NMI during binary64 division, stages 1/2/3/4')
