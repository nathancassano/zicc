"""Interrupt loops that use X for near addresses and Y for far addresses. Check that the loops still work across bank boundaries and when Y wraps."""
import os
import argparse, importlib.util, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'far-loop-interrupt-check';OUT.mkdir(parents=True,exist_ok=True);c.OUT=OUT
parser=argparse.ArgumentParser();parser.add_argument('--region');parser.add_argument('--mode');args=parser.parse_args()
def worker(region,mode):
    sys.path.insert(0,str(ROOT/'tools'))
    from mesen_core import Core,SnesConfig
    stem=OUT/mode;home=OUT/mode/region
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
    script=r'''
local returns,entries,nested,depth=0,0,0,0
local active=nil
local active_entry=nil
local specialized={}
local interrupted={copy_far=0,scan_far=0,equal_far=0,reduce_far=0}
local function word(a) return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false) end
local function byte(a) return emu.read(a&0x1ffff,emu.memType.snesWorkRam,false) end
local function seed(a,n,v)
 for i=0,n-1 do emu.write((a+i)&0x1ffff,v,emu.memType.snesWorkRam) end
 emu.write((a+n)&0x1ffff,0,emu.memType.snesWorkRam)
end
'''
    script+=f'''emu.addMemoryCallback(function()
 seed(0x8000,65793,1);seed(0x1a000,12000,3)
end,emu.callbackType.exec,{sy['main']},{sy['main']})
'''
    targets=[(name,sy[name],False) for name in ('copy_far','scan_far','equal_far','reduce_far')]
    for entry,logical,banks in re.findall(r'^; bank specialization: (\w+) (\w+) ([NRW]{2})$',stem.with_suffix('.s').read_text(),re.M):
        if logical in ('copy_far','equal_far','reduce_far'):targets.append((logical,sy[entry],True))
    for name,address,private in targets:
        script+=f'''emu.addMemoryCallback(function()
 active='{name}';active_entry={address}
 if {'true' if private else 'false'} then specialized[{address}]=specialized[{address}] or 0 end
 local s=emu.getState();local sp=s['cpu.sp'];local target=0x800000|((word(sp+1)+1)&65535)
 local saved={{}};for i=0,15 do saved[i]=word(0x02+i*2) end;local finished=false
 emu.addMemoryCallback(function()
  if finished then return end;finished=true;active=nil;active_entry=nil
  local after=emu.getState();assert(after['cpu.sp']==sp+2 and after['cpu.y']==s['cpu.y'],'callee stack/Y')
 end,emu.callbackType.exec,target,target)
end,emu.callbackType.exec,{address},{address})
'''
    for name in ('loop_irq','loop_nmi'):
        script+=f'''emu.addMemoryCallback(function()
 entries=entries+1;depth=depth+1;if depth>1 then nested=nested+1 end
 if active then interrupted[active]=interrupted[active]+1 end
 if active_entry and specialized[active_entry] then specialized[active_entry]=specialized[active_entry]+1 end
 local s=emu.getState();local sp=s['cpu.sp'];local ps=byte(sp+1);local bank=byte(sp+4)
 local target=(bank<<16)|word(sp+2);local saved={{}};for i=0,15 do saved[i]=word(0x02+i*2) end;local finished=false
 emu.addMemoryCallback(function()
  if finished then return end;finished=true;returns=returns+1;depth=depth-1
  local after=emu.getState()
  for _,key in ipairs({{'a','x','y','d','dbr'}}) do assert(after['cpu.'..key]==s['cpu.'..key],'interrupt '..key) end
  assert(after['cpu.sp']==sp+4 and after['cpu.ps']==ps and after['cpu.k']==bank,'interrupt stack/status/bank')
  for i=0,15 do assert(word(0x02+i*2)==saved[i],'interrupt private DP '..i) end
 end,emu.callbackType.exec,target,target)
end,emu.callbackType.exec,{sy[name]&65535},{sy[name]&65535})
'''
    script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0,'return '..s['cpu.a']);assert(s['cpu.sp']==1279,'main stack')
 assert(entries==returns and depth==0 and nested>0,'nested interrupt coverage')
 for name,count in pairs(interrupted) do assert(count>0,'no interrupts in '..name) end
 for entry,count in pairs(specialized) do assert(count>0,'no interrupts in specialized entry '..entry) end
 assert({'true' if mode=='optimized' else 'false'}== (next(specialized)~=nil),'private-entry coverage')
 emu.log('PASS {region} {mode} interrupts='..entries..' nested='..nested);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1
        config.DisableFrameSkipping=True;config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(stem.with_suffix('.sfc'),home/'check.lua',script);core.start();core.wait_for('PASS',120 if mode=='unoptimized' else 60)
        print(next(line for line in core.log().splitlines() if line.startswith('PASS ')))
    finally:core.close_with_log(home/'check.log')
if args.region:worker(args.region,args.mode);sys.exit(0)
helper=OUT/'enable.o';c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',helper,ROOT/'tests/far_loop_interrupts.s'])
report={}
for mode in ('optimized','unoptimized'):
    stem=OUT/(mode+'_kernels');command=[ROOT/'build/zicc.exe',ROOT/'tests/far_loop_kernels.c','-o',stem.with_suffix('.s')]
    if mode=='unoptimized':command+=['--no-register-loops','--no-strength-reduction']
    c.run(command);c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',stem.with_suffix('.o'),stem.with_suffix('.s')])
    source=(ROOT/'tests/far_loop_interrupts.c').read_text().replace('EXPECTED_SUM',str((10965*257*0x01010101+257)&0xffffffff)+'UL')
    source=source.replace('struct Record ram_records[500];','const struct Record rom_records[500]={'+',\n'.join(['{1,2UL}']*500)+'};\nstruct Record ram_records[500];');objects=[stem.with_suffix('.o')]
    if mode=='optimized':
        source='const char rom_source[12001]={'+',\n'.join(','.join(['3']*64) for _ in range(187))+',\n'+','.join(['3']*32+['0'])+'};\n'+source
        source=source.replace('(const char * __far)0x7fa000UL','rom_source')
        source=source.replace('    /* 65793 bytes', '    if(!equal_far(copied,rom_source))return 6;\n    /* 65793 bytes')
        source+='\n'+(ROOT/'tests/far_loop_kernels.c').read_text().replace('struct Record { short quantity; unsigned long price; };','',1);objects=[]
    c.compile_case(mode,source,extra_objects=[*objects,helper,ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
    for region in ('ntsc','pal'):
        report[mode+'-'+region]=c.run([sys.executable,__file__,'--mode',mode,'--region',region],timeout=150 if mode=='unoptimized' else 90).stdout
        print(report[mode+'-'+region])
(OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
