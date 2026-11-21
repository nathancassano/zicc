"""Check when a loop can keep its index in a register, including early exits and operations that overwrite the register."""
from pathlib import Path
import importlib.util,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('retained_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
SOURCE=r'''
#include <stdint.h>
int data[64];
uint8_t bytes[64];
uint8_t reverse[8],large_bytes[256],wrapping[1024];
uint8_t table[161];
const uint8_t rom[8]={1,2,3,4,5,6,7,8};
int completed,total;
volatile unsigned opaque;
__noinline void fill_middle(void){
 unsigned i;
 for(i=2;i<33;i++)bytes[i]=0xa7;
 for(i=18;i<24;i++)bytes[i]=0x42;
}
__noinline void dual(void){
 uint8_t i;int sum=0;
 for(i=0;i<8;i++){
  data[i]=(int)i+rom[i];bytes[i]=(uint8_t)(data[i]+i);
  reverse[7-i]=i;reverse[7-i]+=i+10;
  if(i<3)sum+=i;else sum+=data[i];
  if(i==5)sum+=1;
  if(bytes[i]>0)sum+=1;
 }
 completed=i;total=sum;
}
__noinline void stride(void){
 unsigned char k;
 for(k=0;k<32;k++){table[k*5+3]=(unsigned char)(k+7);table[k*5+4]=(unsigned char)(k^31);}
 completed=k;
}
__noinline void exits(void){
 unsigned char n;int sum=0;
 for(n=0;n<=9;n++){
  if(n==3)continue;
  bytes[n]=n;
  if(n==7)break;
  sum+=n;
 }
 completed=n;total=sum;
}
__noinline void zero(unsigned start){
 unsigned n;
 for(n=start;n<8;n++){data[n]=n+1;if(n==6)data[n]+=2;}
 completed=n;
}
int *word_addresses[8];
__noinline void make_addresses(void){
 int i;
 for(i=0;i<8;i++){word_addresses[i]=data+i;bytes[i]=(uint8_t)i;}
}
__noinline void signed_start(void){
 int n;for(n=2;n<7;n++){data[n]+=1;if(n==5)data[n]+=2;}completed=n;
}
__noinline void nested(void){
 unsigned char i,j;opaque=opaque;
 for(i=0;i<3;i++)for(j=i;j<8;j++){data[j]+=i;if(j==4)continue;data[j]+=1;}
}
__noinline void call(void){total++;}
__noinline void calls_fallback(void){unsigned char i;for(i=0;i<8;i++){bytes[i]=i;call();}}
volatile unsigned char io[8];
__noinline void volatile_fallback(void){unsigned char i;for(i=0;i<8;i++){bytes[i]=i;io[i]=bytes[i];}}
__noinline void mutation_fallback(void){unsigned char i;for(i=0;i<8;i++){bytes[i]=i;if(i==2)i++;}}
__noinline void escape_fallback(void){unsigned char i,*p=&i;for(i=0;i<8;i++){bytes[i]=i;if(i==2)*p=4;}}
__noinline void wide_fallback(void){unsigned char i;long x=1;for(i=0;i<8;i++){data[i]=i;x=x*3;}total=(int)x;}
__noinline void wrapped_offset(void){uint16_t k;for(k=65000U;k<65008U;k++){wrapping[(uint16_t)(k+1000U)]=(uint8_t)k;if(k==65003U)wrapping[(uint16_t)(k+1000U)]+=1;}completed=(int16_t)k;}
__noinline void upper_byte(void){unsigned char k;for(k=250;k<255;k++){large_bytes[k]=k;if(k==252)large_bytes[k]=large_bytes[k]+1;}completed=k;}
__noinline void helper_fallback(void){unsigned char k;for(k=0;k<8;k++){data[k]=data[k]*data[k];}}
__noinline int return_fallback(void){unsigned char k;for(k=0;k<8;k++){bytes[k]=k;if(k==3)return k;}return 8;}
__noinline void boolean_fallback(void){_Bool k;unsigned steps=0;for(k=0;k<2;k++){bytes[k]=steps;steps++;if(steps==4)break;}completed=k;total=steps;}
__noinline void negative_start_fallback(void){int k;for(k=-2;k<4;k++){bytes[k+2]=k+2;}completed=k;}
__noinline void converted_start_fallback(void){int16_t k;for(k=(int16_t)65534U;k<4;k++){bytes[k+2]=k+2;}completed=k;}
__noinline void dynamic_fallback(unsigned limit){unsigned n;for(n=0;n<limit;n++){data[n]=n;}}
__noinline int repeated_update(unsigned to,unsigned from){
 data[to]=data[to]+data[from];
 return data[to]=data[to]-data[from];
}
struct RomTri{signed char a,b;unsigned char c;};
static const struct RomTri rom_tri[4]={{3,-2,10},{5,4,20},{-7,6,30},{9,-8,40}};
__noinline void rom_struct_sum(void){
 unsigned i;
 for(i=0;i<4;++i)data[i]=(unsigned)((int)rom_tri[i].a*4-(int)rom_tri[i].b+rom_tri[i].c);
}
__noinline void mixed_cursor_loop(unsigned start){
 unsigned i;
 int acc=0;
 for(i=start;i<4;++i){
  if(i==2)continue;
  bytes[i]=(uint8_t)(rom_tri[i].c+i);
  data[i]=(int)rom_tri[i].a*2-(int)rom_tri[i].b;
  data[i]+=10;
  if(data[i]<0)acc+=1;
  if(i==3)break;
 }
 completed=i;total=acc;
}
__noinline void y_rom_stores(unsigned bias){
 unsigned n;
 for(n=0;n<4;++n){
  unsigned idx=(unsigned)bytes[n]+bias;
  data[n*2+0]=rom_tri[idx].a;
  data[n*2+1]=rom_tri[idx].b;
  data[n*2+32+1]=rom_tri[idx].c;
 }
}
__noinline void y_unused_fallback(int *out){
 unsigned i;
 for(i=0;i<4;++i)out[bytes[i]]=rom_tri[i].a;
}
__noinline void y5_ptr_cursor(const uint8_t *src,unsigned bias){
 unsigned i;
 for(i=0;i<4;++i){
  unsigned v=(unsigned)src[i]+bias;
  data[i*2+0]=rom_tri[v].a;
  data[i*2+1]=rom_tri[v].b;
 }
}
__noinline unsigned char_countdown_asc(unsigned crc){
 unsigned char b;
 for(b=0;b<8;b++){
  crc=(crc&1)?((crc>>1)^0xa001u):(crc>>1);
 }
 return crc;
}
__noinline unsigned char_countdown_dec(unsigned seed){
 unsigned char j;
 for(j=6;j;j--){
  seed=(seed<<1)^0x13u;
 }
 return seed;
}
int main(void){
 unsigned n;int expected[8];
 make_addresses();
 for(n=0;n<8;n++)if(word_addresses[n]!=data+n||bytes[n]!=n)return 77;
 opaque=0;dual();if(completed!=8||total!=67)return 1;
 for(n=0;n<8;n++)if(data[n]!=(int)(2*n+1)||bytes[n]!=(unsigned)(3*n+1)||reverse[7-n]!=2*n+10)return 2;
 stride();if(completed!=32)return 3;
 for(n=0;n<32;n++)if(table[n*5+3]!=n+7||table[n*5+4]!=(n^31))return 4;
 exits();if(completed!=7||total!=18)return 5;
 zero(opaque+10);if(completed!=10||data[0]!=1)return 6;
 zero(opaque+4);if(completed!=8||data[4]!=5||data[6]!=9)return 7;
 signed_start();if(completed!=7||data[2]!=6||data[5]!=9)return 8;
 for(n=0;n<8;n++)expected[n]=data[n];
 nested();
 for(n=0;n<8;n++)if(data[n]!=expected[n]+(n==0?1:n==1?3:n==4?3:6))return 9;
 calls_fallback();volatile_fallback();mutation_fallback();escape_fallback();wide_fallback();dynamic_fallback(opaque+8);
 if(total!=6561)return 10;
 helper_fallback();if(data[7]!=49||return_fallback()!=3)return 12;
 upper_byte();if(completed!=255||large_bytes[250]!=250||large_bytes[252]!=253||large_bytes[254]!=254)return 13;
 negative_start_fallback();if(completed!=4||bytes[0]!=0||bytes[5]!=5)return 14;
 converted_start_fallback();if(completed!=4||bytes[0]!=0||bytes[5]!=5)return 18;
 boolean_fallback();if(completed!=1||total!=4||bytes[1]!=3)return 15;
 wrapped_offset();if(completed!=(int16_t)65008U)return 16;
 for(n=0;n<8;n++)if(wrapping[464+n]!=(uint8_t)(65000U+n)+(n==3))return 17;
 frame_only();if(total!=2430||completed!=8||data[7]!=2430)return 11;
 data[0]=10;data[1]=4;if(repeated_update(opaque,opaque+1)!=10||data[0]!=10||data[1]!=4)return 23;
 if(repeated_update(opaque,opaque)!=0||data[0]!=0)return 24;
 rom_struct_sum();
 if(data[0]!=24||data[1]!=36||data[2]!=(unsigned)(-4)||data[3]!=84)return 25;
 data[2]=777;bytes[2]=55;
 mixed_cursor_loop(opaque+1);
 if(completed!=3||total!=0||bytes[1]!=21||bytes[2]!=55||bytes[3]!=43||data[1]!=16||data[2]!=777||data[3]!=36)return 26;
 bytes[0]=0;bytes[1]=2;bytes[2]=1;bytes[3]=3;
 y_rom_stores(opaque);
 if(data[0]!=3||data[1]!=-2||data[33]!=10||data[2]!=-7||data[3]!=6||data[35]!=30||
    data[4]!=5||data[5]!=4||data[37]!=20||data[6]!=9||data[7]!=-8||data[39]!=40)return 27;
 y_unused_fallback(data+16);
 if(data[16]!=3||data[17]!=-7||data[18]!=5||data[19]!=9)return 28;
 bytes[0]=1;bytes[1]=0;bytes[2]=3;bytes[3]=2;
 y5_ptr_cursor(bytes,opaque);
 if(data[0]!=5||data[1]!=4||data[2]!=3||data[3]!=-2||data[4]!=9||data[5]!=-8||data[6]!=-7||data[7]!=6)return 29;
 if(char_countdown_asc(opaque^0x1234u)!=0xd713u)return 30;
 if(char_countdown_dec(opaque+5u)!=0x02f1u)return 31;
 bytes[1]=12;bytes[33]=34;fill_middle();
 if(bytes[1]!=12||bytes[33]!=34)return 32;
 for(n=2;n<33;n++)if(bytes[n]!=(n>=18&&n<24?0x42:0xa7))return 33;
 return 0;
}
'''
SOURCE=SOURCE.replace('int main(void){', '__noinline void frame_only(void){unsigned char i;'+','.join(['int v0=0']+[f'v{k}={k}' for k in range(1,20)])+';for(i=0;i<8;i++){'+''.join(f'v{k}+=i+{k+1};' for k in range(20))+'data[i]='+ '+'.join(f'v{k}' for k in range(20))+';}completed=i;total='+ '+'.join(f'v{k}' for k in range(20))+';}\nint main(void){')

# Opaque entries cover zero trips, triangular starts and both levels of exits
# Expected arrays are calculated here, independently of target loop lowering
NESTED=r'''
__noinline void nested_exits(unsigned start){
 unsigned i;unsigned char j=77;
 for(i=start;i<6;i++){
  data[i]+=3;
  if(i==1)continue;
  for(j=i+1;j<8;j++){
   data[i]+=j;data[j]+=i;
   if(j==4)continue;
   data[i]+=2;
   if(i==2&&j==6)break;
  }
  if(i==4)break;
 }
 completed=i;total=j;
}
__noinline void nested_rect(unsigned start){
 unsigned char i,j=77;
 for(i=start;i<6;i++){
  data[i*2]+=3;
  for(j=0;j<8;j++){
   data[i*2]+=j;data[j]+=i;data[i*2]+=2;
  }
 }
 completed=i;total=j;
}
'''
checks=[]
for start in range(9):
 values=list(range(8));i=start;j=77
 while i<6:
  values[i]+=3
  if i==1:i+=1;continue
  j=i+1
  while j<8:
   values[i]+=j;values[j]+=i
   if j==4:j+=1;continue
   values[i]+=2
   if i==2 and j==6:break
   j+=1
  if i==4:break
  i+=1
 checks.append('for(n=0;n<8;n++)data[n]=n;nested_exits(opaque+'+str(start)+');'+
               'if(completed!='+str(i)+'||total!='+str(j)+')return 19;'+
               ''.join(f'if(data[{k}]!={v})return 20;' for k,v in enumerate(values)))
for start in range(8):
 values=list(range(12));i=start;j=77
 while i<6:
  values[i*2]+=3;j=0
  while j<8:
   values[i*2]+=j;values[j]+=i;values[i*2]+=2;j+=1
  i+=1
 checks.append('for(n=0;n<12;n++)data[n]=n;nested_rect(opaque+'+str(start)+');'+
               f'if(completed!={i}||total!={j})return 21;'+
               ''.join(f'if(data[{k}]!={v})return 22;' for k,v in enumerate(values)))
SOURCE=SOURCE.replace('int main(void){',NESTED+'\nint main(void){').replace(' frame_only();','\n'+'\n'.join(checks)+'\n frame_only();')

def body(s,n):return s.split('_'+n+':',1)[1].split('__size_'+n,1)[0]
def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'retention-host.c';host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 exe=host.with_suffix('.exe')
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(exe),host])
 c.run([exe])
 runtime=ROOT/'build/integers.o'
 rows=[]
 for mode,flags in [('selected',[]),('disabled',['--no-loop-index-retention']),('no-lines',['--no-line-passes'])]:
  _,rom,labels=c.compile_case('retention_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);assembly=rom.with_suffix('.s').read_text()
  c.emulate(rom,labels,0)
  if mode=='selected':
   assert '; constant indexed byte fill' in body(assembly,'fill_middle')
   for name in ('dual','stride','exits','zero','upper_byte'):assert '; retained loop indices:' in body(assembly,name),name
   assert ', Y=counter' in body(assembly,'dual')
   assert '; retained enclosing displacement:' in body(assembly,'nested_exits')
   assert '; retained nested begin' in body(assembly,'nested_exits')
   assert '; retained enclosing displacement: i stride 4' in body(assembly,'nested_rect')
   assert '; retained loop indices:' in body(assembly,'frame_only') and ', Y=counter' not in body(assembly,'frame_only')
   assert '; retained loop indices: X=stride 3' in body(assembly,'rom_struct_sum'),body(assembly,'rom_struct_sum')
   mixed=body(assembly,'mixed_cursor_loop')
   assert '; retained loop indices: X=stride 3, Y=counter' in mixed,mixed
   assert '; retained y-cursor: _data+$0000 -> __arith_lhs+' in mixed,mixed
   assert '),y\n' in mixed,mixed
   y_rom=body(assembly,'y_rom_stores')
   assert '; retained loop indices: Y=stride 4, X free' in y_rom and 'a:.loword(_data+$0042),y' in y_rom,y_rom
   y5_ptr=body(assembly,'y5_ptr_cursor')
   assert '; retained loop indices: Y=stride 4, X free' in y5_ptr and 'lda (__arith_lhs+' in y5_ptr and 'inc z:__arith_lhs+' in y5_ptr,y5_ptr
   asc_cd=body(assembly,'char_countdown_asc')
   assert '; register countdown' in asc_cd and 'ldx #$0008' in asc_cd and 'dex\n' in asc_cd,asc_cd
   dec_cd=body(assembly,'char_countdown_dec')
   assert '; register countdown' in dec_cd and 'ldx #$0006' in dec_cd and 'dex\n' in dec_cd,dec_cd
   assert '; retained loop indices:' not in body(assembly,'y_unused_fallback'),body(assembly,'y_unused_fallback')
   for name in ('calls_fallback','volatile_fallback','mutation_fallback','escape_fallback','wide_fallback','dynamic_fallback','helper_fallback','return_fallback','negative_start_fallback','converted_start_fallback','boolean_fallback'):assert '; retained loop indices:' not in body(assembly,name),name
  if mode=='disabled':assert '; retained loop indices:' not in assembly
  rows.append(dict(mode=mode,bytes=rom.stat().st_size))
 (c.OUT/'loop-index-retention.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS X/Y retention: byte/word counters, affine strides, scalar uses, ROM reads, exits, zero trips, inner loops and rejection guards')
if __name__=='__main__':main()
