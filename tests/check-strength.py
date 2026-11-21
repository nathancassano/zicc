"""Differential checks and a controlled on/off timing for loop cursors."""
import os
import argparse,importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'strength-check'
spec=importlib.util.spec_from_file_location('support',Path(__file__).with_name('check-compiler.py'));support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
CASES={
 'copies_continue':'''int run(int *p){int i,j,total=0;for(i=0;i<4;i++){total+=p[i];j=i;total+=p[j];if(i==1)continue;total+=i;}return total*10+i;}int main(void){int a[4];a[0]=2;a[1]=4;a[2]=6;a[3]=8;return run(a)!=454;}''',
 'descending_result':'''int run(int *p){int i=3,old,total=0;while(i>=0){total+=p[i];old=i--;if(old!=i+1)return -1;}return total*10+i+1;}int main(void){int a[4];a[0]=3;a[1]=5;a[2]=7;a[3]=11;return run(a)!=260;}''',
 'steps_break':'''int run(int *p){int i,total=0;for(i=0;i<6;i+=2)total+=p[i];for(i=4;i>=0;i-=2)total+=p[i];if(i!=-2)return -1;for(i=0;i<6;i++){total+=p[i];if(i==2)break;}return total*10+i;}int main(void){int a[6];a[0]=1;a[1]=2;a[2]=3;a[3]=4;a[4]=5;a[5]=6;return run(a)!=242;}''',
 'multiple_widths':'''int main(void){int a[4],i;long b[4],total=0;for(i=0;i<4;i++){a[i]=i+1;b[i]=(long)(i+1)*10L;total+=a[i]+b[i];}if(i!=4||total!=110L)return 1;return 0;}''',
 'nonlinear_update':'''int run(int *p){int i,total=0;for(i=1;i<5;i*=2)total+=p[i];return total*10+i;}int main(void){int a[5];a[0]=1;a[1]=2;a[2]=3;a[3]=4;a[4]=5;return run(a)!=108;}''',
 'value_contexts':'''int observe(int x){return x;}int run(int *p){int i=0,j=0,n=0;while(i<3){n+=p[i];j=i++;if(observe(j)!=i-1)return 1;}if(i!=3||j!=2)return 2;i=1;n+=p[i];if((i=2)!=2)return 3;n+=p[i];if(++i!=3||i--!=3||i!=2)return 4;if(p[i]!=6)return 5;j=1;i=j+1;n+=p[i];n+=p[j];return n!=32;}int main(void){int a[4];a[0]=2;a[1]=4;a[2]=6;a[3]=8;return run(a);}''',
 'recursive':'''int run(int *p,int depth){int i,total=0;for(i=0;i<3;i++){total+=p[i];if(depth>0)total+=run(p,depth-1);}return total;}int main(void){int a[3];a[0]=1;a[1]=2;a[2]=3;return run(a,2)!=78;}''',
 'parameter_index':'''int run(int *p,int start,int count){int total=0;while(start<count){total+=p[start];start++;}return total*10+start;}int main(void){int a[4];a[0]=3;a[1]=5;a[2]=7;a[3]=11;if(run(a,1,4)!=234)return 1;if(run(a,2,2)!=2)return 2;return 0;}''',
 'unsigned_wrap':'''int main(void){int a[2],k=0,total=0;unsigned short i=65535U;a[0]=9;a[1]=13;while(k<3){++i;if(i<2)total+=a[i];k++;}if(i!=2||total!=22)return 1;return 0;}''',
 'escaped_index':'''int *escaped;void bump(int *p){escaped=p;++*p;}int run(int *p){int i=0,total=0;while(i<3){total+=p[i];bump(&i);}escaped=0;return total;}int main(void){int a[3];a[0]=1;a[1]=2;a[2]=3;return run(a)!=6;}''',
 'mutated_base':'''int run(int *p,int *q){int i,total=0;for(i=0;i<2;i++){total+=p[i];p=q;}return total;}int main(void){int a[2],b[2];a[0]=1;a[1]=2;b[0]=10;b[1]=20;return run(a,b)!=21;}''',
 'escaped_base':'''int **escaped;void swap(int **where,int *next){escaped=where;*where=next;}int run(int *p,int *q){int i,total=0;for(i=0;i<2;i++){total+=p[i];swap(&p,q);}escaped=0;return total;}int main(void){int a[2],b[2];a[0]=1;a[1]=2;b[0]=10;b[1]=20;return run(a,b)!=21;}''',
}

def build(name,source,enabled,indexed_dpage=False,extra_objects=(),branch_relaxation=True,debug_symbols=False,divmod_reuse=True,register_loops=True,required_imports=(),compiler=None,dp_counters=True,unroll=True,dp_homes=True,extra_flags=()):
 suffix='on' if enabled else 'off';stem=OUT/(name+'_'+suffix);cfile=stem.with_suffix('.c');cfile.write_text(source,encoding='ascii')
 command=[compiler or ROOT/'build/zicc.exe',cfile,'-o',stem.with_suffix('.s')]
 if not dp_counters:command.append('--no-dp-counters')
 if not dp_homes:command.append('--no-dp-homes')
 command+=list(extra_flags)
 if not unroll:command.append('--no-loop-unroll')
 if not enabled:command.append('--no-strength-reduction')
 if not indexed_dpage:command.append('--no-indexed-dpage')
 if not branch_relaxation:command.append('--no-branch-relaxation')
 if not divmod_reuse:command.append('--no-divmod-reuse')
 if not register_loops:command.append('--no-register-loops')
 support.run(command)
 assembly=stem.with_suffix('.s').read_text()
 imports=set(re.findall(r'^\.import (\S+)$',assembly,re.M))|set(required_imports)
 def exports(path):
  return {name.strip() for row in re.findall(r'^\.export (.*)$',path.read_text(),re.M) for name in row.split(',')}
 float_exports={name for p in (ROOT/'runtime/ieee32').glob('f*32.s') for name in exports(p)}
 integer_exports={name for p in (ROOT/'runtime/integers').glob('*.s') for name in exports(p)}
 floating=bool(imports&float_exports)
 runtime=[]
 if floating:runtime+=[ROOT/'build/arithmetic.o',ROOT/'build/ieee_engine.o']
 else:runtime.append(ROOT/'build/dp-scratch.o')
 if imports&integer_exports:runtime.append(ROOT/'build/integers.o')
 support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',stem.with_suffix('.o'),stem.with_suffix('.s')])
 support.run([support.CC65/'ld65.exe','-C',ROOT/'linker/lorom32.cfg','-m',stem.with_suffix('.map'),'--dbgfile',stem.with_suffix('.dbg'),'-Ln',stem.with_suffix('.labels'),'-o',stem.with_suffix('.raw'),ROOT/'build/startup.o',stem.with_suffix('.o'),*runtime,*extra_objects,ROOT/'build/nmi.o',ROOT/'build/vectors.o',ROOT/'build/rom_header.o'])
 support.run([ROOT/'build/romtool.exe',stem.with_suffix('.raw'),stem.with_suffix('.sfc'),ROOT/'tests/title.txt'])
 if debug_symbols:support.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',ROOT/'tools/labels-to-sym.ps1','-InputPath',stem.with_suffix('.labels'),'-OutputPath',stem.with_suffix('.sym')])
 labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
 lua=stem.with_suffix('.lua');lua.write_text(f'''local start=0
emu.addMemoryCallback(function()
 local entry=emu.getState()
 start=entry.masterClock
 local pc=emu.read16(((entry['cpu.sp']+1)&0x1ffff),emu.memType.snesWorkRam,false)
 local bank=emu.read(((entry['cpu.sp']+3)&0x1ffff),emu.memType.snesWorkRam,false)
 local target=(bank<<16)|((pc+1)&0xffff)
 emu.addMemoryCallback(function()
 local state=emu.getState()
 if state['cpu.a']~=0 or state['cpu.sp']~=0x04ff then error('return/stack failure: '..state['cpu.a']) end
 emu.log('CLOCKS '..(state.masterClock-start))
 print('PASS CLOCKS '..(state.masterClock-start));emu.stop(0)
 end,emu.callbackType.exec,target,target)
end,emu.callbackType.exec,{labels['main']},{labels['main']})
''',encoding='ascii')
 result=support.run([support.mesen_executable(OUT),'--testRunner','--doNotSaveSettings','--timeout=10',stem.with_suffix('.sfc'),lua])
 assert 'PASS CLOCKS' in result.stdout,result.stdout
 code_bytes=int(re.search(r'^CODE\s+\w+\s+\w+\s+(\w+)',stem.with_suffix('.map').read_text(),re.M)[1],16)
 return dict(master_clocks=int(re.search(r'PASS CLOCKS (\d+)',result.stdout)[1]),code_bytes=code_bytes,assembly=stem.with_suffix('.s').read_text())

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--list-parts',action='store_true');parser.add_argument('--part',choices=('core','affine-loops','dp-counters','loop-unroll'));args=parser.parse_args()
 if args.list_parts:print(json.dumps(['core','affine-loops','dp-counters','loop-unroll']));return
 if args.part and args.part!='core':
  support.run([sys.executable,ROOT/('tests/check-'+args.part+'.py')],timeout=600);return
 OUT.mkdir(parents=True, exist_ok=True);report={}
 for name,source in CASES.items():
  host=OUT/(name+'-host.c');host.write_text(source,encoding='ascii');exe=OUT/(name+'-host.exe')
  support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(OUT/(name+'-host.obj')),'/Fe'+str(exe),host])
  assert subprocess.run([str(exe)],timeout=5).returncode==0,name
  pair={k:build(name,source,k=='on') for k in ('off','on')}
  if name in ('escaped_index','mutated_base','escaped_base'):assert '; strength cursor' not in pair['on']['assembly'],name
  else:assert '; strength cursor' in pair['on']['assembly'],name
  report[name]={k:dict(master_clocks=v['master_clocks']) for k,v in pair.items()}
  print('PASS '+name,flush=True)
 source=(ROOT/'samples/insertion_sort.c').read_text()
 pair={k:build('insertion_sort',source,k=='on') for k in ('off','on')}
 before=pair['off']['assembly'].split('_insertion_sort:',1)[1].split('__size_insertion_sort',1)[0]
 after=pair['on']['assembly'].split('_insertion_sort:',1)[1].split('__size_insertion_sort',1)[0]
 assert re.search(r'^\s+asl a$',before,re.M) and not re.search(r'^\s+asl a$',after,re.M)
 assert 'strength cursor values[i]' in after and 'strength cursor values[j]' in after
 report['insertion_sort']={k:dict(master_clocks=v['master_clocks']) for k,v in pair.items()}
 (OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('PASS insertion_sort: '+str(report['insertion_sort']),flush=True)
 if args.part:return
 support.run([sys.executable,ROOT/'tests/check-affine-loops.py'],timeout=240)
 support.run([sys.executable,ROOT/'tests/check-dp-counters.py'],timeout=240)
 support.run([sys.executable,ROOT/'tests/check-loop-unroll.py'],timeout=240)

if __name__=='__main__':main()
