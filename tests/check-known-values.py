"""Check which bits and value ranges the compiler can still predict after assignments, inlining and branches."""
from pathlib import Path
import importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('known_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
SOURCE=r'''
#include <stdint.h>
#include <math.h>
#include <string.h>
volatile uint16_t input,select;
volatile uint16_t external;
uint16_t calls;
int entry_zero,entry_word=-7;
float entry_scale=4.0f;
uint64_t entry_wide=UINT64_C(0x12ab000000010234);
volatile int entry_io=3;
int entry_loop_seed=7,entry_loop_sum,entry_loop_exit,entry_increment=4;
__noinline void change_entry_word(int *p){*p=9;}
__noinline uint16_t reflect(uint16_t x){uint16_t p=x&63U;return 63U-p;}
__noinline uint16_t join(uint16_t x,uint16_t sel){uint16_t p;if(sel)p=x&31U;else p=x&63U;return 63U-p;}
__noinline uint16_t bad_join(uint16_t x,uint16_t sel){uint16_t p;if(sel)p=x&31U;else p=x;return 63U-p;}
static uint8_t triangle(uint8_t p){p&=63;return p<32?p:63-p;}
__noinline uint16_t inline_chain(uint16_t x){return (uint16_t)triangle((uint8_t)x);}
__noinline uint16_t narrowed(uint16_t x){uint8_t a=(uint8_t)(x&63);uint16_t b=a;return (uint8_t)(63-b);}
__noinline uint16_t wrapped(uint16_t x){uint8_t p=(uint8_t)(x&63);p+=255;return p;}
__noinline int16_t signed_narrow(uint16_t x){return (int8_t)x;}
__noinline uint16_t boolean(uint16_t x){_Bool p=(_Bool)(x&63);return p;}
__noinline uint16_t loop(uint16_t x){uint16_t p=x&63,n,result=0;for(n=0;n<5;n++){if(n==2)continue;result+=63-p;}return result;}
__noinline uint16_t backedge(uint16_t x){uint16_t p=x&63,n,result=0;for(n=0;n<5;n++){result+=63-p;p+=40;}return result;}
__noinline uint16_t changing(uint16_t x,uint16_t sel){uint16_t p=x&63;if(sel)p+=200;return 63-p;}
__noinline int range_compare(uint16_t x){int16_t a=x&1023,b=(x>>6)&1023;return a<b;}
__noinline int signed_compare(int16_t x,int16_t y){return x<y;}
__noinline int quotient_outside(int8_t x){return x/100>=2 || x/100<-1 || x/100==3;}
__noinline int quotient_inside(int8_t x){return x/100>=1;}
__noinline int quotient_effect(void){return (++calls & 255U)/100U >= 3U;}
__noinline int literal_float(void){uint16_t x=65535U;return (float)x+1.0f==65536.0f;}
__noinline int literal_float_join(int condition){
 float x;if(condition)x=32768.0f;else x=32768.0f;
 return x*2.0f==65536.0f;
}
__noinline long literal_float_to_long(void){float x=123456789.0f;return (long)x+2L;}
__noinline float literal_negative_zero(void){float x=0.0f;return -x;}
__noinline float literal_infinity(void){float x=-3.0f,z=-0.0f;return x/z;}
__noinline int literal_unordered(void){float x=NAN;return x!=x&&!(x<1.0f);}
static const float readonly_float=1.5f;
static const volatile float visible_float=2.0f;
__noinline int literal_readonly_float(void){return readonly_float*2.0f==3.0f && visible_float;}
__noinline uint16_t combined_mask(uint16_t x){return 0x1040U ^ (x ^ 0x2080U);}
__noinline uint32_t combine_high_bit(uint32_t x){return (x^0x7654UL)-UINT32_C(0x80000000);}
__noinline uint16_t complement_mask(uint16_t x){return ~(x^0xA5A5U);}
__noinline int32_t mixed_mask(int16_t x){return (x ^ -32768) ^ 0x12340000L;}
__noinline uint32_t conditional_shift(uint32_t x){
 if((x&1U)==0)x=x>>1;
 else x=(x>>1)^0xFEDC4321UL;
 return x;
}
uint32_t shift_source,shift_table[2];
int32_t signed_shift_source;
__noinline uint32_t indexed_shift(unsigned i){
 return ((shift_source>>8)&UINT32_C(0xffffff))^shift_table[i];
}
__noinline int32_t signed_fixed_shift(void){return signed_shift_source>>8;}
__noinline uint32_t masked_xor(uint32_t a,uint32_t b){return (a^b)&UINT32_C(0xff);}
__noinline int sign_and(int32_t a,int32_t b,int32_t c,int32_t d){return ((a^b)&(c^d))<0;}
__noinline int sign_or(int32_t a,int32_t b,int32_t c,int32_t d){return 0<=((a^b)|(c^d));}
__noinline int sign_subtract(int32_t a,int32_t b,int32_t mask){
 return ((a^(mask&INT32_C(0x7f000000)))-b)<0;
}
struct loop_member { int i; } loop_member;
unsigned char loop_byte;
__noinline int fixed_update(void){
 for(loop_member.i=2;loop_member.i<26;loop_member.i++)loop_byte-=3;
 return loop_member.i;
}
__noinline void volatile_update(void){
 int i;for(i=2;i<26;i++)external++;
}
__noinline uint16_t signed_shift(int16_t x){return (uint16_t)(x>>8);}
__noinline void mutate(uint16_t *p){*p=1000;calls++;external=1000;}
__noinline uint16_t escaped(uint16_t x){uint16_t p=x&63;mutate(&p);return 63-p;}
__noinline uint16_t call_barrier(uint16_t x){uint16_t p=x&63;external=p;mutate((uint16_t*)&external);return (63-p)+(63-external);}
__noinline uint16_t short_circuit(uint16_t x,uint16_t sel){uint16_t p=x&63;sel&&(p=x);return 63-p;}
__noinline uint16_t two_arms(uint16_t x,uint16_t sel){uint16_t p=x&63;return sel?(63-p):p;}
__noinline uint16_t known_one(uint16_t x){uint16_t p=(x&63)|192;return (p^255)&255;}
__noinline uint16_t word_wrap(uint16_t x){uint16_t p=x+65520U;return (uint8_t)p;}
__noinline int signed_mask(uint16_t x){int16_t p=(int16_t)x;p&=63;return 63-p;}
uint8_t bytes[32];
uint8_t *volatile published;
__noinline int switch_index(int offset,int readback){
 uint8_t out[32]={0},*p=bytes+offset;
 int i;
 for(i=0;i<30;++i){
  int mask=255,value=*++p;
  switch(i){case 1:mask^=2;break;case 2:mask^=4;break;case 25:mask^=1;break;default:break;}
  out[i]=mask|value;published=p;
 }
 return out[readback];
}
__noinline int switch_rewrites_index(int start){
 int i,count=0;
 for(i=(start&1)*4;i<=6;++i){
  switch(i){case 2:i=-3;break;default:break;}
  if(++count==4)break;
 }
 return i;
}
int diagonal[2][2];
__noinline void fill_diagonal(void){
 int i,j;
 for(i=0;i<2;++i)for(j=0;j<2;++j)if(i==j)diagonal[i][j]=1;
}
__noinline int identical_rom_byte(unsigned i){
 const unsigned char * __far a=(const unsigned char * __far)"\377\0";
 const unsigned char * __far b=(const unsigned char * __far)"\377\0";
 return i<3&&a[i]==b[i];
}
__noinline unsigned embedded_rom_byte(void){
 const char * __far s="x\0\377";
 return (unsigned char)s[2];
}
__noinline int joined_rom_byte(int select){
 const char * __far s;
 if(select)s="Ax";else s="Bx";
 return s[0];
}
__noinline int known_far_pointer(void){
 void * __far a=(void * __far)0x120040UL;
 void * __far b=(void * __far)0x120040UL;
 return a==b;
}
static int has_character(const char * __far text,int character){return strchr(text,character)!=0;}
__noinline int literal_string_search(void){
 return has_character("x\0z",'x')&&!has_character("x\0z",'z')&&has_character("x\0z",256);
}
__noinline unsigned shift_literal_byte(void){
 unsigned char value=0xe1;
 value<<=1;value>>=2;
 return value;
}
__noinline int absorbed_logical(int input){
 int zero=0,one=1;
 return (input&&zero)+(input||one)+(++calls&&zero);
}
int repeated_words[3],repeated_value,repeated_guard;
__noinline void nested_fixed_stores(void){
 int i,j,k;
 for(i=0;i<21;i+=9){
  for(j=0;j<3;++j)repeated_words[j]=1;
  k=1;
  for(;k<10;++k){repeated_value=2;if(i)repeated_guard=3;}
 }
}
__noinline int fixed_store_read(void){
 int old;
 repeated_words[0]=0x1234;repeated_words[1]=4;repeated_words[0]=5;
 old=repeated_words[0];
 repeated_words[0]=6;
 return old;
}
__noinline int dead_counted_while(int choice){
 int i=0,value;
 while(i<10){++i;if(i==1)value=0;if(value==choice)value=5;else value=4;}
 return i;
}
__noinline int dynamic_counted_increment(int bound,int total){
 int i;
 for(i=0;i<bound;++i)++total;
 return total+i;
}
__noinline int dynamic_invariant_store(int bound,int a,int b,int choose){
 int i,result=-5;
 for(i=0;i<bound;++i){if(choose)result=a;else result=b;}
 return result+i;
}
typedef struct {float value;} single_field;
static single_field make_field(float x){single_field r;r.value=x+1.0f;return r;}
__noinline int folded_record(void){
 single_field r;
 for(int i=0;i<10;++i){
  r=make_field(1.0f);
  if(r.value!=2.0f)return 0;
 }
 return 1;
}
static void expect_update(int value,int expected){if(value!=expected)++calls;}
__noinline int used_compound_result(void){
 int x=6,y=(x*=3);
 expect_update(x/=3,6);
 expect_update(x%=4,2);
 int one=1;
 x*=one;
 expect_update(x*=one,2);
 return x+y;
}
__noinline unsigned strided_dead_guard(void){
 unsigned i;
 for(i=4;i<52;i+=5)if((int)i>52)++calls;
 return i;
}
__noinline int strided_signed_guard(void){
 int i;
 for(i=-7;i<=4;i+=3)if(i>4)++calls;
 return i;
}
__noinline unsigned strided_live_guard(void){
 unsigned i;
 for(i=4;i<10;i+=3)if((int)i>5)++calls;
 return i;
}
__noinline int match_index(int target){
 int i,value=0;
 for(i=-3;i<5;++i)if(target==i){++calls;value=i;}
 return i+value;
}
__noinline void match_changing_index(int target){
 for(int i=1;i<4;++i)if(i==target){++calls;++target;}
}
static int guarded_indices[3];
__noinline void store_known_indices(void){
 for(unsigned i=0;i<3;++i)if(i!=1)guarded_indices[i]=7;
}
static int divide_by(int x,int d){return x/d;}
__noinline int repeated_division(int x){
 if(divide_by(x,3)!=x/3)++calls;
 x=x/3;
 if(x!=x/3)++calls;
 return x;
}
int main(void){
 uint16_t n,x,p,sel;int16_t sx;
 while(entry_zero)return 33;
 float startup_scale=entry_scale/2.0f;
 if(startup_scale!=2.0f||entry_wide!=UINT64_C(0x12ab000000010234))return 34;
 float startup_post=1.0f;
 if(startup_post--!=1.0f)return 35;
 if(entry_word==-7)entry_word=11;else return 36;
 if(entry_word!=11)return 37;
 ++entry_increment;
 if(entry_increment!=5)return 41;
 for(n=0;n<11;++n)entry_loop_sum+=entry_loop_seed;
 int entry_loop_counter;
 for(entry_loop_counter=0;entry_loop_counter<3;++entry_loop_counter)
  repeated_words[entry_loop_counter]=entry_loop_counter;
 entry_loop_exit=entry_loop_counter;
 change_entry_word(&entry_word);
 if(entry_word!=9||entry_io!=3||entry_loop_sum!=77||entry_loop_exit!=3)return 38;
 float observed_post=1.0f;
 if(observed_post--!=1.0f||observed_post!=0.0f)return 39;
 for(n=0;n<256;n++){
  input=n*257U;select=n&1;x=input;sel=select;p=x&63;
  if(reflect(x)!=(63U-p)||join(x,sel)!=(63U-(x&(sel?31U:63U))))return 1;
  if(bad_join(x,sel)!=(uint16_t)(63U-(sel?(x&31U):x)))return 2;
  if(inline_chain(x)!=(p<32?p:63-p)||narrowed(x)!=63-p)return 3;
  if(wrapped(x)!=(uint8_t)(p+255U)||boolean(x)!=(p!=0))return 4;
  sx=(n&128)?(int16_t)(n-256):(int16_t)n;
  if(signed_narrow(x)!=sx)return 5;
  if(loop(x)!=(63-p)*4U||backedge(x)!=(uint16_t)((63U-p)*5U-400U))return 6;
  if(changing(x,sel)!=(uint16_t)(63U-p-(sel?200U:0U)))return 7;
  if(range_compare(x)!=((x&1023U)<((x>>6)&1023U)))return 8;
  if(signed_compare((int16_t)x,(int16_t)(x^32768U))!=(n>=128))return 9;
  if(quotient_outside((int8_t)sx)||quotient_inside((int8_t)sx)!=(sx>=100))return 19;
  calls=0;if(quotient_effect()||calls!=1)return 20;
  if(combined_mask(x)!=(x^0x30c0U)||mixed_mask(sx)!=((sx^-32768)^0x12340000L))return 23;
  if(combine_high_bit(x)!=(x^UINT32_C(0x80007654)))return 25;
  if(complement_mask(x)!=(x^0x5A5AU))return 26;
  {uint32_t w=(uint32_t)x<<16 | n;
   if(conditional_shift(w)!=((w>>1)^((n&1)?0xFEDC4321UL:0)))return 24;}
  if(signed_shift((int16_t)x)!=(uint16_t)(n<128?n:n+65280U))return 10;
  calls=0;if(escaped(x)!=(uint16_t)(63U-1000U)||calls!=1)return 11;
  calls=0;if(call_barrier(x)!=(uint16_t)(126U-p-1000U)||calls!=1)return 12;
  if(short_circuit(x,sel)!=(uint16_t)(63U-(sel?x:p)))return 13;
  if(two_arms(x,sel)!=(sel?63-p:p)||known_one(x)!=63-p)return 14;
  if(word_wrap(x)!=(uint8_t)(x+65520U)||signed_mask(x)!=63-p)return 15;
 }
 bytes[2]=2;bytes[3]=0;
 if(switch_index(0,1)!=255||switch_index(0,2)!=251||switch_index(1,25)!=254||
    switch_index(0,31)!=0||published!=bytes+30)return 16;
 if(switch_rewrites_index(0)!=-2||switch_rewrites_index(1)!=7)return 17;
 fill_diagonal();
 if(diagonal[0][0]!=1||diagonal[0][1]!=0||diagonal[1][0]!=0||diagonal[1][1]!=1)return 18;
 loop_byte=33;external=65530U;
 if(fixed_update()!=26||loop_byte!=217)return 21;
 volatile_update();if(external!=18)return 22;
 if(!literal_float()||!literal_float_join(input))return 27;
 if(literal_float_to_long()!=123456794L)return 28;
 {union {float value;uint32_t bits;} zero;zero.value=literal_negative_zero();
  if(zero.bits!=UINT32_C(0x80000000))return 29;
  zero.value=literal_infinity();if(zero.bits!=UINT32_C(0x7f800000))return 30;}
 if(!literal_unordered())return 31;
 if(!literal_readonly_float())return 32;
 shift_source=UINT32_C(0xeb123456);shift_table[1]=UINT32_C(0x9431f500);
 signed_shift_source=INT32_C(-351128490);
 if(indexed_shift(1)!=UINT32_C(0x94dae734)||signed_fixed_shift()!=INT32_C(-1371596)||
    masked_xor(UINT32_C(0xdeadbe12),UINT32_C(0x5afeac0e))!=0x1c)return 33;
 if(!sign_and(-1,0,-2,0)||sign_and(-1,0,-2,-3)||
    sign_or(-1,0,-2,-3)||!sign_or(-1,-2,2,3))return 34;
 if(!sign_subtract(0x10000L,0x10001L,0)||sign_subtract(0x10000L,0xffffL,0)||
    !sign_subtract(0x12010000L,0x10001L,0x12000000L))return 35;
 if(!identical_rom_byte(0)||!identical_rom_byte(2)||identical_rom_byte(3)||
    embedded_rom_byte()!=255||!known_far_pointer()||
    joined_rom_byte(1)!='A'||joined_rom_byte(0)!='B')return 40;
 if(!literal_string_search()||shift_literal_byte()!=48||dead_counted_while(input)!=10)return 42;
 calls=0;if(absorbed_logical(input)!=1||calls!=1)return 43;
 nested_fixed_stores();
 if(repeated_words[0]!=1||repeated_words[1]!=1||repeated_words[2]!=1||
    repeated_value!=2||repeated_guard!=3)return 44;
 if(fixed_store_read()!=5||repeated_words[0]!=6||repeated_words[1]!=4)return 45;
 if(dynamic_counted_increment(9,-3)!=15||dynamic_counted_increment(-1,4)!=4||
    dynamic_counted_increment(0,4)!=4)return 46;
 if(dynamic_invariant_store(7,15,3,1)!=22||dynamic_invariant_store(8,15,3,0)!=11||
    dynamic_invariant_store(-4,15,3,1)!=-5)return 47;
 calls=0;if(!folded_record()||used_compound_result()!=20||calls)return 48;
 if(strided_dead_guard()!=54||strided_signed_guard()!=5||calls)return 49;
 if(strided_live_guard()!=10||calls!=1)return 50;
 calls=0;
 if(match_index(-4)!=5||match_index(5)!=5||calls)return 51;
 if(match_index(-3)!=2||match_index(4)!=9||calls!=2)return 52;
 match_changing_index(1);
 if(calls!=5)return 53;
 guarded_indices[1]=9;store_known_indices();
 if(guarded_indices[0]!=7||guarded_indices[1]!=9||guarded_indices[2]!=7)return 54;
 calls=0;if(repeated_division(-12)!=-4||calls!=1)return 55;
 return 0;
}
'''
def body(s,n):return s.split('_'+n+':',1)[1].split('__size_'+n,1)[0]
def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'known-host.c';host.write_text('#define __noinline __declspec(noinline)\n#define __far\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[]
 for mode,flags in [('selected',[]),('disabled',['--no-known-values']),('no-lines',['--no-line-passes']),('no-inline',['--no-inline'])]:
  _,rom,labels=c.compile_case('known_'+mode,SOURCE,extra_objects=[runtime,ROOT/'build/arithmetic.o',ROOT/'build/ieee_engine.o'],flags=['-I',ROOT/'include',*flags]);assembly=rom.with_suffix('.s').read_text();c.emulate(rom,labels,0)
  if mode=='selected':
   startup=body(assembly,'main').split('_change_entry_word',1)[0]
   assert not re.search(r'_entry_zero|_entry_wide|_entry_loop_seed|__fdiv32|__fsub32',startup),startup
   assert '_strchr' not in body(assembly,'literal_string_search')
   assert 'loop lowering:' not in body(assembly,'dead_counted_while')
   assert '#$1234' not in body(assembly,'fixed_store_read')
   for name in ('dynamic_counted_increment','dynamic_invariant_store','folded_record',
                'strided_dead_guard','strided_signed_guard','match_index','store_known_indices'):
    assert 'loop lowering:' not in body(assembly,name),name
   assert '_make_field' not in body(assembly,'folded_record')
   assert body(assembly,'repeated_division').count('__sdiv16')==2
   for name in ('identical_rom_byte','embedded_rom_byte','known_far_pointer'):
    assert 'tcs' not in body(assembly,name) and '],y' not in body(assembly,name),name
   for name in ('reflect','join','loop','narrowed','signed_mask'):assert 'eor #$003F' in body(assembly,name),name
   for name in ('bad_join','backedge','changing','escaped','short_circuit'):assert 'eor #$003F' not in body(assembly,name),name
   assert 'sbc ' not in body(assembly,'range_compare')
   assert 'sbc ' in body(assembly,'signed_compare')
   assert '__sdiv' not in body(assembly,'quotient_outside') and '__squot' not in body(assembly,'quotient_outside')
   assert 'jsr' in body(assembly,'quotient_inside')
   assert not re.search(r'__ufloat|__fadd32|__fcmp32',body(assembly,'literal_float'))
   assert not re.search(r'__fmul32|__fcmp32|\btcs\b',body(assembly,'literal_float_join'))
   assert 'jsr' not in body(assembly,'literal_float_to_long')
   assert '__fdiv32' not in body(assembly,'literal_infinity')
   assert '__fcmp32' not in body(assembly,'literal_unordered')
   assert '__fmul32' not in body(assembly,'literal_readonly_float')
   assert '_visible_float' in body(assembly,'literal_readonly_float')
   assert body(assembly,'combined_mask').count('    eor ')==1
   assert 'eor #$30C0' in body(assembly,'combined_mask')
   assert 'eor #$8000' in body(assembly,'combine_high_bit') and 'sbc ' not in body(assembly,'combine_high_bit')
   assert body(assembly,'complement_mask').count('    eor ')==1
   assert 'eor #$5A5A' in body(assembly,'complement_mask')
   assert '; shift carry selects the XOR mask' in body(assembly,'conditional_shift')
   indexed=body(assembly,'indexed_shift')
   assert '_shift_source+$0001' in indexed and indexed.count('eor a:$000')==2,indexed
   assert 'php' in body(assembly,'sign_subtract') and 'plp' in body(assembly,'sign_subtract')
   assert '; loop lowering: folded fixed update' in body(assembly,'fixed_update')
   assert '; loop lowering: folded fixed update' not in body(assembly,'volatile_update')
   assert '; inlined call:' in body(assembly,'inline_chain')
   loop=body(assembly,'switch_index')
   zero_fill = r'    lda #\$0000\n(?:    sta a:\$[0-9A-F]{4},y\n){16}'
   assert '; local byte initializer: mvn' in loop or re.search(zero_fill,loop),loop
   assert re.search(r'; loop lowering: generic fallback\n[^\n]* = \*\n    cmp #\$001E\n',loop)
  rows.append(dict(mode=mode,bytes=rom.stat().st_size))
 (c.OUT/'known-values.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS known values: 256 opaque byte/word vectors, joins, inlining, casts, signed values, wrapping, loops and alias/call barriers')
if __name__=='__main__':main()
