"""Check when the compiler can reuse array reads and conditions and when a write makes the previous result stale."""
from pathlib import Path
import importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reuse_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
SOURCE=r'''
#include <stdint.h>
volatile uint16_t input,pulse,guarded[8];uint16_t data[8],other[8],calls,observed;
float exposed_float;
volatile float input_float;
__noinline float repeated_truncation(float value,int *out){
 *out=(int)value;
 value=(float)(int)value;
 return value;
}
__noinline int aliased_truncation(float *out){
 int before=(int)exposed_float;
 *out=-1.75f;
 return before-(int)exposed_float;
}
__noinline int volatile_truncation(int *out){
 *out=(int)input_float;
 return (int)input_float;
}
const uint8_t rom[8]={3,5,7,11,13,17,19,23};
__noinline void change(uint16_t i){data[i]+=7;calls++;}
__noinline void opaque(void){data[0]+=9;calls++;}
__noinline uint16_t mutable_reads(uint16_t i){uint16_t a,b,d;pulse=1;a=data[i];b=data[i]+1;d=data[i]+2;return a+b+d;}
__noinline uint16_t distinct(uint16_t i){uint16_t a,b,d;pulse=2;a=data[i];other[i]=123;b=data[i]+1;d=data[i]+2;return a+b+d;}
__noinline uint16_t changing(uint16_t i){uint16_t a,b,d,e;pulse=3;a=data[i];data[i]+=7;b=data[i];d=data[i]+1;e=data[i]+2;return a+b+d+e;}
__noinline uint16_t index_change(uint16_t i){uint16_t a,b,d,e;pulse=4;a=data[i];i=(i+1)&7;b=data[i];d=data[i]+1;e=data[i]+2;return a+b+d+e;}
__noinline uint16_t immutable_reads(uint16_t i){uint16_t a,b,d;pulse=5;a=rom[i];opaque();b=rom[i];d=rom[i];return a+b+d;}
__noinline uint16_t call_change(uint16_t i){uint16_t a,b,d,e;pulse=6;a=data[i];change(i);b=data[i];d=data[i]+1;e=data[i]+2;return a+b+d+e;}
__noinline uint16_t pointer_change(uint16_t *p,uint16_t i){uint16_t a,b,d,e;pulse=7;a=data[i];*p+=7;b=data[i];d=data[i]+1;e=data[i]+2;return a+b+d+e;}
__noinline uint16_t volatile_reads(uint16_t i){volatile uint16_t *p=data;pulse=8;return p[i]+p[i]+p[i];}
__noinline uint16_t volatile_array(uint16_t i){uint16_t a,b,d;a=guarded[i];b=guarded[i];d=guarded[i];return a+b+d;}
__noinline void bump_index(uint16_t *p){*p=(*p+1)&7;calls++;}
__noinline uint16_t escaped_index(uint16_t i){uint16_t a,b,d;pulse=21;a=rom[i];bump_index(&i);b=rom[i];d=rom[i];return a+b+d;}
__noinline uint16_t paths(uint16_t i,uint16_t yes){uint16_t a=0,b,d;pulse=9;if(yes)a=data[i];b=data[i];d=data[i];return a+b+d;}
__noinline uint16_t iterations(uint16_t count){uint16_t k,a,b,d,total=0;pulse=10;for(k=0;k<count;k++){if(k==2)continue;a=data[0+k*0];b=data[0+k*0]+1;d=data[0+k*0]+2;total+=a+b+d;data[0]+=7;if(k==4)break;}return total;}
__noinline uint16_t predicates(int16_t a,int16_t b){uint16_t r=0;pulse=11;r+=a<b;r+=a<b;r+=b>a;r+=a>=b;return r;}
__noinline uint16_t branch_facts(int16_t a,int16_t b){uint16_t r=0;pulse=12;if(a<b){if(b>a)r+=1;if(a>=b)r+=2;}else{if(a>=b)r+=4;}return r;}
__noinline uint16_t predicate_change(int16_t a,int16_t b){uint16_t r=0;pulse=13;r+=a<b;a=b;r+=a<b;r+=a>=b;return r;}
__noinline uint16_t unsigned_order(uint16_t a,uint16_t b){uint16_t r=0;pulse=14;if(a<b){if(b>a)r++;}else{if(a>=b)r+=2;}return r;}
__noinline uint16_t mixed_types(int16_t a,uint16_t b){uint16_t r=0;pulse=15;r+=a<(int16_t)b;r+=(uint16_t)a<b;return r;}
__noinline uint16_t equality(uint16_t a,uint16_t b){uint16_t r=0;pulse=18;if(a==b){if(a!=b)r=8;else r=1;}else{if(a!=b)r=2;}return r;}
__noinline uint16_t array_predicate(uint16_t i){uint16_t r=0;pulse=19;r+=data[i]<data[(i+1)&7];r+=data[i]<data[(i+1)&7];data[i]=0;r+=data[i]<data[(i+1)&7];return r;}
__noinline uint16_t same_expression(uint16_t i){uint16_t a,b,d;pulse=20;a=data[i]+data[i];b=data[i];d=data[i]+1;return a+b+d;}
__noinline int argument_change(uint16_t i){change(i);return 1;}
__noinline uint16_t unordered(uint16_t i){uint16_t a,b,d;pulse=16;observed=argument_change(i)+data[i];a=data[i];b=data[i]+1;d=data[i]+2;return a+b+d;}
struct Packet{uint16_t value[4];};struct Packet packet;
__noinline uint16_t member_change(uint16_t i){uint16_t a,b,d;pulse=17;a=packet.value[i];packet.value[i]+=7;b=packet.value[i];d=packet.value[i];return a+b+d;}
static unsigned clip(int value){
 if((unsigned)value<=23U)return (unsigned)value;
 return value<0?0U:23U;
}
__noinline void transform(uint16_t first,uint16_t count,int16_t delta){
 for(uint16_t i=first,end=first+count;i<end;++i){
  unsigned v=data[i];
  unsigned a=clip((int)(v&31U)+delta);
  unsigned b=clip((int)((v>>5)&31U)+delta);
  other[i]=a|(b<<5);
 }
}
__noinline uint16_t keep_increment(uint16_t value){
 return value+1U==17U?0U:value+1U;
}
uint8_t byte_limit;
uint16_t word_limit;
__noinline uint16_t step_up(uint16_t value){
 return value==(uint16_t)(byte_limit-1)?37U:value+1U;
}
__noinline uint16_t step_down(uint16_t value){
 return (uint16_t)(word_limit+1U)!=value?value-1U:93U;
}
__noinline uint16_t either_bit(uint16_t value){
 if((value&2U)==2U||(value&256U)==256U)return 7;
 return 11;
}
__noinline uint16_t reload_word(uint16_t value){
 observed=value+37U;
 return observed+5U;
}
__noinline uint16_t local_bytes(uint16_t i){
 char text[]="abcde";
 return text[i];
}
__noinline uint16_t long_local_bytes(uint16_t i){
 unsigned char text[24]="0123456789\0abcdefghij";
 text[0]=(unsigned char)i;
 return text[i];
}
__noinline unsigned letter(const char * __far s){return (unsigned char)*s;}
__noinline unsigned fixed_table(void){
 const char * __far const entries[]={"a","b","c"};
 unsigned sum=0;
 for(unsigned i=0;i<3;++i)sum+=letter(entries[i]);
 return sum;
}
__noinline unsigned dynamic_table(unsigned i){
 const char * __far const entries[]={"a","b","c"};
 return letter(entries[i]);
}
__noinline unsigned pair(unsigned a,unsigned b){return a^b;}
__noinline unsigned shifted_pair(uint16_t n){
 uint16_t previous=n-16U;
 return pair(n>>4,previous>>4);
}
__noinline unsigned shifted_add(uint16_t n){
 return pair(n>>3,((uint16_t)(n+24U))>>3);
}
__noinline unsigned shifted_unaligned(uint16_t n){
 return pair(n>>4,((uint16_t)(n-15U))>>4);
}
int main(void){uint16_t n,i,k,v,expect,prior;int16_t a,b;int converted;
 if((int)repeated_truncation(-123.75f,&converted)!=-123||converted!=-123)return 35;
 exposed_float=7.25f;if(aliased_truncation(&exposed_float)!=8)return 36;
 input_float=5.75f;if(volatile_truncation(&converted)!=5||converted!=5)return 37;
 for(n=0;n<128;n++){
  input=(uint16_t)(n*25173U+13849U);v=input;i=n&7;calls=0;
  for(k=0;k<8;k++)data[k]=v+k;
  if(mutable_reads(i)!=(uint16_t)(3U*(v+i)+3U))return 1;
  if(distinct(i)!=(uint16_t)(3U*(v+i)+3U)||other[i]!=123)return 2;
  prior=data[i];if(changing(i)!=(uint16_t)(4U*prior+24U)||data[i]!=(uint16_t)(prior+7))return 3;
  prior=data[i];expect=(uint16_t)(prior+3U*data[(i+1)&7]+3U);if(index_change(i)!=expect)return 4;
  if(immutable_reads(i)!=(uint16_t)(3U*rom[i])||calls!=1)return 5;
  prior=data[i];if(call_change(i)!=(uint16_t)(4U*prior+24U)||calls!=2)return 6;
  prior=data[i];if(pointer_change(&data[i],i)!=(uint16_t)(4U*prior+24U))return 7;
  if(volatile_reads(i)!=(uint16_t)(3U*data[i]))return 8;
  guarded[i]=data[i];if(volatile_array(i)!=(uint16_t)(3U*guarded[i]))return 20;
  if(paths(i,0)!=(uint16_t)(2U*data[i])||paths(i,1)!=(uint16_t)(3U*data[i]))return 9;
  data[0]=v;expect=(uint16_t)(12U*v+138U);if(iterations(0)!=0||data[0]!=v||iterations(6)!=expect||data[0]!=(uint16_t)(v+28))return 10;
  a=(int16_t)v;b=(int16_t)(v^32768U);
  if(predicates(a,b)!=(a<b?3:1)||branch_facts(a,b)!=(a<b?1:4))return 11;
  if(predicates(a,a)!=1||branch_facts(a,a)!=4||predicate_change(a,b)!=(uint16_t)((a<b)+1))return 12;
  if(unsigned_order(v,v^32768U)!=(v<(uint16_t)(v^32768U)?1:2))return 13;
  if(mixed_types(a,(uint16_t)b)!=(uint16_t)((a<b)+((uint16_t)a<(uint16_t)b)))return 14;
  if(equality(v,v)!=1||equality(v,v^32768U)!=2)return 17;
  if(same_expression(i)!=(uint16_t)(4U*data[i]+1U))return 18;
  expect=(uint16_t)(2U*(data[i]<data[(i+1)&7])+(data[(i+1)&7]!=0));if(array_predicate(i)!=expect||data[i]!=0)return 19;
  prior=data[i];if(unordered(i)!=(uint16_t)(3U*prior+24U)||calls!=3)return 15;
  if(escaped_index(i)!=(uint16_t)(rom[i]+2U*rom[(i+1)&7])||calls!=4)return 21;
  for(k=0;k<4;k++)packet.value[k]=v+k;prior=packet.value[i&3];if(member_change(i&3)!=(uint16_t)(3U*prior+14U))return 16;
  a=(int16_t)((int)n-64);
  transform(i,1,a);
  b=(int16_t)(data[i]&31U)+a;
  expect=b<0?0:b>23?23:(uint16_t)b;
  b=(int16_t)((data[i]>>5)&31U)+a;
  expect|=(uint16_t)(b<0?0:b>23?23:b)<<5;
  if(other[i]!=expect)return 22;
  transform(i,0,0);
  if(other[i]!=expect)return 23;
  if(keep_increment((uint16_t)(n-1U))!=(n==17U?0U:n))return 24;
  if(either_bit(v)!=((v&258U)?7U:11U))return 25;
  if(reload_word(v)!=(uint16_t)(v+42U)||observed!=(uint16_t)(v+37U))return 26;
  if(local_bytes(n%6U)!=(n%6U==5U?0U:97U+n%6U))return 27;
  k=n%24U;
  if(long_local_bytes(k)!=(k==0||k>=21U||k==10U?0U:k<10U?48U+k:86U+k))return 32;
  if(fixed_table()!=294U||dynamic_table(n%3U)!=97U+n%3U)return 28;
  k=n<32U?n:n<64U?65535U-(n-32U):v;
  if(shifted_pair(k)!=((k>>4)^((uint16_t)(k-16U)>>4)))return 29;
  if(shifted_add(k)!=((k>>3)^((uint16_t)(k+24U)>>3)))return 30;
  if(shifted_unaligned(k)!=((k>>4)^((uint16_t)(k-15U)>>4)))return 31;
  byte_limit=(uint8_t)(n*17U);
  if(step_up((uint16_t)(byte_limit-1U))!=37U||step_up((uint16_t)(byte_limit+255U))!=byte_limit+256U)return 33;
  word_limit=k;
  if(step_down((uint16_t)(k+1U))!=93U||step_down(k)!=(uint16_t)(k-1U))return 34;
 }return 0;}
'''
def body(s,n):return s.split('_'+n+':',1)[1].split('__size_'+n,1)[0]
def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'reuse-reference.c';host.write_text('#define __noinline __declspec(noinline)\n#define __far\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/Od','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 conversions=ROOT/'build/libc.a'
 rows=[];assemblies={}
 for mode,flags in [('selected',[]),('disabled',['--no-value-reuse']),('no-lines',['--no-line-passes']),('no-inline',['--no-inline']),('no-retention',['--no-loop-index-retention'])]:
  _,rom,labels=c.compile_case('reuse_'+mode,SOURCE,extra_objects=[runtime,conversions],flags=['-I',ROOT/'include',*flags]);c.emulate(rom,labels,0);assemblies[mode]=rom.with_suffix('.s').read_text();rows.append(dict(mode=mode,bytes=rom.stat().st_size))
 selected,disabled=assemblies['selected'],assemblies['disabled']
 def header(s,n):return s.split('_'+n+':',1)[0].split('; allocation function')[-1]
 assert 'typed value reuse:' in header(selected,'mutable_reads')
 assert re.search(r'typed value reuse: \d+ memory, [1-9]\d* predicates',header(selected,'predicates'))
 assert 'typed value reuse:' not in header(selected,'volatile_reads')
 assert 'typed value reuse:' not in header(selected,'volatile_array')
 assert len(re.findall(r'^    lda (?:[af]:.*_guarded.*|a:\$0000,x)$',body(selected,'volatile_array'),re.M))==3
 assert body(selected,'branch_facts').count('sbc ')<body(disabled,'branch_facts').count('sbc ')
 assert body(selected,'immutable_reads').count('f:_')<body(disabled,'immutable_reads').count('f:_')
 assert 'typed value reuse:' not in disabled
 assert body(selected,'repeated_truncation').count('__fix32')==1
 assert body(disabled,'repeated_truncation').count('__fix32')==2
 for name in ('aliased_truncation','volatile_truncation'):
  assert body(selected,name).count('__fix32')==2
 transform=body(selected,'transform')
 assert 'jsr ' not in transform and transform.count('accumulator conditional join')==2,transform
 assert transform.count('tax\n')==1,transform
 assert body(selected,'keep_increment').count('accumulator conditional join')==1
 assert 'accumulator stepped conditional join' in body(selected,'step_up')
 assert 'accumulator stepped conditional join' in body(selected,'step_down')
 assert 'and #$0102' in body(selected,'either_bit')
 assert not re.search(r'lda .*_observed',body(selected,'reload_word'))
 assert body(selected,'local_bytes').count('fused adjacent RAM byte stores')==3
 assert 'local byte initializer: mvn' in body(selected,'long_local_bytes')
 assert 'inx\n    inx' in transform,transform
 assert body(selected,'fixed_table').count('pea .bankbyte(')==3
 assert 'pea .bankbyte(' not in body(selected,'dynamic_table')
 for name in ('shifted_pair','shifted_add'):
  assert 'shared unsigned word shift' in body(selected,name),body(selected,name)
  assert 'shared unsigned word shift' not in body(disabled,name)
 assert 'shared unsigned word shift' not in body(selected,'shifted_unaligned')
 (c.OUT/'value-reuse.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS value reuse: 128 opaque inputs, mutable/immutable loads, predicates, signedness, aliases, calls, dominance, loop mutation and zero trips')
if __name__=='__main__':main()
