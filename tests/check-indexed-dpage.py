"""Verify full-width native DP,X with D=0 for writable array cursors."""
import os
import importlib.util,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'indexed-dpage-check'
spec=importlib.util.spec_from_file_location('strength_checks',Path(__file__).with_name('check-strength.py'));checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
CASES={
 'stack_pages':'''int main(void){int a[130],i;for(i=0;i<130;i++)a[i]=i*3+7;for(i=0;i<130;i++)if(a[i]!=i*3+7)return 1;return 0;}''',
 'global_pages':'''unsigned long data[80];void fill(unsigned long *p){int i;for(i=0;i<80;i++)p[i]=0x12340000UL+(unsigned long)i;}int main(void){int i;fill(data);for(i=0;i<80;i++)if(data[i]!=0x12340000UL+(unsigned long)i)return 1;return 0;}''',
 'word_results':'''int change(int *p){int i,old;for(i=0;i<4;i++){old=p[i]++;if(old!=i+1)return 1;p[i]+=3;if(++p[i]!=i+6)return 2;}return 0;}int main(void){int a[4];a[0]=1;a[1]=2;a[2]=3;a[3]=4;if(change(a))return 1;return a[3]!=9;}''',
 'long_results':'''int main(void){long a[3],old;int i;for(i=0;i<3;i++){a[i]=0xfffeL+i;old=a[i]++;if(old!=0xfffeL+i)return 1;a[i]+=5L;if(a[i]!=0xfffeL+i+6)return 2;if(--a[i]!=0xfffeL+i+5)return 3;}return 0;}''',
 'rom_readonly':'''extern const unsigned long table[4];int sum(const unsigned long * __far p){int i;unsigned long n=0;for(i=0;i<4;i++)n+=p[i];return n!=10UL;}int main(void){return sum(table);}''',
}

def main():
 OUT.mkdir(parents=True, exist_ok=True);checks.OUT=OUT;report={}
 table=OUT/'table.s';table.write_text('.export _table\n.segment "RODATA"\n_table: .dword 1,2,3,4\n',encoding='ascii')
 checks.support.run([checks.support.CC65/'ca65.exe','--cpu','65816','-g','-o',OUT/'table.o',table])
 for name,source in CASES.items():
  host=OUT/(name+'-host.c');host.write_text(source+('\nconst unsigned long table[4]={1,2,3,4};' if name=='rom_readonly' else ''),encoding='ascii');exe=OUT/(name+'-host.exe')
  checks.support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(OUT/(name+'-host.obj')),'/Fe'+str(exe),host]);assert subprocess.run([str(exe)],timeout=5).returncode==0,name
  extra=(OUT/'table.o',) if name=='rom_readonly' else ()
  pair={k:checks.build(name+'_'+k,source,True,indexed_dpage=k=='dp',extra_objects=extra) for k in ('absolute','dp')}
  if name in ('rom_readonly','global_pages','word_results'):assert 'z:$0000,x' not in pair['dp']['assembly']
  else:assert 'z:$0000,x' in pair['dp']['assembly']
  report[name]={k:dict(master_clocks=v['master_clocks']) for k,v in pair.items()}
  print('PASS '+name,flush=True)
 (OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':main()
