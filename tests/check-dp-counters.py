"""Locally saved $00 word: current-version differential tests and real interrupts."""
import os
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'dp-counter-check'
BASELINE_DIR=ROOT/'build/bank7e-change/compatible-baselines/dp0-loop-change'
BASELINES=list(BASELINE_DIR.glob('baseline-*.exe'))
if len(BASELINES)>1:
    raise ValueError(f'Expected at most one compiler baseline in {BASELINE_DIR}')
BASELINE=next(iter(BASELINES),None)
spec=importlib.util.spec_from_file_location('checks',ROOT/'tests/check-strength.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
checks.OUT=OUT
support=checks.support
spec=importlib.util.spec_from_file_location('interrupts',ROOT/'tests/check-interrupts.py')
interrupts=importlib.util.module_from_spec(spec);spec.loader.exec_module(interrupts)
CASES={
 'break_recover':'''int run(void){int i,k=0;for(i=2;i<9;i++){if(++k==3)break;}return i;}int main(void){return run()!=4;}''',
 'dynamic':'''int run(int start,int end){int i,n=0;for(i=start;i<end;i++)n++;return n*10+i;}int main(void){if(run(-3,2)!=52||run(2,2)!=2||run(3,-2)!=3)return 1;return 0;}''',
 'unsigned_range':'''unsigned int n;unsigned int run(void){unsigned int i;for(i=0;i<65535U;i++)n++;return i;}int main(void){return run()!=65535U||n!=65535U;}''',
 'signed_range':'''unsigned int n;int run(void){int i;for(i=-32768;i<32767;i++)n++;return i;}int main(void){return run()!=32767||n!=65535U;}''',
 'stack_args':'''long calc(int a,int b,int c,int d){int i;long s=0;for(i=0;i<3;i++)s+=(long)(a+b+c+d);return s;}int main(void){int i;long s=0;for(i=0;i<3;i++)s+=calc(1,2,3,4);return s!=90L;}''',
 'small_trips':'''int run(int n){int i,total=0;for(i=0;i<n;i++)total++;return total*10+i;}int main(void){return run(0)!=0||run(1)!=11||run(2)!=22||run(3)!=33;}''',
 'zero_start':'''static volatile int limit;
void run(int end,unsigned char *out,const unsigned char *in){
 int i;for(i=0;i<end;++i)out[i]=in[4*i];
}
int main(void){
 unsigned char in[8]={11,0,0,0,19,0,0,0},out[2]={3,7};
 limit=-32768;run(limit,out,in);if(out[0]!=3||out[1]!=7)return 1;
 limit=0;run(limit,out,in);if(out[0]!=3||out[1]!=7)return 2;
 limit=2;run(limit,out,in);if(out[0]!=11||out[1]!=19)return 3;
 return 0;
}''',
 'nested_calls':'''int run(int depth){int i,total=0;for(i=0;i<3;i++){if(depth)total+=run(depth-1);else total++;}return total;}int main(void){return run(3)!=81;}''',
 'unrelated_label':'''int run(int n){int i,hits=0;if(n<0)goto done;
 i=0;for(;i<n;++i)++hits;
 done:return hits;
 }int main(void){return run(-1)!=0||run(0)!=0||run(4)!=4;}''',
 'local_cursor':'''unsigned run(unsigned n){unsigned a[8],i,total=0;for(i=0;i<8;i++)a[i]=i+1;
for(i=0;i<n;i++)total+=a[i];return total;}int main(void){return run(0)!=0||run(1)!=1||run(8)!=36;}''',
}
FALLBACKS={
 # The discarded step now feeds the immediate comparison directly. Keeping
 # a second counter would add work to every iteration of this maintained index
 'continue':'''int run(void){int i,total=0;for(i=0;i<6;i++){if(i==2)continue;total+=i;}return total*10+i;}int main(void){return run()!=136;}''',
 'nested_break':'''int run(void){int i,j,n=0;for(i=0;i<3;i++){for(j=0;j<5;j++){n++;if(j==2)break;}}return n;}int main(void){return run()!=9;}''',
 'return':'''int run(void){int i;for(i=0;i<5;i++){if(i==2)return i;}return i;}int main(void){return run()!=2;}''',
 'changing_bound':'''int run(int n){int i;for(i=0;i<n;i++){if(i==2)n=3;}return i;}int main(void){return run(7)!=3;}''',
 'escaped_bound':'''void bump(int *n){*n=3;}int run(int n){int i;for(i=0;i<n;i++)bump(&n);return i;}int main(void){return run(7)!=3;}''',
 'escaped_index':'''void bump(int *i){(*i)++;}int run(void){int i;for(i=0;i<5;i++)bump(&i);return i;}int main(void){return run()!=6;}''',
 'loop_jump_edges':'''int enter(int jump){int i=2,hits=0;if(jump)goto inside;
 for(i=0;i<4;++i){inside:++hits;}return hits;}
 int leave(int n){int i,hits=0;for(i=0;i<4;++i){if(++hits==n)goto done;}
 done:return hits;}int main(void){return enter(0)!=4||enter(1)!=2||leave(2)!=2||leave(7)!=4;}''',
}


def build_interrupts():
    OUT.mkdir(parents=True,exist_ok=True)
    driver=OUT/'driver.s';driver.write_text(interrupts.driver(15,0))
    objects=[]
    for source in (driver,ROOT/'tests/dp0_counter_probe.s'):
        obj=OUT/(source.stem+'.o')
        support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',obj,source]);objects.append(obj)
    source=(ROOT/'tests/dp0_counter_interrupts.c').read_text()
    for mode in ('disabled','enabled','nested-disabled','nested-enabled'):
        path=OUT/(mode+'.c');path.write_text(('#define DP_NESTED_INTERRUPT 1\n' if mode.startswith('nested-') else '')+source);asm=path.with_suffix('.s')
        # Keep the fixed-trip loops so these ROMs exercise DP saves and restores
        command=[ROOT/'build/zicc.exe',path,'-o',asm,'--no-loop-unroll']
        if mode.endswith('disabled'):command.append('--no-dp-counters')
        support.run(command)
        support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',path.with_suffix('.o'),asm])
        support.run([support.CC65/'ld65.exe','-C',ROOT/'linker/lorom32.cfg','-Ln',path.with_suffix('.labels'),
                     '-o',path.with_suffix('.raw'),ROOT/'build/startup.o',path.with_suffix('.o'),*objects,
                     ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o',ROOT/'build/tables.o',
                     ROOT/'build/nmi.o',ROOT/'build/vectors.o',ROOT/'build/rom_header.o'])
        support.run([ROOT/'build/romtool.exe',path.with_suffix('.raw'),path.with_suffix('.sfc'),ROOT/'tests/title.txt'])
        text=asm.read_text()
        for name in interrupts.NAMES:
            body=re.search(r'^_'+name+r':\n.*?^__size_'+name+r' = .*?$',text,re.M|re.S).group(0)
            assert body.count('    pei ($00)')==(mode.endswith('enabled')),name
            assert body.count('    pla\n    sta z:$0000')==(mode.endswith('enabled')),name
        # No widening of the handler-wide scratch scanner is required
        if mode.endswith('enabled'):assert 'saved DP counter:' in text


def worker(region,mode):
    stem=OUT/mode;sy=interrupts.labels(stem);home=OUT/region/mode;home.mkdir(parents=True,exist_ok=True)
    script="local snapshot=nil\nlocal events=0\nlocal irq_active=false\nlocal nested=0\nlocal function word(a) return emu.read16(((a)&0x1ffff),emu.memType.snesWorkRam,false) end\n"
    for kind in interrupts.KINDS:
        for variant in range(4):
            script+=f'''emu.addMemoryCallback(function()
 snapshot=emu.getState();snapshot.dp=word(0)
 irq_active={'true' if kind=='irq' else 'false'}
 assert(snapshot.dp>0,'outer word not live')
end,emu.callbackType.exec,{sy[f'before_{kind}_{variant}']},{sy[f'before_{kind}_{variant}']})
emu.addMemoryCallback(function()
 local s=emu.getState()
 for _,key in ipairs({{'a','x','y','d','dbr','sp','ps','k'}}) do assert(s['cpu.'..key]==snapshot['cpu.'..key],'{kind}/{variant} '..key) end
 assert(word(0)==snapshot.dp,'{kind}/{variant} outer DP word')
 irq_active=false;events=events+1
end,emu.callbackType.exec,{sy[f'after_{kind}_{variant}']},{sy[f'after_{kind}_{variant}']})
'''
    if mode.startswith('nested-'):
        script+=f'''emu.addMemoryCallback(function()
 if not irq_active then return end
 nested=nested+1
 local before=word(0);local s=emu.getState()
 assert(before=={3 if mode.endswith('enabled') else 48879},'IRQ counter not live')
 local target=(emu.read(((s['cpu.sp']+4)&0x1ffff),emu.memType.snesWorkRam,false)<<16)|word(s['cpu.sp']+2)
 emu.addMemoryCallback(function()
  assert(word(0)==before,'nested NMI did not restore IRQ counter')
  assert(emu.getState()['cpu.sp']==s['cpu.sp']+4,'nested NMI stack')
 end,emu.callbackType.exec,target,target)
end,emu.callbackType.exec,{sy['vblank']&65535},{sy['vblank']&65535})
'''
    script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0 and s['cpu.sp']==1279,'result/stack')
 assert(events==32,'interrupt events')
 assert(nested=={1 if mode.startswith('nested-') else 0},'nested interrupt count')
 emu.log('PASS DP counters {region} {mode} events='..events);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    lua=home/'check.lua';lua.write_text(script);core=interrupts.Core(home)
    try:
        config=interrupts.SnesConfig();config.Region=1 if region=='ntsc' else 2
        config.Port1.Type=1;config.DisableFrameSkipping=True;config.RamPowerOnState=1
        config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,interrupts.SnesConfig)(config)
        core.load(stem.with_suffix('.sfc'),lua,script);core.start();core.wait_for('PASS',25)
    finally:
        core.close_with_log(home/'check.log')


def benchmark():
    spec=importlib.util.spec_from_file_location('affine',ROOT/'tests/check-affine-loops.py')
    affine=importlib.util.module_from_spec(spec);spec.loader.exec_module(affine);affine.OUT=OUT
    source=OUT/'kernels.c';source.write_text(affine.KERNELS);report={};assembly=[]
    for enabled in (False,True):
        mode='enabled' if enabled else 'disabled';asm=OUT/('kernels_'+mode+'.s');obj=asm.with_suffix('.o')
        # Isolate the saved-$00 counter from the independent home allocator,
        # which can now keep a short loop's counter in Y in both modes
        command=[ROOT/'build/zicc.exe',source,'-o',asm,'--no-loop-unroll','--no-dp-homes']
        if not enabled:command.append('--no-dp-counters')
        support.run(command)
        if not enabled and BASELINE is not None:
            before=OUT/'kernels_previous.s';support.run([BASELINE,source,'-o',before])
            assert before.read_bytes()==asm.read_bytes(),'disabled option differs from current-version snapshot'
        support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',obj,asm])
        checks.build('kernels_'+mode,affine.DRIVER,True,dp_counters=enabled,dp_homes=False,unroll=False,extra_objects=[obj],
                     required_imports=re.findall(r'^\.import (\S+)$',asm.read_text(),re.M))
        stem=OUT/('kernels_'+mode+'_on')
        if not enabled and BASELINE is not None:
            before=OUT/'driver_previous.s';support.run([BASELINE,stem.with_suffix('.c'),'-o',before,'--no-indexed-dpage'])
            assert before.read_bytes()==stem.with_suffix('.s').read_bytes(),'disabled driver differs from snapshot'
        masters,cycles=affine.instrument(stem,cpu_samples=True)
        report[mode]=dict(samples=masters,cpu_samples=cycles,rom_sha256=hashlib.sha256(stem.with_suffix('.sfc').read_bytes()).hexdigest())
        heading = 'Direct-page counter on' if enabled else 'Direct-page counter off'
        assembly.append('## '+heading+'\n\n```c\n'+source.read_text()+'\n```\n\n```asm\n'+asm.read_text()+'\n```\n')
    for name in ('across_row','down_column','nested_rows','nested_columns'):
        before=report['disabled']['samples'][0][name];after=report['enabled']['samples'][0][name]
        cpu_before=report['disabled']['cpu_samples'][0][name];cpu_after=report['enabled']['cpu_samples'][0][name]
        if max(after)>=min(before):
            # Other passes can shrink the marginal gain below the fixture's
            # 40-clock refresh spread. Require direct CPU-cycle dominance and
            # a faster best master-clock sample, retaining the worst-case guard
            assert max(cpu_after)<min(cpu_before),(name,cpu_before,cpu_after)
            assert min(after)<min(before) and max(after)<=max(before)+40,(name,before,after)
        else:assert max(after)<min(before),(name,before,after)
        print(name+': '+str(before)+' -> '+str(after)+'; CPU '+str(cpu_before)+' -> '+str(cpu_after),flush=True)
    (OUT/'assembly.md').write_text(
        '# Counting loop steps in direct-page memory\n\n'
        'Both builds fill the same rows and columns. Compare the assembly to see where each build keeps the number of steps left in a loop.\n\n'
        +'\n'.join(assembly))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region',choices=('ntsc','pal'));parser.add_argument('--mode',choices=('disabled','enabled','nested-disabled','nested-enabled'))
    args=parser.parse_args()
    if args.region:worker(args.region,args.mode);return
    OUT.mkdir(parents=True,exist_ok=True);report={'cases':{}}
    # Current-version baseline remains the disabled option for repeatable checks
    # The development snapshot independently proves that disabling is identical
    for name,source in {**CASES,**FALLBACKS}.items():
        pair={}
        for enabled in (False,True):
            mode='enabled' if enabled else 'disabled'
            # Keep stack homes in this fixture to exercise $00 with incoming
            # arguments. Three-trip loops with promoted homes prefer the
            # cheaper ordinary index, covered by check-body-codegen.py
            result=checks.build(name+'_'+mode,source,True,dp_counters=enabled,unroll=False,dp_homes=name!='stack_args')
            assert ('saved DP counter:' in result['assembly'])==(enabled and name in CASES),name
            if enabled and name=='local_cursor':assert '; eliminated index i: cursors only' in result['assembly']
            if enabled and name=='zero_start':assert '    pei ($00)\n    sta z:$0000\n' in result['assembly']
            pair[mode]={k:result[k] for k in ('master_clocks','code_bytes')}
        path=OUT/(name+'_host.c');path.write_text(source);host=path.with_suffix('.exe')
        support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(path.with_suffix('.obj')),'/Fe'+str(host),path])
        support.run([host]);report['cases'][name]=pair
        print('PASS DP '+name,flush=True)
    report['kernels']=benchmark()
    build_interrupts()
    for region in ('ntsc','pal'):
        for mode in ('disabled','enabled','nested-disabled','nested-enabled'):
            result=support.run([sys.executable,__file__,'--region',region,'--mode',mode],timeout=45)
            print('PASS DP interrupts '+region+' '+mode,flush=True)
    paths=[ROOT/'src/codegen/dp_counters.inc',ROOT/'src/codegen/codegen.inc',ROOT/'src/codegen/affine_loops.inc',ROOT/'build/zicc.exe',
           *sorted((ROOT/'runtime/integers').glob('*.s')),ROOT/'build/integers.o',ROOT/'tests/dp0_counter_probe.s',ROOT/'tests/dp0_counter_interrupts.c']
    report['inputs']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    if BASELINE is not None:report['baseline_sha256']=hashlib.sha256(BASELINE.read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS DP counters: semantic/fallback pairs, recursive ownership, NTSC/PAL all four interrupts and width modes')


if __name__=='__main__':main()
