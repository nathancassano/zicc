"""Check the exact bytes strcpy copies from string literals, including bank limits and interrupted copies."""
import os
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'literal-copy-check'
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig

def symbols(stem):
    return {alias:int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)
            for alias in (n,n.removeprefix('_'))}

def execute(stem,region):
    sy=symbols(stem);meta=json.loads(stem.with_suffix('.json').read_text());home=OUT/stem.name/region
    rom=stem.with_suffix('.sfc').read_bytes();start=sy['literal_copy']&32767;end=sy['tiny_copy']&32767
    moves=[0x800000|(0x8000+i) for i in range(start,end-2) if rom[i]==0x54 and rom[i+1]==0x7e]
    script='''local active,finished=nil,true
local call_sp,call_y,call_target=0,0,0
local hooks,frames,irq_hooks={},{},{}
local hit={nmi=0,irq=0,brk=0,cop=0}
local mvn_hit={nmi=0,irq=0}
local fallback=0
local function byte(a) return emu.read(a,emu.memType.snesMemory,false) end
local function word(a) return emu.read16(a,emu.memType.snesMemory,false) end
'''
    if meta['banked']:
        script+=f'''emu.addMemoryCallback(function()
 for i=0,{sy['__RODATA_SIZE__']}-1 do emu.write(({sy['__RODATA_RUN__']}+i)&0x1ffff,byte({sy['__RODATA_LOAD__']}+i),emu.memType.snesWorkRam) end
end,emu.callbackType.exec,{sy['main']},{sy['main']})
'''
    for name in ('literal_copy','tiny_copy'):
        script+=f'''emu.addMemoryCallback(function()
 assert(active==nil,'nested test leaf');active='{name}';finished=false
 local s=emu.getState();call_sp=s['cpu.sp'];call_y=s['cpu.y']
 local target=0x800000|((word(call_sp+1)+1)&65535);call_target=target
 if not hooks[target] then hooks[target]=true
 emu.addMemoryCallback(function()
  if finished or call_target~=target then return end
  finished=true;active=nil;local s=emu.getState()
  assert(s['cpu.sp']==call_sp+2 and s['cpu.y']==call_y and s['cpu.dbr']==0x7e,'leaf stack/Y/DBR')
 end,emu.callbackType.exec,target,target) end
end,emu.callbackType.exec,{sy[name]},{sy[name]})
'''
    if 'strcpy' in sy:
        script+=f"emu.addMemoryCallback(function() if active=='literal_copy' then fallback=fallback+1 end end,emu.callbackType.exec,{sy['strcpy']},{sy['strcpy']})\n"
    mvnset='{'+','.join('['+str(a)+']=true' for a in moves)+'}'
    script+='local move_sites='+mvnset+'\n'
    for kind in ('nmi','irq','brk','cop'):
        script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();local sp=s['cpu.sp'];local ps=byte(sp+1)
 local target=(byte(sp+4)<<16)|word(sp+2)
 if active then hit.{kind}=hit.{kind}+1 end
 if move_sites[target] and mvn_hit.{kind} then mvn_hit.{kind}=mvn_hit.{kind}+1 end
 local saved={{}};for i=0,15 do saved[i]=word(0x02+i*2) end
 frames[target]=frames[target] or {{}};table.insert(frames[target],{{s=s,sp=sp,ps=ps,saved=saved,kind='{kind}'}})
 if not irq_hooks[target] then irq_hooks[target]=true
 emu.addMemoryCallback(function()
  if #frames[target]==0 then return end
  local f=table.remove(frames[target]);local t=emu.getState()
  -- Mesen can report a resumed MVN at its repeated byte fetch, after one
  -- transfer. Accept only that exact A/X/Y transition and verify the byte
  local stepped=move_sites[target] and t['cpu.a']==((f.s['cpu.a']-1)&65535)
    and t['cpu.x']==((f.s['cpu.x']+1)&65535) and t['cpu.y']==((f.s['cpu.y']+1)&65535)
  if stepped then assert(byte(0x7e0000|f.s['cpu.y'])==byte((byte(target+2)<<16)|f.s['cpu.x']),'resumed MVN byte') end
  for _,k in ipairs({{'a','x','y','d','dbr'}}) do
   local expected=f.s['cpu.'..k]
   if stepped and k=='a' then expected=(expected-1)&65535 end
   if stepped and (k=='x' or k=='y') then expected=(expected+1)&65535 end
   assert(t['cpu.'..k]==expected,f.kind..' '..k..' expected='..expected..' actual='..t['cpu.'..k]..' target='..target..' ps='..f.ps)
  end
  assert(t['cpu.sp']==f.sp+4 and t['cpu.ps']==f.ps,'interrupt stack/status')
  for i=0,15 do assert(word(0x02+i*2)==f.saved[i],'interrupt scratch '..i) end
 end,emu.callbackType.exec,target,target) end
end,emu.callbackType.exec,{sy['literal_'+kind]&65535},{sy['literal_'+kind]&65535})
'''
    script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0,'return '..s['cpu.a']);assert(s['cpu.sp']==1279,'main stack')
 assert(hit.nmi>0 and hit.irq>0,'hardware interrupt coverage')
 {'assert(mvn_hit.nmi>0 and mvn_hit.irq>0,"interrupted MVN coverage")' if meta['expect_mvn'] else ''}
 {'assert(fallback>0,"source bank fallback")' if meta['expect_fallback'] else ''}
 {'assert(hit.brk>0 and hit.cop>0,"software interrupt coverage")' if meta['traps'] else ''}
 emu.log('PASS {region} nmi='..hit.nmi..' irq='..hit.irq..' mvn-nmi='..mvn_hit.nmi..' mvn-irq='..mvn_hit.irq..' fallback='..fallback);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1
        config.DisableFrameSkipping=True;config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        (home/'check.lua').write_text(script);core.load(stem.with_suffix('.sfc'),home/'check.lua',script);core.start();core.wait_for('PASS',90)
        return next(x for x in core.log().splitlines() if x.startswith('PASS '))
    finally:core.close_with_log(home/'check.log')

def main():
    p=argparse.ArgumentParser();p.add_argument('--worker',type=Path);p.add_argument('--region');args=p.parse_args()
    if args.worker:print(execute(args.worker,args.region));return
    OUT.mkdir(parents=True,exist_ok=True);c.OUT=OUT;original=c.run
    helper=OUT/'enable.o';c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',helper,ROOT/'tests/far_loop_interrupts.s'])
    source=(ROOT/'tests/literal-copies.c').read_text();report={}
    for mode,layout,traps in [('optimized','normal',False),('disabled','normal',False),
                              ('optimized','large-edge',False),('optimized','tiny-edge',False),
                              ('optimized','normal',True),('optimized','large-edge',True)]:
        name=mode+'-'+layout+('-traps' if traps else '');banked=layout!='normal';stem=OUT/name
        def run(cmd,*a,**kw):
            if Path(cmd[0]).name=='zicc.exe' and mode=='disabled':cmd=[*cmd,'--no-copy-selection']
            if traps and Path(cmd[0]).name=='ca65.exe' and Path(cmd[-1]).name==name+'.s':
                path=Path(cmd[-1]);text=path.read_text()
                for target in ('literal_copy','tiny_copy'):
                    start=text.index('_'+target+':\n');end=text.index('__size_'+target,start)
                    body=text[start:end];body=re.sub(r'(?m)^(    [a-z]{3}(?: [^\n]*)?)$',r'    .byte $00,$00\n    .byte $02,$00\n\1',body)
                    text=text[:start]+body+text[end:]
                path.write_text(text)
            return original(cmd,*a,**kw)
        c.run=run
        case=('#define BANKED_LITERAL_TEST\n' if banked else '')+source
        if traps:case=case.replace('i<4000','i<128')
        c.compile_case(name,case,extra_objects=[helper,ROOT/'build/libc.a',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
        assembly=stem.with_suffix('.s').read_text()
        body=lambda n:assembly.split('_'+n+':\n',1)[1].split('__size_'+n,1)[0]
        assert 'jsr .loword(_strcpy)' in body('dynamic_copy')
        if mode=='optimized':
            assert 'literal strcpy: mvn 31 bytes' in body('literal_copy')
            assert 'literal strcpy: inline 3 bytes' in body('tiny_copy')
        else:assert 'literal strcpy:' not in assembly
        if banked:
            sy=symbols(stem);target='literal_copy' if layout=='large-edge' else 'tiny_copy'
            literal=re.search(r'(str_\w+_\d+)',body(target))[1]
            offset=sy[literal]-min(v for n,v in sy.items() if n.startswith('str_'))
            runbase=(0x7efff0 if layout=='large-edge' else 0x7effff)-offset
            cfg=(ROOT/'linker/lorom32.cfg').read_text().replace('MEMORY {',f'MEMORY {{\n    LITERAL: start = ${runbase:06X}, size = $10000, type = rw, file = "";')
            cfg=cfg.replace('RODATA:     load = ROM,     type = ro, optional = yes, align = $0002;',
                            'RODATA: load = ROM, run = LITERAL, type = rw, optional = yes, define = yes;')
            config=stem.with_suffix('.cfg');config.write_text(cfg)
            original([c.CC65/'ld65.exe','-C',config,'-Ln',stem.with_suffix('.labels'),'-o',stem.with_suffix('.raw'),ROOT/'build/startup.o',stem.with_suffix('.o'),helper,ROOT/'build/libc.a',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o',ROOT/'build/nmi.o',ROOT/'build/vectors.o',ROOT/'build/rom_header.o'])
            original([ROOT/'build/romtool.exe',stem.with_suffix('.raw'),stem.with_suffix('.sfc'),ROOT/'tests/title.txt'])
            sy=symbols(stem);assert sy[literal]==(0x7efff0 if layout=='large-edge' else 0x7effff),(literal,sy[literal])
        stem.with_suffix('.json').write_text(json.dumps(dict(banked=banked,traps=traps,expect_mvn=mode=='optimized' and layout!='large-edge' and not traps,expect_fallback=mode=='disabled' or layout=='large-edge')))
        for region in ('ntsc','pal'):
            result=original([sys.executable,__file__,'--worker',stem,'--region',region],timeout=120).stdout.strip()
            report[name+'-'+region]=result;print(name,result,flush=True)
        report[name+'-rom-sha256']=hashlib.sha256(stem.with_suffix('.sfc').read_bytes()).hexdigest()
    c.run=original
    custom='''unsigned calls;char b[8];
char *strcpy(char *d,const char * __far s){++calls;d[0]='Z';d[1]=0;return d;}
int main(void){return strcpy(b,"hello")!=b||calls!=1||b[0]!='Z'||b[1]!=0;}
'''
    _,rom,labels=c.compile_case('custom-definition',custom,
        extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
    assert 'literal strcpy:' not in (OUT/'custom-definition.s').read_text()
    report['custom-definition']=c.emulate(rom,labels,0)
    report['compiler-sha256']=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: literal lengths/NUL/return/evaluation; inline/MVN/disabled/custom/dynamic; bank edges and NTSC/PAL interrupts')
if __name__=='__main__':main()
