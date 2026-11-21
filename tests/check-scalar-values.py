"""Check copies and conversions of private values, omitted stack frames and interrupts in functions that make no calls."""
import os
import hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'scalar-value-check'
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig

def execute(stem,region):
    labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
    home=OUT/stem.name/region;core=Core(home)
    probes=('probe','store_probe','schedule_probe')
    script='''local active,returned=false,true
local call_hooks,irq_hooks,irq_frames={},{},{}
local call_sp,call_y=0,0
local hit={nmi=0,irq=0,brk=0,cop=0}
local covered={probe={nmi=0,irq=0,brk=0,cop=0},store_probe={nmi=0,irq=0,brk=0,cop=0},schedule_probe={nmi=0,irq=0,brk=0,cop=0}}
local function word(a) return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false) end
'''
    # Track actual calls, then require real IRQ/NMI delivery during the selected
    # leaf; injected BRK/COP also exercise every instruction boundary and A8
    for name in probes:
      script+=f'''emu.addMemoryCallback(function()
 active='{name}';returned=false
 local s=emu.getState();local sp=s['cpu.sp'];call_sp=sp;call_y=s['cpu.y']
 local target=0x800000|((word(sp+1)+1)&65535)
 if not call_hooks[target] then call_hooks[target]=true
 emu.addMemoryCallback(function()
  if returned then return end
  returned=true;active=false;local t=emu.getState()
  assert(t['cpu.sp']==call_sp+2 and t['cpu.y']==call_y,'leaf stack/Y')
 end,emu.callbackType.exec,target,target) end
end,emu.callbackType.exec,{labels[name]},{labels[name]})
'''
    for kind in ('nmi','irq','brk','cop'):
        script+=f'''emu.addMemoryCallback(function()
 if active then hit.{kind}=hit.{kind}+1;covered[active].{kind}=covered[active].{kind}+1 end
 local s=emu.getState();local sp=s['cpu.sp'];local ps=emu.read(sp+1,emu.memType.snesMemory,false)
 local target=(emu.read(sp+4,emu.memType.snesMemory,false)<<16)|word(sp+2)
 local saved={{}};for i=0,15 do saved[i]=word(0x02+i*2) end
 irq_frames[target]=irq_frames[target] or {{}}
 table.insert(irq_frames[target],{{s=s,sp=sp,ps=ps,saved=saved}})
 if not irq_hooks[target] then irq_hooks[target]=true
 emu.addMemoryCallback(function()
  if #irq_frames[target]==0 then return end
  local frame=table.remove(irq_frames[target]);local s,sp,ps,saved=frame.s,frame.sp,frame.ps,frame.saved
  local t=emu.getState()
  for _,k in ipairs({{'a','x','y','d','dbr'}}) do assert(t['cpu.'..k]==s['cpu.'..k],'interrupt '..k) end
  assert(t['cpu.sp']==sp+4 and t['cpu.ps']==ps,'interrupt stack/status')
  for i=0,15 do assert(word(0x02+i*2)==saved[i],'interrupt scratch '..i) end
 end,emu.callbackType.exec,target,target) end
end,emu.callbackType.exec,{labels['scalar_'+kind]&65535},{labels['scalar_'+kind]&65535})
'''
    script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0,'return '..s['cpu.a']);assert(s['cpu.sp']==1279,'main stack')
 assert(hit.nmi>0 and hit.irq>0,'hardware interrupt leaf coverage')
 for name,c in pairs(covered) do assert(c.nmi>0 and c.irq>0,'hardware interrupt coverage '..name..' nmi='..c.nmi..' irq='..c.irq) end
 {'assert(hit.brk>0 and hit.cop>0,"software interrupt leaf coverage")' if 'traps' in stem.name else ''}
 emu.log('PASS {region} nmi='..hit.nmi..' irq='..hit.irq..' brk='..hit.brk..' cop='..hit.cop);emu.breakExecution()
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1
        config.DisableFrameSkipping=True;config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(stem.with_suffix('.sfc'),home/'check.lua',script);core.start();core.wait_for('PASS',90)
        return next(x for x in core.log().splitlines() if x.startswith('PASS '))
    finally:
        core.close_with_log(home/'check.log')

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path);p.add_argument('--worker',type=Path);p.add_argument('--region');args=p.parse_args()
    if args.worker:print(execute(args.worker,args.region));return
    OUT.mkdir(parents=True,exist_ok=True);c.OUT=OUT;original=c.run
    helper=OUT/'enable.o';c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',helper,ROOT/'tests/far_loop_interrupts.s'])
    source=(ROOT/'tests/scalar-values.c').read_text();report={}
    for mode,compiler in [('optimized',ROOT/'build/zicc.exe')]+([('baseline',args.baseline)] if args.baseline else []):
        for trapped in (False,True):
            if trapped and mode=='baseline':continue
            name=mode+('-traps' if trapped else '')
            def run(cmd,*a,**kw):
                if Path(cmd[0]).name=='zicc.exe':cmd=[compiler,*cmd[1:]]
                if trapped and Path(cmd[0]).name=='ca65.exe' and Path(cmd[-1]).name==name+'.s':
                    path=Path(cmd[-1]);text=path.read_text()
                    for target in ('probe','store_probe','schedule_probe'):
                        start=text.index('_'+target+':\n');end=text.index('__size_'+target,start)
                        body=text[start:end];body=re.sub(r'(?m)^(    [a-z]{3}(?: [^\n]*)?)$',r'    .byte $00,$00\n    .byte $02,$00\n\1',body)
                        text=text[:start]+body+text[end:]
                    path.write_text(text)
                return original(cmd,*a,**kw)
            c.run=run
            # Every byte value and its high-byte alias are checked. Software
            # traps need fewer repetitions to cover the same instruction paths
            case=source.replace('a<512','a<16').replace('b<512','b<16').replace('i<12000','i<512') if trapped else source
            c.compile_case(name,case,extra_objects=[helper,ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'],flags=['--no-inline'])
            assembly=(OUT/(name+'.s')).read_text();part=assembly.split('_probe:\n',1)[1].split('__size_probe',1)[0]
            if mode=='optimized':
                assert 'scalar leaf without Y frame' in part and '    phy\n' not in part and '__arith_' not in part,part
                assert '    cmp 1,s\n' in part and 'and #$00FF' not in part,part
                def body(n):return assembly.split('_'+n+':\n',1)[1].split('__size_'+n,1)[0]
                for target in ('store_probe','pointer_first','pointer_second','pointer_last'):
                    assert 'native word store leaf' in body(target) and '    phy\n' not in body(target),body(target)
                for target in ('conditional_store','alias_store','narrow_store'):
                    assert 'scalar leaf without Y frame' in body(target) and '    phy\n' not in body(target),body(target)
                for target in ('multiple_use','changed_source','intervening_call','repeated_use','global_snapshot'):
                    assert 'native word store leaf' not in body(target),body(target)
                region=body('framed_store').split('jsr .loword(_effect)',1)[1]
                assert '    phx\n' not in region and '    sta a:$0000,x\n' in region,region
                assert '    phx\n' in body('alias_store') and 'lda 9,s' in body('alias_store'),body('alias_store')
                scheduled=body('schedule_probe')
                assert '    phx\n' not in scheduled.split('; ',1)[-1],scheduled
                snapshot=body('destination_snapshot')
                assert snapshot.index('    phx\n')<snapshot.index('jsr .loword(_change_destination)'),snapshot
            for region in ('ntsc','pal'):
                r=original([sys.executable,__file__,'--worker',OUT/name,'--region',region],timeout=120)
                report[name+'-'+region]=r.stdout.strip();print(r.stdout.strip(),flush=True)
            report[name+'-rom-sha256']=hashlib.sha256((OUT/(name+'.sfc')).read_bytes()).hexdigest()
    c.run=original
    report['compiler-sha256']=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: copy/conversion/alias/call/recursion semantics; NTSC/PAL hardware and instruction-boundary software interrupts')
if __name__=='__main__':main()
