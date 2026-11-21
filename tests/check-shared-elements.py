"""Compare runs with and without reuse of the same structure element within an expression."""
import os
import argparse,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'shared-element-check'
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py');support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
CASES={}
CASES['strides']='''struct Six {short a;unsigned short b;short c;};
struct Item {short quantity;unsigned short id;unsigned long price;};
struct Nested {short head;struct Item item;short tail;};
unsigned long product(const struct Item *p,int i){return (unsigned long)p[i].quantity*p[i].price;}
long signed_product(const struct Six *p,int i){return (long)p[i].a*(long)p[i].c;}
unsigned long unsigned_product(const struct Six *p,int i){return (unsigned long)p[i].b*(unsigned long)p[i].b;}
short nested(const struct Nested *p,int i){return p[i].item.quantity+(short)p[i].item.price;}
int main(void){struct Six a[3];struct Item b[3];struct Nested c[2];int i;
 for(i=0;i<3;++i){a[i].a=-7;a[i].b=65535U;a[i].c=13;b[i].quantity=-2;b[i].price=125UL;}
 if(product(b,1)!=0xffffff06UL||signed_product(a,1)!=-91L||unsigned_product(a,2)!=0xfffe0001UL)return 1;
 if(product(b+1,-1)!=0xffffff06UL||signed_product(a+1,-1)!=-91L)return 3;
 i=1;if((unsigned long)b[i].quantity*b[i].price!=0xffffff06UL)return 4;
 c[1].item.quantity=-3;c[1].item.price=0x12340009UL;if(nested(c,1)!=6)return 2;
 return 0;}
'''
CASES['operations']='''struct Row {unsigned long a,b;short c,d;unsigned char e,f;};
unsigned long add(const struct Row *p,int i){return p[i].a+p[i].b;}
unsigned long sub(const struct Row *p,int i){return p[i].a-p[i].b;}
unsigned long bits(const struct Row *p,int i){return (p[i].a^p[i].b)|(p[i].a&p[i].b);}
unsigned long divide(const struct Row *p,int i){return p[i].a/p[i].b;}
unsigned long remainder(const struct Row *p,int i){return p[i].a%p[i].b;}
short words(const struct Row *p,int i){return p[i].c-p[i].d;}
short word_divide(const struct Row *p,int i){return p[i].c/p[i].d;}
short word_remainder(const struct Row *p,int i){return p[i].c%p[i].d;}
unsigned short bytes(const struct Row *p,int i){return p[i].e*p[i].f;}
int main(void){struct Row a[2];a[1].a=0xffffffffUL;a[1].b=2UL;a[1].c=-100;a[1].d=23;a[1].e=255;a[1].f=128;
 if(add(a,1)!=1UL||sub(a,1)!=0xfffffffdUL||bits(a,1)!=0xffffffffUL)return 1;
 if(divide(a,1)!=0x7fffffffUL||remainder(a,1)!=1UL||words(a,1)!=-123||bytes(a,1)!=32640U)return 2;
 if(word_divide(a,1)!=-4||word_remainder(a,1)!=-8)return 3;
 return 0;}
'''
CASES['forms']='''struct Item {short a,b;unsigned long c;};
unsigned long forms(const struct Item *p,int i){return (unsigned long)p[i].a*(p+i)->c;}
unsigned long affine(const struct Item *p,int i){return (unsigned long)p[i+1].a*p[i+1].c;}
unsigned long truncate(const struct Item *p,int i){return (unsigned long)(short)p[i].c*(unsigned long)p[i].b;}
unsigned long recursive(const struct Item *p,short n){if(!n)return 0UL;return forms(p,0)+recursive(p,(short)(n-1));}
int main(void){struct Item a[2];a[0].a=3;a[0].b=-2;a[0].c=0xffffUL;a[1].a=7;a[1].c=19UL;
 if(forms(a,0)!=196605UL||affine(a,0)!=133UL||truncate(a,0)!=2UL||recursive(a,4)!=786420UL)return 1;
 return 0;}
'''
CASES['effects']='''struct Item {short a,b;unsigned long c;};struct Item items[3];int calls,index_calls;
struct Item *next(void){++calls;return items;}
int next_index(void){int old=index_calls;++index_calls;return old;}
short call_both(void){return next()->a+next()->b;}
short indexed_calls(struct Item *p){return p[next_index()].a+p[next_index()].b;}
short increment(struct Item *p,int i){short first=p[i++].a;return first+p[i++].b;}
short mutate(struct Item *p,int i){short first=p[(i=1)].a;return first+p[(i=1)].b;}
short indirect(struct Item *p,int *i){return p[*i].a+p[*i].b;}
struct Floats {float a,b;};struct Floats floats[1];
float float_sum(const struct Floats *p,int i){return p[i].a+p[i].b;}
int main(void){int i=0;short value;items[0].a=2;items[0].b=3;items[1].a=5;items[1].b=7;
 if(call_both()!=5||calls!=2)return 1;
 if(increment(items,0)!=9||mutate(items,0)!=12)return 2;
 value=indexed_calls(items);if(index_calls!=2||(value!=9&&value!=8))return 3;
 if(indirect(items,&i)!=5)return 4;
 floats[0].a=1.5f;floats[0].b=2.25f;if(float_sum(floats,0)!=3.75f)return 5;
 return 0;}
'''
CASES['shapes']='''struct Item {short a,b;unsigned long c;};
unsigned long shared(const struct Item *p,int i){return (unsigned long)p[i].a*p[i].c;}
unsigned long different(const struct Item *p,int i,int j){return (unsigned long)p[i].a*p[j].c;}
unsigned long other(const struct Item *p,const struct Item *q,int i){return (unsigned long)p[i].a*q[i].c;}
short fixed(void){struct Item a[1];a[0].a=3;a[0].b=4;return a[0].a+a[0].b;}
int main(void){struct Item a[2];a[0].a=2;a[0].c=3UL;a[1].c=5UL;
 if(shared(a,0)!=6UL||different(a,0,1)!=10UL||other(a,a,0)!=6UL||fixed()!=7)return 1;return 0;}
'''
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);args=parser.parse_args()
 OUT.mkdir(parents=True, exist_ok=True);support.OUT=OUT;original=support.run;report={}
 extra=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o']
 for name,source in CASES.items():
  cfile,rom,labels=support.compile_case(name,source,extra_objects=extra)
  exe=OUT/(name+'-host.exe');support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(OUT/(name+'-host.obj')),'/Fe'+str(exe),cfile]);assert subprocess.run([str(exe)]).returncode==0,name
  report[name]=support.emulate(rom,labels,0)
  if args.baseline:
   def baseline(cmd,*a,**kw):
    if Path(cmd[0]).name=='zicc.exe':cmd=[args.baseline,*cmd[1:]]
    return original(cmd,*a,**kw)
   try:
    support.run=baseline;_,br,bl=support.compile_case(name+'-baseline',source,extra_objects=extra);support.emulate(br,bl,0)
   finally:support.run=original
  print('PASS shared element '+name,flush=True)
 def body(text,name):return text.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
 assembly=(OUT/'shapes.s').read_text();shared=body(assembly,'shared')
 assert shared.count('; shared element address')==1 and shared.count('    asl a\n')==3,shared
 assert 'lda a:$0002,x' not in shared # a is at offset zero here
 assert 'lda a:$0000,x' in shared and 'lda a:$0004,x' in shared and 'lda a:$0006,x' in shared
 for name in ('different','other','fixed'):assert '; shared element address' not in body(assembly,name)
 effects=(OUT/'effects.s').read_text()
 for name in ('call_both','indexed_calls','increment','mutate','indirect','float_sum'):assert '; shared element address' not in body(effects,name)
 strides=(OUT/'strides.s').read_text()
 for name in ('product','signed_product','unsigned_product','nested'):
  assert body(strides,name).count('; shared element address')==1
 for name in ('signed_product','unsigned_product','nested'):
  # Shared addresses still evaluate the displacement once; strides 6 and 12
  # now use the common inline word-scale selector rather than a helper call
  selected=body(strides,name)
  assert 'jsr .loword(__mul16)' not in selected
  assert selected.count('    asl a\n')==(3 if name=='nested' else 2)
 assert '__mul16wide' in body(strides,'signed_product') and '__mul16wide' in body(strides,'unsigned_product')
 forms=(OUT/'forms.s').read_text()
 for name in ('forms','affine','truncate'):assert body(forms,name).count('; shared element address')==1
 (OUT/'results.json').write_text(json.dumps(dict(cases=report,compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256(args.baseline.read_bytes()).hexdigest() if args.baseline else None),indent=2)+'\n')
 print('PASS: five MSVC/Mesen cases, optional paired baseline; strides, casts, arithmetic, nesting, calls/updates and shared-address/fallback shapes')
if __name__=='__main__':main()
