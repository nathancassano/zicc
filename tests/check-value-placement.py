"""Cumulative scalar regions, recurrences, dual offsets and versioned facts."""
from pathlib import Path
import importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('placement_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
SOURCE=r'''
#include <stdint.h>
volatile uint16_t input,pulse;
uint8_t phase,bands[64];int16_t data[16],other[16];int8_t velocity[16];
union Packet {uint8_t bytes[64];uint16_t words[32];} packet;
uint16_t final_index,calls;
static uint8_t triangle(uint8_t p){p&=63;return p<32?p:63-p;}
static uint16_t conditional(uint16_t p){p&=63;return p<32?p:p^63;}
static uint8_t shifted(uint8_t p){p<<=2;return p;}
__noinline uint16_t scalar(uint16_t x){uint16_t a=triangle((uint8_t)x);return a+conditional(x)+(shifted((uint8_t)x)==0?257:0);}
__noinline uint16_t branch_value(uint16_t x){if(conditional(x))return 7;return 11;}
__noinline void recurrence(uint8_t start){uint8_t i,ph,c;for(i=start;i<16;i++){ph=(uint8_t)(i+phase);c=triangle(ph+21);bands[i]=c;bands[i+16]=ph;}final_index=i;}
__noinline void masked_recurrence(uint8_t start){uint8_t i,ph;for(i=start;i<16;i++){ph=(uint8_t)(i+phase);bands[i]=(ph+42)&63;bands[i+16]=(ph-17)&63;bands[i+32]=(~ph)&15;}final_index=i;}
__noinline uint16_t limit_recurrence(void){uint8_t i,ph;uint16_t sum=0;for(i=0;i<255;i++){ph=(uint8_t)(i+phase);sum+=(ph+42)&63;}return sum;}
__noinline void compared_recurrence(uint8_t start){uint8_t i,ph;for(i=start;i<16;i++){ph=(uint8_t)(i+phase);bands[i]=ph==0?17:31;}}
__noinline uint8_t live_recurrence(uint8_t start){uint8_t i,ph=99;for(i=start;i<16;i++){ph=(uint8_t)(i+phase);bands[i]=ph&63;}return ph;}
__noinline void rewritten_recurrence(uint8_t start){uint8_t i,ph;for(i=start;i<16;i++){ph=(uint8_t)(i+phase);ph++;bands[i]=ph&63;}}
__noinline void non_affine(void){uint8_t i,ph;for(i=0;i<16;i++){ph=(uint8_t)(_Bool)(i+phase);bands[i]=ph;bands[i+16]=ph;}}
__noinline void mutation(uint8_t start){uint8_t i,ph;for(i=start;i<16;i++){ph=(uint8_t)(i+phase);bands[i]=ph;phase++;}final_index=i;}
__noinline void continues(uint8_t start){uint8_t i,ph;for(i=start;i<16;i++){if(i==3)continue;ph=(uint8_t)(i+phase);bands[i]=ph;}final_index=i;}
__noinline void offsets(void){uint8_t i;for(i=0;i<12;i++){data[i]+=velocity[i];other[i]=data[i]+i;packet.bytes[i*4]=(uint8_t)data[i];packet.bytes[i*4+1]=(uint8_t)other[i];}final_index=i;}
__noinline void pairs(uint8_t start){uint8_t i,j;for(i=start;i<4;i++){for(j=i+1;j<12;j++){data[i]+=other[j]&3;data[j]+=other[i]&3;if(j==7)continue;other[j]+=data[i]&1;}}}
__noinline uint16_t path(uint8_t i,int16_t limit){if(data[i]<0)return 1;if(data[i]>limit)return 2;return 3;}
__noinline uint16_t exited(int16_t x){uint8_t i;uint16_t sum=0;for(i=0;i<4;i++){if(x<=0)continue;sum+=(x+1)>>1;}return sum;}
__noinline void change(uint8_t i){data[i]=-30000;calls++;}
__noinline uint16_t barrier(uint8_t i,int16_t *p){if(data[i]<0)return 1;*p=-30000;if(data[i]<0)return 2;change(i);return data[i]<0?3:4;}
__noinline uint16_t changing_index(uint8_t i){if(data[i]<0)return 1;i=(i+1)&15;return data[i]<0?2:3;}
__noinline uint16_t change_value(uint8_t i){change(i);return 0;}
__noinline uint16_t within_expression(uint8_t i){return data[i]<0?1:(change_value(i)?(data[i]<0?2:3):(data[i]<0?2:3));}
__noinline uint16_t pending(uint8_t i){uint16_t a,b,d;pulse=3;a=data[i];b=data[i]+1;d=data[i]+2;return a+b+d;}
__noinline void bytes(void){uint8_t i;int8_t t;for(i=0;i<12;i++){t=velocity[i];velocity[i]=-velocity[i];if(i<8)velocity[i]=t;}}
__noinline void cfg_clamp(int16_t limit,int16_t other_limit){uint8_t i;for(i=0;i<12;i++){
 if(data[i]<0)data[i]=0;else if(data[i]>limit)data[i]=limit;
 if(other[i]<0)other[i]=0;else if(other[i]>other_limit)other[i]=other_limit;
 packet.bytes[i*4]=(uint8_t)data[i];packet.bytes[i*4+1]=(uint8_t)other[i];
}}
__noinline int16_t lower(int16_t a,int16_t b){return a<b?a:b;}
__noinline int16_t upper(int16_t a,int16_t b){return a>=b?a:b;}
__noinline uint16_t span(int16_t a,int16_t b,int16_t c,int16_t d){return (uint16_t)(a<b?a:b)-(uint16_t)(c>d?c:d);}
__noinline uint16_t unsigned_lower(uint16_t a,uint16_t b){return b>a?a:b;}
__noinline uint16_t masked(uint16_t a){return ((a&255)+42)&63;}
__noinline uint16_t holes(uint16_t a){return ((a&240)+17)&240;}
__noinline uint16_t mask_flags(uint16_t a){uint16_t b=(a&255)+42;if(b>255)return 9;return b&63;}
__noinline void byte_pairs(void){uint8_t i,j;int8_t t;for(i=0;i<4;i++)for(j=i+1;j<12;j++){
 data[i]+=other[j]&3;data[j]+=other[i]&3;other[j]+=data[i]&1;t=velocity[i];velocity[i]=velocity[j];velocity[j]=t;
 if(velocity[i]>0)velocity[i]=-velocity[i];if(velocity[j]<0)velocity[j]=-velocity[j];
 if(velocity[i]<=0)velocity[i]=-velocity[i];if(velocity[j]>=0)velocity[j]=-velocity[j];
 if(velocity[i]==0)velocity[i]=-velocity[i];if(velocity[j]!=0)velocity[j]=-velocity[j];
}}
static const int16_t edge[8]={-32768,-32767,-129,-1,0,128,32766,32767};
int main(void){uint16_t n,k;int16_t expected[16],oy[16],v;int8_t ev[16];uint8_t expect_band[64],oldphase;uint16_t total;
 {uint16_t a,b;
  for(a=0;a<8;a++)for(b=0;b<8;b++){
   int16_t x=edge[a],y=edge[b];input=(uint16_t)x;x=(int16_t)input;
   if(lower(x,y)!=(x<y?x:y)||upper(x,y)!=(x>=y?x:y))return 18;
   if(span(x,y,y,x)!=(uint16_t)((uint32_t)(uint16_t)(x<y?x:y)-(uint16_t)(y>x?y:x)))return 19;
   if(unsigned_lower((uint16_t)x,(uint16_t)y)!=((uint16_t)x<(uint16_t)y?(uint16_t)x:(uint16_t)y))return 20;
  }
 }
 phase=255;total=0;for(k=0;k<255;k++)total+=(k+255+42)&63;if(limit_recurrence()!=total)return 28;
 masked_recurrence(255);if(final_index!=255)return 29;
 for(n=0;n<256;n++){
  input=n;k=input;
  if(masked(k+65280)!=((k+42)&63)||holes(k)!=(((k&240)+17)&240)||mask_flags(k)!=(k+42>255?9:(k+42)&63))return 21;
  v=k&63;if(scalar(k)!=(uint16_t)(2*(v<32?v:63-v)+((uint8_t)(k<<2)==0?257:0)))return 1;
  if(branch_value(k)!=((v==0||v==63)?11:7))return 2;
  phase=(uint8_t)(k+240);oldphase=phase;
  for(k=0;k<64;k++)bands[k]=expect_band[k]=99;
  k=n%20;for(total=k;total<16;total++){v=(total+oldphase+21)&63;expect_band[total]=v<32?v:63-v;expect_band[total+16]=(uint8_t)(total+oldphase);}
  recurrence((uint8_t)k);if(final_index!=(k<16?16:k)||phase!=oldphase)return 3;
  for(total=0;total<64;total++)if(bands[total]!=expect_band[total])return 4;
  masked_recurrence((uint8_t)k);if(final_index!=(k<16?16:k))return 23;
  for(total=k;total<16;total++)if(bands[total]!=((total+phase+42)&63)||bands[total+16]!=((total+phase-17)&63)||bands[total+32]!=((~(total+phase))&15))return 24;
  compared_recurrence((uint8_t)k);for(total=k;total<16;total++)if(bands[total]!=((uint8_t)(total+phase)==0?17:31))return 25;
  if(live_recurrence((uint8_t)k)!=(k<16?(uint8_t)(15+phase):99))return 26;
  rewritten_recurrence((uint8_t)k);for(total=k;total<16;total++)if(bands[total]!=((total+phase+1)&63))return 27;
  non_affine();for(total=0;total<16;total++)if(bands[total]!=(uint8_t)((total+phase)!=0)||bands[total+16]!=bands[total])return 17;
  mutation((uint8_t)k);for(total=k;total<16;total++)if(bands[total]!=(uint8_t)(total+oldphase+total-k))return 5;
  oldphase=phase;continues((uint8_t)k);for(total=k;total<16;total++)if(total!=3&&bands[total]!=(uint8_t)(total+oldphase))return 6;
  for(k=0;k<16;k++){expected[k]=data[k]=(int16_t)(n*13+k*7-1500);oy[k]=other[k]=(int16_t)(k*17+3);velocity[k]=(int8_t)(n+k);}
  offsets();if(final_index!=12)return 7;
  for(k=0;k<12;k++){expected[k]+=(int8_t)(n+k);oy[k]=expected[k]+k;if(data[k]!=expected[k]||other[k]!=oy[k]||packet.bytes[k*4]!=(uint8_t)expected[k]||packet.bytes[k*4+1]!=(uint8_t)oy[k])return 8;}
  {uint16_t i,j;for(i=n%6;i<4;i++)for(j=i+1;j<12;j++){expected[i]+=oy[j]&3;expected[j]+=oy[i]&3;if(j==7)continue;oy[j]+=expected[i]&1;}}
  pairs((uint8_t)(n%6));for(k=0;k<16;k++)if(data[k]!=expected[k]||other[k]!=oy[k])return 9;
  k=n&15;v=data[k];if(path((uint8_t)k,1000)!=(v<0?1:v>1000?2:3))return 10;
  v=(int16_t)(n*100-500);if(exited(v)!=(uint16_t)(v<=0?0:4*((v+1)>>1)))return 11;
  data[k]=100;if(pending((uint8_t)k)!=303)return 12;
  data[k]=100;if(barrier((uint8_t)k,&data[k])!=2)return 13;
  data[k]=100;data[(k+1)&15]=-30000;if(changing_index((uint8_t)k)!=2)return 14;
  data[k]=100;if(within_expression((uint8_t)k)!=2)return 15;
  bytes();for(k=0;k<12;k++)if(velocity[k]!=(k<8?(int8_t)(n+k):(int8_t)-(int8_t)(n+k)))return 16;
  for(k=0;k<16;k++){ev[k]=velocity[k];expected[k]=data[k];}
  {uint16_t i,j;int8_t t;for(i=0;i<4;i++)for(j=i+1;j<12;j++){
   expected[i]+=oy[j]&3;expected[j]+=oy[i]&3;oy[j]+=expected[i]&1;t=ev[i];ev[i]=ev[j];ev[j]=t;
   if(ev[i]>0)ev[i]=(int8_t)-ev[i];if(ev[j]<0)ev[j]=(int8_t)-ev[j];
   if(ev[i]<=0)ev[i]=(int8_t)-ev[i];if(ev[j]>=0)ev[j]=(int8_t)-ev[j];
   if(ev[i]==0)ev[i]=(int8_t)-ev[i];if(ev[j]!=0)ev[j]=(int8_t)-ev[j];
  }}
  byte_pairs();for(k=0;k<16;k++)if(data[k]!=expected[k]||other[k]!=oy[k]||velocity[k]!=ev[k])return 22;
  for(k=0;k<16;k++){expected[k]=data[k]=(int16_t)(n*25173U+k*13849U);oy[k]=other[k]=(int16_t)(n*13849U+k*25173U);}
  for(k=0;k<12;k++){expected[k]=expected[k]<0?0:expected[k]>(int16_t)(n&127)?(int16_t)(n&127):expected[k];oy[k]=oy[k]<0?0:oy[k]>(int16_t)(n&63)?(int16_t)(n&63):oy[k];}
  cfg_clamp((int16_t)(n&127),(int16_t)(n&63));
  for(k=0;k<16;k++)if(data[k]!=expected[k]||other[k]!=oy[k])return 30;
  for(k=0;k<12;k++)if(packet.bytes[k*4]!=(uint8_t)expected[k]||packet.bytes[k*4+1]!=(uint8_t)oy[k])return 31;
 }return 0;}
'''
def body(s,n):return s.split('_'+n+':',1)[1].split('__size_'+n,1)[0]
def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'placement-reference.c';host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/Od','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[];assemblies={}
 for mode,flags in [('selected',[]),('no-lines',['--no-line-passes']),('no-body',['--no-body-optimizations']),('no-inline',['--no-inline'])]:
  _,rom,labels=c.compile_case('placement_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);c.emulate(rom,labels,0);assemblies[mode]=rom.with_suffix('.s').read_text();rows.append(dict(mode=mode,bytes=rom.stat().st_size))
 selected=assemblies['selected']
 assert 'accumulator conditional join' in body(selected,'branch_value')
 assert 'second retained displacement:' in body(selected,'offsets')
 assert 'second retained displacement:' in body(selected,'pairs')
 assert 'commuted indexed update' in body(selected,'offsets')
 assert 'discarded indexed byte region' in body(selected,'bytes')
 assert 'retained byte indices begin' in body(selected,'byte_pairs')
 assert 'fused selection subtraction' in body(selected,'span')
 assert 'and #$00FF' not in body(selected,'masked')
 assert 'and #$00F0' in body(selected,'holes')
 assert body(selected,'pending').count('lda a:.loword(_data+')==1
 assert '; exact modular value recurrence' in selected
 assert '; coalesced recurrence home: low-byte observations' in selected
 assert 'inc z:__arith_' in body(selected,'masked_recurrence')
 assert 'inc z:__arith_' not in body(selected,'compared_recurrence')
 (c.OUT/'value-placement.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS value placement: 256 opaque vectors, flags, modular recurrences, two scaled offsets, signed-byte updates, exits, alias/index/call and same-expression barriers')
if __name__=='__main__':main()
