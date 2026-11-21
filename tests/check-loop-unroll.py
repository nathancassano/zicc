"""Costed loop forms: current-version differential semantics, tails and execution."""
import os
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'loop-unroll-check'
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support);support.OUT=OUT


def block(text,name):
    return re.search(r'^_'+name+r':\n.*?^__size_'+name+r' = .*?$',text,re.M|re.S).group(0)


def semantics():
    path=OUT/'semantics.c';path.write_text((ROOT/'tests/unroll_cases.c').read_text());assemblies={};roms={}
    for enabled in (False,True):
        mode='enabled' if enabled else 'disabled';stem=OUT/('semantics_'+mode)
        command=[ROOT/'build/zicc.exe',path,'-o',stem.with_suffix('.s')]
        if not enabled:command.append('--no-loop-unroll')
        support.run(command);assemblies[mode]=stem.with_suffix('.s').read_text()
        support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',stem.with_suffix('.o'),stem.with_suffix('.s')])
        support.run([support.CC65/'ld65.exe','-C',ROOT/'linker/lorom32.cfg','-Ln',stem.with_suffix('.labels'),
                     '--dbgfile',stem.with_suffix('.dbg'),'-o',stem.with_suffix('.raw'),ROOT/'build/startup.o',stem.with_suffix('.o'),
                     *[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables','nmi','vectors','rom_header')],
                     ROOT/'build/libc.a'])
        support.run([ROOT/'build/romtool.exe',stem.with_suffix('.raw'),stem.with_suffix('.sfc'),ROOT/'tests/title.txt'])
        labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
        support.emulate(stem.with_suffix('.sfc'),labels,0)
        roms[mode]=hashlib.sha256(stem.with_suffix('.sfc').read_bytes()).hexdigest()
    host=OUT/'reference.exe';support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2',
        '/Fo'+str(OUT/'reference.obj'),'/Fe'+str(host),path]);support.run([host])
    text=assemblies['enabled'];assert '; cost unroll:' not in assemblies['disabled']
    for name in ('fill','indices','byte_fill','wide_fill','real_fill','large_fill','column_fill','fixed_33'):
        assert '; cost unroll: partial' in block(text,name),name
    for name in ('five_reloads','negative_start','affine_start','fixed_32','short_two','wrapped_start'):
        assert '; cost unroll: full' in block(text,name),name
    for name in ('negative_start','affine_start','short_two','wrapped_start'):
        assert 'known initial index, direct X' in block(text,name),name
    single=block(text,'short_one')
    assert 'loop lowering:' not in single and single.count('sta a:')==1
    assert 'lda #$0003\nreturn_short_one = *\n    rts' in single,single
    assert re.findall(r'^    [^;].*',block(text,'dead_empty'),re.M)==['    rts']
    for name in ('cast_start','retained_objects','wide_after','recursive_after'):
        assert '; eliminated induction home:' in block(text,name),name
    assert '; entry-only cursor leaf: no frame' in block(text,'dynamic_offset')
    for name in ('short_two','short_one','wrapped_start','fill'):
        assert '; eliminated induction home:' not in block(text,name),name
    for name in ('negative_start',):
        assert '; visible final index: constant recovery' in block(text,name),name
    assert block(text,'five_reloads').count('lda a:.loword(_global_value)')==5,'global value incorrectly hoisted'
    assert '; cost unroll:' not in block(text,'reverse'),'negative displacement fallback'
    for body in re.findall(r'; cost unroll: [^\n]*bytes (\d+)',text):assert int(body)<=128
    sizes={mode:{name:int(value,16) for name,value in re.findall(r'name="__size_([^"]+)"[^\n]*?val=0x([0-9A-Fa-f]+)',
        (OUT/('semantics_'+mode+'.dbg')).read_text())} for mode in ('disabled','enabled')}
    for name,size in sizes['enabled'].items():
        # The 128-byte budget applies to each selected region. A function
        # such as main contains several independently costed loops
        regions=block(text,name).count('; cost unroll:')
        assert size<=sizes['disabled'][name]+128*max(1,regions),(name,size,sizes['disabled'][name],regions)
    return dict(roms=roms,code_bytes=sizes)


def ownership_build():
    spec=importlib.util.spec_from_file_location('dp',ROOT/'tests/check-dp-counters.py')
    dp=importlib.util.module_from_spec(spec);spec.loader.exec_module(dp)
    home=OUT/'interrupts';home.mkdir(parents=True,exist_ok=True)
    driver=home/'driver.s';driver.write_text(dp.interrupts.driver(15,0))
    objects=[]
    for path in (driver,ROOT/'tests/dp0_counter_probe.s'):
        obj=home/(path.stem+'.o');support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',obj,path]);objects.append(obj)
    source=(ROOT/'tests/dp0_counter_interrupts.c').read_text()
    source='unsigned char unroll_bytes[2][8];long unroll_wide[2][8];\n'+source
    for slot in (0,2,3):
        original=f'    for(i=0;i<3;i++) counts[{slot}]++;'
        source=source.replace(original,original+'\n    for(i=0;i<5;i++) unroll_bytes[1][i]=211;\n    for(i=0;i<3;i++) unroll_wide[1][i]=0x12345678L;')
    head,tail=source.split('int main(void)',1)
    tail=tail.replace('    return 0;', '''    if(unroll_bytes[1][4]!=211 || unroll_wide[1][2]!=0x12345678L) return 4;
    if(unroll_bytes[0][0] || unroll_bytes[1][5] || unroll_wide[0][0] || unroll_wide[1][3]) return 5;
    return 0;''')
    source=head+'int main(void)'+tail
    for mode in ('disabled','enabled'):
        stem=home/mode;stem.with_suffix('.c').write_text(source)
        command=[ROOT/'build/zicc.exe',stem.with_suffix('.c'),'-o',stem.with_suffix('.s')]
        if mode=='disabled':command.append('--no-loop-unroll')
        support.run(command)
        text=stem.with_suffix('.s').read_text()
        assert text.count('; cost unroll: full')==(6 if mode=='enabled' else 0)
        support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',stem.with_suffix('.o'),stem.with_suffix('.s')])
        support.run([support.CC65/'ld65.exe','-C',ROOT/'linker/lorom32.cfg','-Ln',stem.with_suffix('.labels'),
                     '-o',stem.with_suffix('.raw'),ROOT/'build/startup.o',stem.with_suffix('.o'),*objects,
                     *[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables','nmi','vectors','rom_header')]])
        support.run([ROOT/'build/romtool.exe',stem.with_suffix('.raw'),stem.with_suffix('.sfc'),ROOT/'tests/title.txt'])


def ownership_worker(region,mode):
    spec=importlib.util.spec_from_file_location('dp',ROOT/'tests/check-dp-counters.py')
    dp=importlib.util.module_from_spec(spec);spec.loader.exec_module(dp);dp.OUT=OUT/'interrupts'
    sy=dp.interrupts.labels(dp.OUT/mode);core_type=dp.interrupts.Core
    class AuditCore(core_type):
        def load(self,rom,path,script):
            for kind in dp.interrupts.KINDS:
                for variant in range(4):
                    before=sy[f'before_{kind}_{variant}'];after=sy[f'after_{kind}_{variant}']
                    script+=f'''emu.addMemoryCallback(function()
 for i=0x02,0x21 do emu.write(((i)&0x1ffff),(i*37+{variant})&255,emu.memType.snesWorkRam) end
end,emu.callbackType.exec,{before},{before})
emu.addMemoryCallback(function()
 for i=0x02,0x21 do assert(emu.read(((i)&0x1ffff),emu.memType.snesWorkRam,false)==((i*37+{variant})&255),'unrolled handler scratch') end
end,emu.callbackType.exec,{after},{after})
'''
            path.write_text(script);super().load(rom,path,script)
    dp.interrupts.Core=AuditCore;dp.worker(region,mode)


def dynamic_measure(stem):
    labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
    script=f'''local active=nil
local samples={{}}
local targets={{}}
emu.addMemoryCallback(function()
 assert(active==nil,'nested dynamic call')
 local s=emu.getState();local n=#samples
 assert(s['cpu.a']==n and s['cpu.x']=={labels['matrix']&65535},'dynamic arguments')
 assert(emu.read16(((s['cpu.sp']+3)&0x1ffff),emu.memType.snesWorkRam,false)==73,'dynamic value')
 active={{n=n,clock=s.masterClock,writes=0}}
 local target=(s['cpu.k']<<16)|((emu.read16(((s['cpu.sp']+1)&0x1ffff),emu.memType.snesWorkRam,false)+1)&65535)
 if not targets[target] then
  targets[target]=true
  emu.addMemoryCallback(function()
   assert(emu.getState()['cpu.a']==active.n,'dynamic final index')
   assert(active.writes==active.n*2,'dynamic write count')
   samples[#samples+1]=emu.getState().masterClock-active.clock;active=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{labels['runtime_row']},{labels['runtime_row']})
emu.addMemoryCallback(function() if active then active.writes=active.writes+1 end end,
emu.callbackType.write,{0x7e0000|(labels['matrix']&65535)},{(0x7e0000|(labels['matrix']&65535))+319})
emu.addMemoryCallback(function()
 assert(emu.getState()['cpu.a']==0 and emu.getState()['cpu.sp']==1279,'dynamic result/stack')
 assert(#samples==66 and active==nil,'dynamic call count')
 print('SAMPLES '..table.concat(samples,','));print('PASS');emu.stop(0)
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
    path=stem.with_name(stem.name+'_measure.lua');path.write_text(script);runs=[]
    for _ in range(3):
        result=support.run([support.mesen_executable(OUT),'--testRunner','--doNotSaveSettings','--timeout=10',stem.with_suffix('.sfc'),path])
        assert 'PASS' in result.stdout,result.stdout+result.stderr
        runs.append(list(map(int,re.search(r'SAMPLES ([0-9,]+)',result.stdout)[1].split(','))))
    assert runs[0]==runs[1]==runs[2]
    return runs


def benchmark():
    spec=importlib.util.spec_from_file_location('affine',ROOT/'tests/check-affine-loops.py')
    affine=importlib.util.module_from_spec(spec);spec.loader.exec_module(affine);affine.OUT=OUT
    checks=affine.checks;checks.OUT=OUT;path=OUT/'kernels.c'
    path.write_text(affine.KERNELS+'''int runtime_row(int m[][80],int n,int value){int j;for(j=0;j<n;j++)m[1][j]=value;return j;}
''')
    report={};examples=[]
    for enabled in (False,True):
        mode='enabled' if enabled else 'disabled';stem=OUT/('kernels_'+mode)
        command=[ROOT/'build/zicc.exe',path,'-o',stem.with_suffix('.s')]
        if not enabled:command.append('--no-loop-unroll')
        support.run(command)
        support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',stem.with_suffix('.o'),stem.with_suffix('.s')])
        checks.build('driver_'+mode,affine.DRIVER,True,unroll=enabled,extra_objects=[stem.with_suffix('.o')],
                     required_imports=re.findall(r'^\.import (\S+)$',stem.with_suffix('.s').read_text(),re.M))
        driver=OUT/('driver_'+mode+'_on')
        report[mode]=dict(samples=affine.instrument(driver),rom_sha256=hashlib.sha256(driver.with_suffix('.sfc').read_bytes()).hexdigest())
        dynamic='''int runtime_row(int m[][80],int n,int value);int matrix[2][80];
int main(void){int n,i,j;for(n=0;n<=65;n++){
 for(i=0;i<2;i++)for(j=0;j<80;j++)matrix[i][j]=-99;
 if(runtime_row(matrix,n,73)!=n)return 1;
 for(i=0;i<2;i++)for(j=0;j<80;j++){
  if(i==1&&j<n){if(matrix[i][j]!=73)return 2;}else if(matrix[i][j]!=-99)return 3;
 }}return 0;}
'''
        checks.build('dynamic_'+mode,dynamic,True,unroll=enabled,extra_objects=[stem.with_suffix('.o')],
                     required_imports=re.findall(r'^\.import (\S+)$',stem.with_suffix('.s').read_text(),re.M))
        report[mode]['dynamic']=dynamic_measure(OUT/('dynamic_'+mode+'_on'))
        text=stem.with_suffix('.s').read_text()
        if enabled:
            assert text.count('; cost unroll: full')==4
            assert '; cost unroll: partial' in block(text,'runtime_row')
            for name in ('across_row','down_column','nested_rows','nested_columns'):
                body=block(text,name)
                assert '__mul16' not in body,name+' still uses stride helper'
                assert 'known initial index, direct X' in body,name
                assert '; eliminated induction home:' in body,name
                if name in ('across_row','down_column','nested_rows','nested_columns'):
                    assert '; entry-only cursor leaf: no frame' in body,name
                    assert ',y' not in body and not re.search(r'^\s+(?:ph[axy]|pl[axy]|tcs)\b',body,re.M),name
            # Incoming stack arguments no longer prevent whole-function DP
            # homes: the runtime loop can be entered without allocating six
            # bytes, while its value argument remains an incoming N,s home
            runtime=block(text,'runtime_row')
            assert 'sbc #$0006' not in runtime.split(';',1)[0]
            assert re.search(r'    lda \d+,s',runtime)
            assert '; eliminated induction home:' not in block(text,'runtime_row')
        heading = 'Unrolling on' if enabled else 'Unrolling off'
        examples.append('## '+heading+'\n\n```c\n'+path.read_text()+'\n```\n\n```asm\n'+text+'\n```\n')
    for name in ('across_row','down_column','nested_rows','nested_columns'):
        before=report['disabled']['samples'][0][name];after=report['enabled']['samples'][0][name]
        assert max(after)<min(before),(name,before,after)
        print(name+': '+str(before)+' -> '+str(after),flush=True)
    assert report['enabled']['dynamic'][0][32]<report['disabled']['dynamic'][0][32]
    for n in (0,1,2,3,8,15,16,17,31,32,33,64,65):
        print('runtime '+str(n)+': '+str(report['disabled']['dynamic'][0][n])+' -> '+str(report['enabled']['dynamic'][0][n]),flush=True)
    (OUT/'assembly.md').write_text(
        '# Repeating the loop body in assembly\n\n'
        'Unrolling copies the loop body so that a program can do more work between loop tests. Compare the same C functions with this choice switched off and on.\n\n'
        +'\n'.join(examples))
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region',choices=('ntsc','pal'));parser.add_argument('--mode',choices=('disabled','enabled'))
    args=parser.parse_args()
    if args.region:ownership_worker(args.region,args.mode);return
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(semantics=semantics(),kernels=benchmark())
    ownership_build()
    for region in ('ntsc','pal'):
        for mode in ('disabled','enabled'):
            support.run([sys.executable,__file__,'--region',region,'--mode',mode],timeout=45)
            print('PASS unrolled handler ownership '+region+' '+mode,flush=True)
    paths=[ROOT/'build/zicc.exe',ROOT/'src/codegen/loop_unroll.inc',ROOT/'tests/unroll_cases.c',Path(__file__),
           *sorted((ROOT/'runtime/integers').glob('*.s')),ROOT/'build/integers.o',ROOT/'build/startup.o',OUT/'kernels.c',OUT/'driver_disabled_on.c']
    report['inputs']={str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p):
                      hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS loop unrolling: current-version/MSVC semantics, all runtime tails, widths, live indices, cost budgets and repeated opaque kernels')


if __name__=='__main__':main()
