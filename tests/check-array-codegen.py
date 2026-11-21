"""Check that array reads and writes use the right address and evaluate the destination only as often as C requires."""
import os
import importlib.util,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'array-check'
spec=importlib.util.spec_from_file_location('support',Path(__file__).with_name('check-compiler.py'))
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
CASES={
'local_byte_displacement': '''#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
NEVER int observe(const unsigned char *a,int i){return a[i];}
NEVER int write_byte(int i,unsigned char v){
 unsigned char a[4]={10,20,30,40};
 a[i]=v;
 return observe(a,i)+observe(a,(i+1)&3);
}
int main(void){return write_byte(3,180)!=190||write_byte(1,90)!=120;}''',
 'fixed':'''long globals[3];int main(void){int a[3];unsigned char b[3];a[0]=9;a[1]=-4;a[2]=32000;b[0]=255;b[1]=128;b[2]=7;globals[0]=0x12345678L;globals[1]=-1234567L;globals[2]=99;if(a[0]!=9||a[1]!=-4||a[2]!=32000)return 1;if(b[0]!=255||b[1]!=128||b[2]!=7)return 2;if(globals[0]!=0x12345678L||globals[1]!=-1234567L||globals[2]!=99)return 3;return 0;}''',
 'dynamic':'''int main(void){int a[4];int *p=a;int i=1;long wide=0x12345678L;a[0]=10;a[1]=20;a[2]=30;a[3]=40;p[i]=p[i-1];p[i+1]=77;p[i+2]=(short)wide;if(a[0]!=10||a[1]!=10||a[2]!=77||a[3]!=22136)return 1;p=a+1;p[-1]=9;if(a[0]!=9)return 2;if((p[0]=123)!=123||a[1]!=123)return 3;return 0;}''',
 'side_effects':'''int first[2];int second[2];int *p;int calls;int change(void){p=second;return 42;}int next(void){++calls;return 1;}int main(void){p=first;first[0]=10;first[1]=20;second[0]=30;second[1]=40;p[0]=change();
#ifdef __ZICC__
if(first[0]!=42||second[0]!=30)return 1;
#else
if(!((first[0]==42&&second[0]==30)||(first[0]==10&&second[0]==42)))return 1;
#endif
p=first;p[next()]=77;if(calls!=1||first[1]!=77)return 2;*p++=99;if(p!=first+1||first[0]!=99)return 3;return 0;}''',
 'adjacent_bytes':'''int main(void){unsigned char a[4];unsigned char *p=a;int i=1;a[0]=255;a[1]=128;a[2]=7;a[3]=9;if((p[i]=p[i-1])!=255)return 1;if(a[0]!=255||a[1]!=255||a[2]!=7||a[3]!=9)return 2;a[0]=128;a[i]=a[i-1];if(a[1]!=128||a[2]!=7)return 3;return 0;}''',
 'indirect_updates':'''int calls;int **choose(int **p){++calls;return p;}
#ifdef __ZICC__
__noinline
#endif
int *advance(int **slot){return (*choose(slot))++;}
int main(void){int a[3];int *p=a+1,*old;int **slot=&p;
 old=advance(slot);if(calls!=1||old!=a+1||p!=a+2)return 1;
 if(--*choose(slot)!=a+1||p!=a+1||calls!=2)return 2;
 a[0]=7;a[1]=9;(void)*(*choose(slot))--;if(p!=a||calls!=3||a[1]!=9)return 3;
 *(*choose(slot))++=12;if(calls!=4||p!=a+1||a[0]!=12)return 4;return 0;}''',
 'indirect_long_transfers':'''typedef unsigned long Word;
#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
int visits;
NEVER Word *visit(Word *p){++visits;return p;}
NEVER void move(Word *in,Word *out,int i){Word temp=in[i];out[i]=temp;}
NEVER void scale(Word *in,Word *out,int i){Word temp=2UL*visit(in)[i];visit(out)[i]=temp;}
NEVER void shift(Word *in,Word *out,int i){Word temp=in[i]<<1;out[i]=temp;}
Word elements[3];
NEVER void double_pair(int i){Word first=elements[i]*2UL,second=elements[i+1]<<1;
 elements[i+1]=second;elements[i]=first;}
NEVER void double_overlap(int i,int j){Word first=elements[i]*2UL,second=elements[j]<<1;
 elements[i]=first;elements[j]=second;}
struct Fields {Word a,b,c,d;};
NEVER void field_transfer(struct Fields *out,struct Fields *in){
 out->a=in->b;out->c=in->a;in->b=0;in->d=0xabcd8001UL;
}
int main(void){Word a[3]={0x89AB8001UL,0x7FFF0001UL,55UL},b[3]={1UL,2UL,3UL};
 struct Fields to={11,12,13,14},from={0xcafe8002UL,0x12345678UL,33,34};
 move(a,b,0);if(b[0]!=0x89AB8001UL||b[1]!=2UL)return 1;
 scale(a,b,0);if(b[0]!=0x13570002UL||a[0]!=0x89AB8001UL||visits!=2)return 2;
 shift(a,a,1);if(a[1]!=0xFFFE0002UL||a[2]!=55UL||b[2]!=3UL)return 3;
 elements[0]=0x33458001UL;elements[1]=0xf123ffffUL;elements[2]=77;
 double_pair(0);
 if(elements[0]!=0x668b0002UL||elements[1]!=0xe247fffeUL||elements[2]!=77)return 4;
 double_overlap(0,0);if(elements[0]!=0xcd160004UL||elements[1]!=0xe247fffeUL)return 5;
 field_transfer(&to,&from);
 if(to.a!=0x12345678UL||to.c!=0xcafe8002UL||from.b||from.d!=0xabcd8001UL)return 6;
 field_transfer(&to,&to);
 if(to.a!=12||to.c!=12||to.b||to.d!=0xabcd8001UL)return 7;
 return 0;}''',
 'assigned_subscript':'''#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
int calls;
NEVER unsigned char value(unsigned char n){++calls;return n;}
NEVER int private_index(unsigned char n){unsigned char a[3]={9,5,7},i;
 a[i=257U]=value(n);
 return a[i]+i+a[0]+a[2];}
NEVER void redirect_index(int *i){*i=2;}
NEVER int escaped_index(unsigned char n){unsigned char a[3]={9,5,7};int i;
 a[i=1]=value(n);
 redirect_index(&i);
 return a[i]+a[1];}
NEVER int folded_updates(unsigned char n){unsigned char a[3]={9,5,7},i=255;
 a[++i]=value(n);a[i++]=value(n+1);a[i--]=value(n+2);
 return a[0]+a[1]+a[2]+i;}
int main(void){if(private_index(34)!=51||calls!=1)return 1;
 if(escaped_index(62)!=69||calls!=2)return 2;
 if(folded_updates(10)!=30||calls!=5)return 3;
 return 0;}''',
 'pointer_table':'''#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
NEVER int fixed_table(int seed){int *p[5],data[15],i;
 for(i=0;i<5;++i)p[i]=data+3*i;
 *p[1]=seed;p[4][0]=seed+1;
 return data[3]+data[12]+i;}
NEVER int dynamic_table(int slot){int *p[5],data[15],i;
 data[6]=0;
 for(i=0;i<5;++i)p[i]=&data[i*3];
 *p[slot]=17;
 return data[6]+i;}
NEVER void redirect(int **p,int *replacement){p[1]=replacement;}
NEVER int escaped_table(void){int *p[5],data[15],i,replacement=0;
 for(i=0;i<5;++i)p[i]=data+3*i;
 redirect(p,&replacement);*p[1]=23;
 return replacement;}
int main(void){if(fixed_table(11)!=28)return 1;
 if(dynamic_table(2)!=22)return 2;
 if(escaped_table()!=23)return 3;
 return 0;}''',
 'parallel_fill':'''#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
NEVER int check_fill(const short *words,const unsigned char *bytes,int end){
 int j;
 if(end!=0||words[0]!=91||bytes[0]!=83)return 1;
 for(j=1;j<10;++j)if(words[j]!=j||bytes[j]!=255)return 2;
 return 0;
}
NEVER int fill_pair(void){
 short words[10];unsigned char bytes[10];int i;
 words[0]=91;bytes[0]=83;
 for(i=9;i>0;--i){words[i]=i;bytes[i]=(unsigned char)-1;}
 return check_fill(words,bytes,i);
}
NEVER int check_wide_fill(const long *words,int end){
 int i;
 if(end!=7)return 3;
 for(i=0;i<10;++i)if(words[i]!=(long)i-3)return 4;
 return 0;
}
NEVER int fill_wide(void){long words[10];int i;
 for(i=-3;i<7;++i)words[i+3]=i;
 return check_wide_fill(words,i);
}
int main(void){int status=fill_pair();return status?status:fill_wide();}''',
 'fixed_scan':'''#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
int hits;
NEVER void hit(void){++hits;}
NEVER int scan(int value){
 int a[8]={1,value,value+1,value+3,value+4,value+1,value+5,value+6},i;
 for(i=7;i>0;--i)if(7==a[i])hit();
 return i;
}
struct Selection {int tag,values[2];} inputs;
int best;
NEVER int select_two(void){
 int i;
 for(i=0;i<2;++i)best=best>inputs.values[i]?best:inputs.values[i];
 return i;
}
int main(void){
 if(scan(6)!=0||hits!=2)return 1;
 if(scan(0)!=0||hits!=2)return 2;
 best=-32768;inputs.values[0]=-19;inputs.values[1]=17;
 if(select_two()!=2||best!=17)return 3;
 inputs.values[0]=-32768;inputs.values[1]=-23;
 if(select_two()!=2||best!=17)return 4;
 return 0;
}''',
 'x_addresses':'''int global_value;int next_value(void){return 41;}int probe(const int *p,int value){return *p+value;}int echo(int x){return x;}int main(void){int a=7,b=8;int values[2];int *p;unsigned char byte=255;long wide=0x12345678L;values[0]=9;values[1]=10;p=values;global_value=11;if(probe(&a,next_value())!=48)return 1;if(probe(&b,next_value())!=49)return 2;if(probe(values,next_value())!=50)return 3;if(probe(p,next_value())!=50)return 4;if(probe(&global_value,next_value())!=52)return 5;if(echo(byte)!=255||echo((short)wide)!=22136)return 6;return 0;}''',
 'near_word_pair':'''
#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
NEVER int sum_row(const int a[][2]){return a[1][0]+a[1][1];}
NEVER int reverse_pair(const int *p){return p[1]-p[0];}
NEVER int separate_pair(const int *p,const int *q){return p[0]+q[1];}
NEVER int volatile_pair(const volatile int *p){return p[0]+p[1];}
int main(void){
 int a[2][2]={{7,8},{-101,25}};
 if(sum_row(a)!=-76||reverse_pair(a[1])!=126)return 1;
 if(separate_pair(a[0],a[1])!=32||volatile_pair(a[1])!=-76)return 2;
 return 0;
}''',
 'results':'''int main(void){int a[3];int *p=a;unsigned char b[3];long c[2];int r;a[0]=1;a[1]=2;a[2]=3;r=(a[0]=a[1]=55);if(r!=55||a[0]!=55||a[1]!=55)return 1;r=(p[2]+=7);if(r!=10||a[2]!=10)return 2;b[0]=0;b[1]=7;b[2]=8;if((b[0]=255)!=255||b[1]!=7||b[2]!=8)return 3;c[0]=0;c[1]=0;if((c[0]=0x12345678L)!=0x12345678L||c[1]!=0)return 4;return 0;}''',
 'pointer_scan':'''
#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
int total;
NEVER void note(int value){total+=value;}
NEVER int walk(const int *first,const int *last,int threshold){
 const int *p;
 for(p=first;p<=last;++p)if(*p<threshold)note(threshold);
 return p-first;
}
int main(void){
 int a[3]={1,9,2};
 if(walk(a,a+2,4)!=3||total!=8)return 1;
 if(walk(a+1,a,4)!=0||total!=8)return 2;
 return 0;
}''',
}

def main():
 OUT.mkdir(parents=True, exist_ok=True);support.OUT=OUT;report={}
 for name,source in CASES.items():
  cfile,rom,labels=support.compile_case(name,source,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
  exe=OUT/(name+'-host.exe')
  support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/W4','/O2','/Fo'+str(OUT/(name+'-host.obj')),'/Fe'+str(exe),cfile])
  host=subprocess.run([str(exe)],timeout=5);assert host.returncode==0,(name,host.returncode)
  report[name]=support.emulate(rom,labels,0)
 # A fixed word element store must not manufacture a pointer or touch scratch
 source='''__noinline int check(const int *a){return a[0]!=9||a[1]!=-4||a[2]!=32000;}
 int main(void){int a[3];a[0]=9;a[1]=-4;a[2]=32000;return check(a);}'''
 _,rom,labels=support.compile_case('fixed_shape',source,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'],flags=['--no-dp-homes','--no-stack-frames'])
 assembly=(OUT/'fixed_shape.s').read_text()
 import re
 assert re.search(r'lda #\$0009\s+sta a:\$0001,y',assembly),assembly
 assert re.search(r'lda #\$7D00\s+sta a:\$0005,y',assembly),assembly
 support.emulate(rom,labels,0)
 advance=(OUT/'indirect_updates.s').read_text().split('_advance:\n',1)[1].split('__size_advance',1)[0]
 assert re.search(r'lda ([az]:\$[0-9A-F]+,x)\n    inc \1\n    inc \1',advance),advance
 local=(OUT/'local_byte_displacement.s').read_text().split('_write_byte:\n',1)[1].split('__size_write_byte',1)[0]
 assert re.search(r'    tya\n    clc\n    adc a:\$[0-9A-F]+,y\n    tax\n',local),local
 assert re.search(r'    sta a:\$(?!0000)[0-9A-F]{4},x',local),local
 # Reusing an index for a different loop must preserve the first loop's
 # live array cursor while removing the later unused cursor updates
 source='''__noinline int read_last(int *a,int n){return a[n-1];}
 __noinline int loops(int count,const int *p){
  int a[8],i,result;
  for(i=0;i<count;++i)a[i]=i+7;
  result=read_last(a,count);
  for(i=0;i<count;++i,++p)result+=*p;
  return result;
 }
 int main(void){const int data[4]={2,3,5,7};return loops(4,data)!=27;}'''
 for disabled in (False,True):
  flags=['--no-loop-index-retention','--no-index-elimination','--no-dp-homes','--no-stack-frames']
  if disabled:flags.append('--no-line-passes')
  path,rom,labels=support.compile_case(f'dead_cursor_steps_{int(disabled)}',source,flags=flags)
  loop=path.with_suffix('.s').read_text().split('_loops:\n',1)[1].split('__size_loops',1)[0]
  cursor=re.search(r'; strength cursor a\[i\], stride 2, frame \$([0-9A-F]+)',loop)
  assert cursor,loop
  tail=loop.split('jsr .loword(_read_last)',1)[1]
  assert ('sta a:$'+cursor[1]+',y' in tail)==disabled,loop
  support.emulate(rom,labels,0)
 transfers=(OUT/'indirect_long_transfers.s').read_text()
 fields=transfers.split('\n_field_transfer:\n',1)[1].split('__size_field_transfer',1)[0]
 assert '; shared structure pointers' in fields,fields
 for name in ('scale','shift'):
  part=transfers.split('\n_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert re.search(r'lda [az]:\$[0-9A-F]+,x\n    asl a\n    sta .*\n    lda [az]:\$[0-9A-F]+,x\n    rol a\n    sta ',part),part
 pair=transfers.split('\n_double_pair:\n',1)[1].split('__size_double_pair',1)[0]
 assert pair.count('    asl a:$0000,x\n    rol a:$0002,x\n')==2,pair
 subscript=(OUT/'assigned_subscript.s').read_text()
 for name in ('private_index','folded_updates'):
  assigned=subscript.split('\n_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert not re.search(r'\b(?:lda|sta) [az]:\$[0-9A-F]+,x',assigned),assigned
 tables=(OUT/'pointer_table.s').read_text()
 def table(name):return tables.split('\n_'+name+':\n',1)[1].split('__size_'+name,1)[0]
 assert 'loop lowering:' not in table('fixed_table'),table('fixed_table')
 assert 'loop lowering:' in table('dynamic_table'),table('dynamic_table')
 assert 'loop lowering:' in table('escaped_table'),table('escaped_table')
 fill=(OUT/'parallel_fill.s').read_text().split('\n_fill_pair:\n',1)[1].split('__size_fill_pair',1)[0]
 assert 'loop lowering:' not in fill and fill.count('    sep #$20\n')>=9,fill
 wide=(OUT/'parallel_fill.s').read_text().split('\n_fill_wide:\n',1)[1].split('__size_fill_wide',1)[0]
 assert 'loop lowering:' not in wide,wide
 scan=(OUT/'fixed_scan.s').read_text().split('\n_scan:\n',1)[1].split('__size_scan',1)[0]
 assert 'loop lowering:' not in scan and scan.count('jsr .loword(_hit)')==7,scan
 selects=(OUT/'fixed_scan.s').read_text().split('\n_select_two:\n',1)[1].split('__size_select_two',1)[0]
 assert 'loop lowering:' not in selects and '_inputs+$0002' in selects and '_inputs+$0004' in selects,selects
 walk=(OUT/'pointer_scan.s').read_text().split('\n_walk:\n',1)[1].split('__size_walk',1)[0]
 assert '; loop lowering: register pointer scan' in walk,walk
 pair=(OUT/'near_word_pair.s').read_text()
 for name,operation in (('sum_row','adc'),('reverse_pair','sbc'),('separate_pair',None),('volatile_pair',None)):
  body=pair.split('\n_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  if operation:assert f'{operation} a:$0000,x' in body,body
  else:assert 'adc a:$0000,x' not in body,body
 # X-only address consumers select register-specific forms at offsets 1/3/5
 # Keep explicit calls and a pointer home to exercise the X-load fallback
 support.compile_case('x_address_shapes',CASES['x_addresses'],extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'],flags=['--no-inline','--no-body-optimizations'])
 xasm=(OUT/'x_address_shapes.s').read_text()
 assert '    tyx\n    inx\n' in xasm
 assert '    tyx\n    inx\n    inx\n    inx\n' in xasm
 assert '    tya\n    clc\n    adc #$0005\n    tax\n' in xasm
 assert re.search(r'ldx a:\$[0-9A-F]+,y',xasm)
 (OUT/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('PASS: fixed word/byte/long arrays, dynamic/negative indices, RHS calls/aliasing, destination evaluated once, assignment results; MSVC and Mesen')

if __name__=='__main__':main()
