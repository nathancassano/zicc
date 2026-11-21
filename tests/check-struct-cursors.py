"""Run structure-array loops with and without pointer stepping. Check the results and when the compiler uses it."""
import os
import argparse,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'struct-cursor-check'
spec=importlib.util.spec_from_file_location('strength',ROOT/'tests/check-strength.py');strength=importlib.util.module_from_spec(spec);spec.loader.exec_module(strength)
S='struct Item {short value;unsigned short tag;unsigned long price;};'
CASES={
'control':S+'''int run(const struct Item *p){int i,total=0;for(i=0;i<6;i++){if(i==1)continue;total+=p[i].value;if(i==4)break;}if(i!=4||total!=13)return 1;
for(i=4;i>=0;i-=2)total+=p[i].value;if(i!=-2||total!=22)return 2;
i=0;do{total+=p[i].value;++i;}while(i<2);if(i!=2||total!=25)return 3;
i=1;while(i<6){total+=p[i].value;i*=2;}if(i!=8||total!=35)return 4;
return 0;}
int main(void){struct Item p[6];int k;for(k=0;k<6;++k)p[k].value=(short)(k+1);return run(p);}''',
'values':S+'''int run(const struct Item *p){int i=0,j=0,total=0,old;
while(i<3){total+=p[i].value;j=i++;if(j!=i-1)return 1;}
i=1;total+=p[i].value;if((i=2)!=2)return 2;total+=p[i].value;if(++i!=3||i--!=3||i!=2)return 3;
j=1;i=j+1;total+=p[i].value;total+=p[j].value;
old=i++;if(old!=2||i!=3)return 4;if(total!=32)return 5;return 0;}
int main(void){struct Item p[4];int k;for(k=0;k<4;++k)p[k].value=(short)(2*(k+1));return run(p);}''',
'strides':'''struct Six {short a,b,c;};struct Twelve {short head;struct Six data;unsigned long tail;};
int sum(const struct Six *p,const struct Twelve *q,int start,int end){int total=0;while(start<end){total+=p[start].a+q[start].data.b;start++;}return total*10+start;}
int main(void){struct Six p[4];struct Twelve q[4];int i;
for(i=0;i<4;++i){p[i].a=(short)(i+1);q[i].data.b=(short)(2*(i+1));}
if(sum(p,q,1,4)!=274||sum(p,q,2,2)!=2||sum(p+1,q+1,-1,0)!=30||sum(0,0,0,0)!=0)return 1;return 0;}''',
'local_rom':'''struct Six {short a,b,c;};const struct Six rom[3]={{1,2,3},{4,5,6},{7,8,9}};
const short words[3]={2,4,6};
int main(void){struct Six local[3];int i,j,total=0;for(i=0;i<3;++i){local[i].a=(short)(i+1);total+=rom[i].b+words[i];}
for(i=0;i<3;++i){j=i;total+=local[j].a;}
for(i=0;i<2;++i)total+=local[i+1].a;total+=local[i-1].a;
if(total!=40||i!=2)return 1;return 0;}''',
'recursive':S+'''unsigned long run(const struct Item *p,int depth){int i;unsigned long total=0;for(i=0;i<3;++i){total+=p[i].price;if(depth)total+=run(p,depth-1);}return total;}
int main(void){struct Item p[3];p[0].price=1UL;p[1].price=2UL;p[2].price=3UL;return run(p,2)!=78UL;}''',
'escaped_index':S+'''int *escaped;void bump(int *p){escaped=p;++*p;}
int run(const struct Item *p){int i=0,total=0;while(i<3){total+=p[i].value;bump(&i);}escaped=0;return total;}
int main(void){struct Item a[3];a[0].value=1;a[1].value=2;a[2].value=3;return run(a)!=6;}''',
'mutated_base':S+'''int run(struct Item *p,struct Item *q){int i,total=0;for(i=0;i<2;++i){total+=p[i].value;p=q;}return total;}
int main(void){struct Item a[2],b[2];a[0].value=1;a[1].value=2;b[0].value=10;b[1].value=20;return run(a,b)!=21;}''',
'escaped_base':S+'''struct Item **escaped;void swap(struct Item **p,struct Item *q){escaped=p;*p=q;}
int run(struct Item *p,struct Item *q){int i,total=0;for(i=0;i<2;++i){total+=p[i].value;swap(&p,q);}escaped=0;return total;}
int main(void){struct Item a[2],b[2];a[0].value=1;a[1].value=2;b[0].value=10;b[1].value=20;return run(a,b)!=21;}''',
'wrap':S+'''int main(void){struct Item a[2];unsigned short i=65535U;int k=0,total=0;a[0].value=9;a[1].value=13;while(k<3){++i;if(i<2)total+=a[i].value;k++;}return i!=2||total!=22;}''',
'negative':S+'''int run(const struct Item *p,int i){int total=0;while(i<1){total+=p[i].value;++i;}return total;}
int main(void){struct Item a[3];a[0].value=2;a[1].value=3;a[2].value=5;if(run(a+1,-1)!=5||run(a,1)!=0||run(0,1)!=0)return 1;return 0;}''',
}
CASES['control_six']=CASES['control'].replace(S,'struct Item {short value;unsigned short tag;short extra;};')
CASES['values_six']=CASES['values'].replace(S,'struct Item {short value;unsigned short tag;short extra;};')

# The selector must be independent of function/field names and layout, preserve
# signed widening and modulo-32-bit arithmetic, and decline observable indices,
# changing bounds/bases, calls, and casts which alter a field's value
REDUCTION=S+'''struct Item data[5]={{-32768,0,0xFFFFFFFFUL},{-1,0,0x80000001UL},
{0,0,0x12345678UL},{32767,0,0x0001FFFFUL},{2,0,0xFFFFFFFFUL}};
unsigned long reduce(const struct Item *p,int count){unsigned long total=0;int i;
for(i=0;i<count;++i)total+=(unsigned long)p[i].value*p[i].price;
return total;}
int main(void){if(reduce(0,0)||reduce(0,-1)||reduce(0,-32768))return 1;
if(reduce(data,1)!=32768UL||reduce(data,2)!=0x80007FFFUL||reduce(data,3)!=0x80007FFFUL)return 2;
if(reduce(data,4)!=0x7FFE0000UL||reduce(data,5)!=0x7FFDFFFEUL)return 3;
if(reduce(data+1,1)!=0x7FFFFFFFUL||reduce(data+3,2)!=0xFFFD7FFFUL)return 4;return 0;}'''
REDUCTIONS={
 'signed_overflow':(REDUCTION,True),
 'stride_twelve':(REDUCTION.replace(S,'struct Item {unsigned long pad;short value;unsigned short tag;unsigned long price;};').replace('{{-32768,0,','{{0,-32768,0,').replace('},{-1,0,','},{0,-1,0,').replace('{0,0,0x12345678','{0,0,0,0x12345678').replace('{32767,0,','{0,32767,0,').replace('{2,0,','{0,2,0,'),True),
 'post_increment':(REDUCTION.replace('++i)','i++)'),True),
 'block_body':(REDUCTION.replace('total+=(unsigned long)p[i].value*p[i].price;','{total+=(unsigned long)p[i].value*p[i].price;}'),True),
 'live_index':(REDUCTION.replace('return total;','if(i!=count&&count>0)return 1UL;return total;'),False),
 'changed_bound':(REDUCTION.split('int main(void)')[0].replace('total+=(unsigned long)p[i].value*p[i].price;','{total+=(unsigned long)p[i].value*p[i].price;--count;}')+'int main(void){return reduce(data,5)!=0x80007FFFUL;}',False),
 'changed_base':(REDUCTION.split('int main(void)')[0].replace('total+=(unsigned long)p[i].value*p[i].price;','{total+=(unsigned long)p[i].value*p[i].price;++p;}')+'int main(void){return reduce(data,3)!=32766UL;}',False),
 'cast_chain':(REDUCTION.replace('(unsigned long)p[i].value','(unsigned long)(short)(unsigned long)p[i].value'),False),
 'extra_call':(REDUCTION
     .replace('unsigned long reduce','''volatile unsigned visits;
#ifdef __ZICC__
__noinline
#endif
void record_visit(void){++visits;}
unsigned long reduce''')
     .replace('total+=(unsigned long)p[i].value*p[i].price;',
              '{record_visit();total+=(unsigned long)p[i].value*p[i].price;}')
     .replace('return 4;return 0;','return 4;return visits!=18U;'),False),
}
def body(assembly,name):return assembly.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);args=parser.parse_args()
 OUT.mkdir(parents=True, exist_ok=True);strength.OUT=OUT;report={};original=strength.support.run
 for name,source in CASES.items():
  host=OUT/(name+'-host.c');host.write_text(source);exe=host.with_suffix('.exe')
  original([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(exe),host]);assert subprocess.run([str(exe)]).returncode==0,name
  pair={kind:strength.build(name,source,kind=='on',indexed_dpage=True) for kind in ('off','on')}
  if name in ('escaped_index','mutated_base','escaped_base'):assert '; strength cursor' not in body(pair['on']['assembly'],'run'),name
  else:assert '; strength cursor' in pair['on']['assembly'],name
  if name=='strides':assert 'stride 6,' in pair['on']['assembly'] and 'stride 12,' in pair['on']['assembly']
  if name=='local_rom':assert 'lda z:$0000,x' not in pair['on']['assembly']
  if args.baseline:
   def baseline(command,*a,**kw):
    if Path(command[0]).name=='zicc.exe':command=[args.baseline,*command[1:]]
    return original(command,*a,**kw)
   try:strength.support.run=baseline;strength.build(name+'-baseline',source,True,indexed_dpage=True)
   finally:strength.support.run=original
  report[name]={kind:dict(master_clocks=v['master_clocks'],code_bytes=v['code_bytes']) for kind,v in pair.items()}
  print('PASS struct cursor '+name,flush=True)
 for name,(source,selected) in REDUCTIONS.items():
  host=OUT/(name+'-host.c');host.write_text(source);exe=host.with_suffix('.exe')
  original([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(exe),host]);assert subprocess.run([str(exe)]).returncode==0,name
  pair={kind:strength.build(name,source,kind=='on',indexed_dpage=True) for kind in ('off','on')}
  assert ('; counted reduction:' in body(pair['on']['assembly'],'reduce'))==selected,name
  assert '; counted reduction:' not in pair['off']['assembly'],name
  if selected:
   after=body(pair['on']['assembly'],'reduce')
   assert 'frame 8' in after and '    pea $0000\n    pea $0000\n' in after and '    phx\n    lda a:' not in after
   assert pair['on']['master_clocks']<pair['off']['master_clocks'],name
  report[name]={kind:dict(master_clocks=v['master_clocks'],code_bytes=v['code_bytes']) for kind,v in pair.items()}
  print('PASS counted reduction '+name,flush=True)
 catalog=(ROOT/'samples/structures_and_tables.c').read_text().replace(' __far ',' ').replace('const struct Item catalog','struct Item catalog');pair={kind:strength.build('catalog',catalog,kind=='on',indexed_dpage=True) for kind in ('off','on')}
 after=body(pair['on']['assembly'],'inventory_value');before=body(pair['off']['assembly'],'inventory_value')
 assert '; counted reduction: stride 8, frame 8' in after and '    adc #$0008\n' in after and '    asl a\n' not in after
 assert '    asl a\n' in before and pair['on']['master_clocks']<pair['off']['master_clocks']
 report['catalog']={k:dict(master_clocks=v['master_clocks'],code_bytes=v['code_bytes']) for k,v in pair.items()}
 (OUT/'results.json').write_text(json.dumps(dict(cases=report,compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest() if args.baseline else None),indent=2)+'\n')
 print(f'PASS: {len(CASES)} cursor and {len(REDUCTIONS)} counted-reduction MSVC/Mesen on/off cases, optional baseline, catalog shape/timing, alias/control-flow guards')
if __name__=='__main__':main()
