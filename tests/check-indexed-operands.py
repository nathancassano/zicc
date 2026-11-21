"""Check which array accesses can use indexed instructions and when the compiler needs its usual address calculation."""
import importlib.util,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('indexed_support',ROOT/'tests/check-compiler.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
OUT=support.OUT

SOURCE=r'''
#include <stdint.h>
int words[16];
unsigned bits[16];
int8_t bytes[16];
struct Row { char a,b,c; } rows[16];
union Buffer { unsigned char bytes[64]; unsigned word; } buffer;
volatile int opaque;
int calls,index_value;
int addend;
__noinline int get_index(void){calls++;return index_value;}
__noinline int change(void){index_value=7;words[1]=100;return 7;}
__noinline int read_word(int i){return words[i];}
__noinline int read_byte(int i){return bytes[i];}
__noinline int arithmetic(int a,int i){return (a+words[i])^(a-words[i]);}
__noinline unsigned bitops(unsigned n,int i){return (n+bits[i])^(n-bits[i])^(n&bits[i])^(n|bits[i]);}
__noinline int fixed_fallback(void){return words[2];}
__noinline int compare(int a,int i){return (a<words[i])+2*(a>words[i])+4*(a==words[i]);}
__noinline int scaled(int i,int v){buffer.bytes[i*4+3]=v;return buffer.bytes[i*4+3];}
__noinline int member(int i,int v){rows[i].c=v;return rows[i].c;}
__noinline int compound(int i,int n){words[i]+=n;words[i]-=n;words[i]^=n;words[i]^=n;return words[i];}
__noinline void indexed_sum(int i){words[i]=words[i]+addend;}
__noinline int snapshot(void){index_value=1;words[1]=3;int i=get_index();words[i]+=change();return words[1];}
__noinline int once(void){index_value=3;return words[get_index()]=17;}
__noinline int nested(int a){return a+words[get_index()];}
volatile unsigned char volatile_bytes[4];
__noinline int volatile_fallback(int i){volatile_bytes[i]=3;return volatile_bytes[i];}
long wide[4];
__noinline long wide_fallback(int i,long n){wide[i]=n;return wide[i];}
__noinline int local_fallback(int i){int a[4];a[i]=9;return a[i];}
__noinline int pointer_fallback(int *p,int i){return p[i];}
extern unsigned edge[8];
__noinline unsigned boundary(int i,unsigned n){edge[i]=n;return edge[i];}
struct Pair { unsigned x,y; } src[8],dst[8];
__noinline void parallel(unsigned count){
 struct Pair *p=src,*q=dst;
 struct Pair *end=src+count;
 while(p!=end){
  if(p->x==99){p->x=3;continue;}
  q->x=p->x+q->y;
  q->y=p->y;
  p++;q++;
 }
}
__noinline unsigned casted(unsigned off){
 return *(unsigned*)((unsigned char*)src+2+off)+*(unsigned*)((unsigned char*)dst+off);
}
struct Writer { unsigned *next; unsigned sum,position; } writer;
static void append_pair(unsigned x,unsigned y){
 *writer.next++=x;
 *writer.next++=y;
 writer.sum+=x+y;
 if(++writer.position==2)writer.position=0;
}
__noinline void append_many(unsigned n){
 unsigned i;writer.next=bits;writer.position=0;writer.sum=0;
 for(i=0;i<n;i++)append_pair(i,i+7);
}
int main(void){
 int i,a,b,expected;
 opaque=15;
 for(i=0;i<=opaque;i++){words[i]=i*17-120;bits[i]=i*257;bytes[i]=(int8_t)(i*17);}
 for(i=0;i<=opaque;i++){
  a=i*17-120;b=i*17;expected=b<128?b:b-256;
  if(read_word(i)!=a||read_byte(i)!=expected)return 1;
  if(arithmetic(31,i)!=((31+a)^(31-a)))return 2;
  if(bitops(0xF000U,i)!=((0xF000U+bits[i])^(0xF000U-bits[i])^(0xF000U&bits[i])^(0xF000U|bits[i])))return 15;
  if(compare(a,i)!=4||compare(a-1,i)!=1||compare(a+1,i)!=2)return 3;
  if(compound(i,23)!=a)return 4;
  if(scaled(i,i+128)!=i+128||member(i,i+128)!=i+128)return 5;
 }
 calls=0;if(snapshot()!=107||calls!=1||index_value!=7)return 6;
 calls=0;if(once()!=17||calls!=1||words[3]!=17)return 7;
 if(nested(100)!=117||calls!=2)return 8;
 if(volatile_fallback(opaque&3)!=3||local_fallback(opaque&3)!=9)return 9;
 if(wide_fallback(opaque&3,0x12345678L)!=0x12345678L)return 10;
 if(pointer_fallback(words,3)!=17)return 11;
 words[3]=-32768;if(compare(32767,3)!=2)return 12;
 words[3]=32767;if(compare(-32768,3)!=1)return 13;
 for(i=0;i<8;i++)if(boundary(i,0x8000U+i)!=(0x8000U+i))return 14;
 src[0].x=99;src[0].y=12;dst[0].y=6;src[1].x=7;src[1].y=13;dst[1].y=2;
 parallel(opaque&2);
 if(src[0].x!=3||dst[0].x!=9||dst[0].y!=12||dst[1].x!=9||dst[1].y!=13)return 16;
 if(casted((opaque&1)*4)!=22)return 17;
 append_many(opaque&3);
 if(writer.next!=bits+6||writer.sum!=27||writer.position!=1||bits[0]!=0||bits[5]!=9)return 18;
 words[2]=100;words[6]=-19;addend=14;
 indexed_sum(opaque&6);indexed_sum(opaque&2);
 if(words[2]!=114||words[6]!=-5)return 19;
 return 0;
}
'''

def body(assembly,name):return assembly.split('_'+name+':',1)[1].split('__size_'+name,1)[0]

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 external=OUT/'indexed-boundary.s';external.write_text('.export _edge\n_edge = $FFF0\n')
 obj=external.with_suffix('.o');support.run([support.CC65/'ca65.exe','-o',obj,external])
 runtime=ROOT/'build/integers.o'
 rows=[]
 for name,flags in [('selected',[]),('disabled',['--no-indexed-operands']),
                    ('general',['--no-body-optimizations','--no-line-passes','--no-stack-frames','--no-dp-homes','--no-region-homes'])]:
  _,rom,labels=support.compile_case('indexed_'+name,SOURCE,extra_objects=[obj,runtime],flags=['-I',ROOT/'include',*flags])
  assembly=rom.with_suffix('.s').read_text();support.emulate(rom,labels,0)
  if name=='selected':
   for fn in ('read_word','read_byte','arithmetic','bitops','compare','scaled','member','compound','snapshot','once','nested','boundary'):
    assert '; direct indexed operand' in body(assembly,fn),fn
   for fn in ('volatile_fallback','wide_fallback','local_fallback','pointer_fallback','fixed_fallback'):
    assert '; direct indexed operand' not in body(assembly,fn),fn
   assert re.search(r'\b(?:adc|sbc) a:\.loword\(_words\+\$0000\),x',assembly)
   assert 'adc a:.loword(_words+$0000),x' in body(assembly,'indexed_sum')
   assert 'adc a:.loword(_dst+$0000),x' in body(assembly,'casted')
   assert 'lda a:.loword(_src+$0002),x' in body(assembly,'parallel')
  if name=='disabled':assert '; direct indexed operand' not in assembly
  rows.append(dict(mode=name,rom_bytes=rom.stat().st_size))
 (OUT/'indexed-operands.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS direct indexed loads/stores/ALU/comparisons; signed bytes, odd strides, aliasing/calls, bank end and fallbacks (three emission modes)')

if __name__=='__main__':main()
