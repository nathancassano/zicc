"""Check which calculations can use bytes and which need wider values, including calls to arithmetic helpers."""
import os
import hashlib,importlib.util,json,random,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sp=importlib.util.spec_from_file_location('body',ROOT/'tests/check-body-codegen.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b);c=b.c
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'arithmetic-regions-check'
SOURCE=r"""
#include <string.h>
#ifndef __ZICC__
#define __noinline
#define __far
#endif
unsigned char data[600],extra[32769],aux;
volatile unsigned seed=19;
const unsigned char rom_bytes[4]={1,9,250,37};const unsigned long rom_word=0x89abcdefUL;
__noinline unsigned far_read(const unsigned char * __far p){return p[2]+p[3]*256u;}
__noinline unsigned long far_word(const unsigned long * __far p){return *p;}
unsigned runtime_div(unsigned,unsigned);extern unsigned register_error;
static inline unsigned pair(unsigned x,unsigned k){aux=(unsigned char)(x%k);return (unsigned char)(x/k);}
__noinline unsigned descending(unsigned rounds){unsigned i,j,q=0;memset(data,2,600);
 for(j=0;j<rounds;j++){q=0;for(i=600;i>0;--i){unsigned k=3*i+7;unsigned short x=10*data[i-1]+q*i;q=pair(x,k);data[i-1]=aux;}data[0]=(unsigned char)(q%10);}
 return q;}
__noinline unsigned ranged(unsigned x,unsigned n){unsigned q=0,i;for(i=0;i<n;i++){q=(unsigned char)x;q=q*x;}return q;}
__noinline unsigned mixed(unsigned char x,unsigned y){return x*y;}
__noinline unsigned mixed_reverse(unsigned y,unsigned char x){return y*x;}
__noinline unsigned masked_factor(unsigned x,unsigned k){
 unsigned factor=k&3;return x*factor;}
__noinline unsigned masked_factor_reverse(unsigned x,unsigned k){
 unsigned factor=k&3;return factor*x;}
__noinline unsigned guarded_quotient(unsigned x,unsigned k){
 if(k<256)return x/k;return 0;}
__noinline int signed_remainder(int x,int k){
 if(k>0&&k<256)return x%k;return 0;}
unsigned left[300],right[300];
__noinline unsigned direct_factor(unsigned k,unsigned reverse){
 unsigned factor=k&3;
 if(reverse)return factor*right[0];
 return left[0]*factor;
}
__noinline unsigned join_shifts(const unsigned *p,unsigned high){
 unsigned limb=*p;
 unsigned value=(high<<4)|(limb>>2);
 return value^(limb&3);
}
__noinline unsigned masked_remainder_loop(const unsigned *source,unsigned *target,
                                         unsigned divisor,unsigned count){
 unsigned carry=0;
 if(divisor<256){
  do{
   unsigned limb=*source++;
   unsigned high=(carry<<4)|(limb>>2);
   unsigned quotient=high/divisor;
   unsigned remainder=high%divisor;
   carry=(remainder<<2)|(limb&3);
   *target++=quotient;
  }while(--count);
 }
 return carry;
}
__noinline unsigned indexed_pair_add(unsigned i){return left[i]+(63u^right[i]);}
__noinline unsigned indexed_pair_sub(unsigned i){return left[i]^(7u-right[i]);}
__noinline unsigned indexed_pair_reverse(unsigned i){return left[i]|(right[i]-7u);}
__noinline unsigned sweep(int first,int last){
 unsigned sum=1;int i;
 for(i=last;i>=first;--i){
  unsigned value=left[i]+(63^right[i])+sum;
  left[i]=value&63;sum=value>>6;
 }return sum;}
__noinline unsigned changed_index(int i){
 unsigned previous=left[i];++i;return right[i]^previous;}
__noinline unsigned cursor_words(const unsigned *source,unsigned *target,unsigned count,unsigned state){
 do{
  unsigned limb=*source++;
  state=(state<<3)|*source++;
  *target++=state^limb;
 }while(--count);
 return state;}
__noinline unsigned reverse_words(const unsigned *source,unsigned count){
 unsigned sum=0;do{sum+=*source--;}while(--count);return sum;}
__noinline unsigned cursor_pair(const unsigned *source,unsigned *target,unsigned count,unsigned k){
 unsigned total=0;
 if(k<1)return 0;
 if(k>=1024)return 0;
 do{
  unsigned value=*source--;
  unsigned q=value/k,r=value%k;
  total+=r;
  *target++=q;
 }while(--count);
 return total+*source+*target;}
__noinline unsigned cursor_remainder(const unsigned *source,unsigned *target,unsigned count,unsigned k){
 unsigned remainder=0;
 if(k<1)return 0;
 if(k>=1024)return 0;
 do{
  unsigned value=(remainder<<6)|*source++;
  unsigned q=value/k;
  remainder=value%k;
  *target++=q;
 }while(--count);
 return remainder+*source+*target;}
__noinline unsigned adjust_word(unsigned q,unsigned dividend,unsigned correction,unsigned divisor){
 int residue=(int)(dividend-correction);
 if(residue<0){
  --q;
  residue+=(int)divisor;
 }
 return (unsigned)residue ^ q;
}
__noinline unsigned adjust_loop(const unsigned *source,unsigned *target,unsigned count,unsigned divisor){
 unsigned q=0,carry=0;
 do{
  unsigned limb=*source++;
  int residue=(int)(limb-carry);
  if(residue<0){
   --q;
   residue+=(int)divisor;
  }
  carry=(unsigned)residue;
  *target++=q^carry;
 }while(--count);
 return carry;
}
__noinline unsigned adjust_saved(const unsigned *source,unsigned *target,unsigned count,unsigned divisor){
 unsigned q=0,carry=0;
 do{
  unsigned limb=*source++;
  int residue=(int)(limb-carry);
  unsigned saved=(unsigned)residue;
  if(residue<0){
   --q;
   residue+=(int)divisor;
  }
  carry=(unsigned)residue;
  *target++=q^carry^saved;
 }while(--count);
 return carry;
}
__noinline unsigned paired_loop(const unsigned *source,unsigned k,unsigned count){
 unsigned sum=0;
 if(k<256){
  do{
   unsigned dividend=*source++;
   unsigned q=dividend/k,r=dividend%k;
   sum+=q^r;
  }while(--count);
 }
 return sum;}
__noinline unsigned mixed_pair_loop(const unsigned *source,unsigned k,unsigned count){
 unsigned sum=0;
 if(k<1)return 0;
 if(k>=1024)return 0;
 do{
  unsigned dividend=*source++;
  unsigned q=dividend/k,r=dividend%k;
  sum+=q^r;
 }while(--count);
 return sum;}
__noinline unsigned changing_pair_loop(const unsigned *source,unsigned k,unsigned count){
 unsigned sum=0;
 if(k<1)return 0;
 if(k>=1024)return 0;
 do{
  unsigned dividend=*source++;
  unsigned q=dividend/k,r=dividend%k;
  sum+=q^r;
  k=(k&511)+1;
 }while(--count);
 return sum;}
__noinline unsigned byte_remainder_loop(const unsigned *source,unsigned k,unsigned count){
 unsigned remainder=0;
 if(k>=256)return 0;
 do{
  unsigned dividend=(remainder<<6)|*source++;
  remainder=dividend%k;
 }while(--count);
 return remainder;
}
__noinline unsigned word_seed_loop(const unsigned *source,unsigned k,unsigned count,unsigned seed_value){
 unsigned remainder=seed_value;
 if(k>=256)return 0;
 do{
  unsigned dividend=(remainder<<6)|*source++;
  remainder=dividend%k;
 }while(--count);
 return remainder;
}
__noinline unsigned guarded_pair(unsigned x,unsigned k){
 if(k<256){unsigned q=x/k,r=x%k;return q^r;}return 0;}
__noinline void expand_divisor(unsigned *k){*k=257;}
__noinline unsigned escaped_pair(unsigned x,unsigned k){
 if(k<256){expand_divisor(&k);unsigned q=x/k,r=x%k;return q^r;}return 0;}
__noinline unsigned unsafe(unsigned x,unsigned n){unsigned q=0,i;for(i=0;i<n;i++){q=300;q=(unsigned char)x;q+=x;}return q*x;}
__noinline unsigned escaped(unsigned x){unsigned q=(unsigned char)x;unsigned *p=&q;*p=400;return q*x;}
__noinline unsigned edge(void){unsigned i;for(i=32768u;i>0;--i)extra[i-1]=(unsigned char)(i+7);return extra[0]+extra[32767];}
__noinline unsigned above(void){unsigned i;for(i=32769u;i>0;--i)extra[i-1]=(unsigned char)(i+7);return extra[0]+extra[32768];}
__noinline unsigned ambiguous(unsigned n){unsigned i;for(i=n;i>0;--i)data[i-1]=(unsigned char)i;return data[0];}
__noinline int private_branches(int n){int a=7,b=9;if(n)a=11;else b=13;return a*3+b;}
__noinline unsigned alias_case(unsigned *p){unsigned a=7;*p=11;return a+*p;}
unsigned tick_count;
__noinline void tick(void){tick_count++;}
unsigned long countdown_ticks;
__noinline void countdown_wrap(unsigned count){
 do{++countdown_ticks;}while(--count!=0);
}
__noinline unsigned countdown_break(unsigned count){
 unsigned trips=0;
 do{
  countdown_wrap(2);
  if(++trips<3)continue;
  if(trips==4)break;
 }while(--count);
 return count;
}
__noinline unsigned countdown_observed(unsigned count){
 unsigned sum=0;do{sum+=count;}while(--count);return sum;
}
__noinline int signed_break(int start,int lower,unsigned stop){
 int i;
 unsigned trips=0;
 for(i=start;i>=lower;i-=1){
  if(++trips==stop)break;
  if(trips&1)continue;
  ++countdown_ticks;
 }
 return i;
}
__noinline unsigned signed_trips(int start,int lower){
 int i;
 unsigned trips=0;
 for(i=start;i>lower;--i)++trips;
 return trips;
}
__noinline unsigned fixed_clear(unsigned start,unsigned end){
 unsigned i;for(i=start;i<=end;++i)right[i]=0;return i;
}
__noinline int fixed_pattern(int start,int end){
 int i;for(i=start;i<end;++i)right[i]=0xa156u;return i;
}
__noinline unsigned repeat_plus(unsigned char n){unsigned i;for(i=0;i<n;i+=1)tick();return i;}
__noinline unsigned changing(unsigned char n){unsigned i;for(i=0;i<n;i++){tick();n--;}return i;}
__noinline unsigned repeat(unsigned char n){unsigned i;for(i=0;i<n;i++)tick();return i;}
__noinline unsigned byte_equal(unsigned char x){return x==65;}
__noinline unsigned packed(void){unsigned char b[3];b[0]=255;b[1]=128;b[2]=7;return b[0]!=255||b[1]!=128||b[2]!=7;}
__noinline unsigned chained(unsigned n){n+=1;n+=2;n+=3;n+=4;n+=5;n+=6;n+=7;n+=8;n+=9;return n;}
__noinline unsigned stores(unsigned x){unsigned char a=(unsigned char)x;unsigned b=a;unsigned c=b;return c+b;}
unsigned num[]={NUM},den[]={DEN},quo[]={QUO},rem[]={REM},prod[]={PROD};
int main(void){unsigned i;for(i=0;i<COUNT;i++){
 unsigned q=num[i]/den[i],r=num[i]%den[i];if(q!=quo[i]||r!=rem[i])return 1;
 if(runtime_div(num[i],den[i])!=quo[i]||register_error)return 2;
 if(mixed((unsigned char)num[i],den[i])!=prod[i]||mixed_reverse(den[i],(unsigned char)num[i])!=prod[i])return 3;
 if(masked_factor(num[i],den[i])!=(unsigned short)(num[i]*(den[i]&3)))return 16;
 if(guarded_quotient(num[i],den[i])!=(den[i]<256?quo[i]:0))return 17;
 if(guarded_pair(num[i],den[i])!=(den[i]<256?(quo[i]^rem[i]):0))return 14;
 }
 left[0]=0x8001u;right[0]=0xfedcu;
 for(i=0;i<4;++i){
  unsigned expected=(unsigned short)(0x8001u*i);
  if(masked_factor(0x8001u,i+8)!=expected||masked_factor_reverse(0x8001u,i+8)!=expected)return 39;
  if(direct_factor(i+8,0)!=expected||direct_factor(i+8,1)!=(unsigned short)(0xfedcu*i))return 51;
 }
 if(escaped_pair(65535u,5)!=255)return 15;
 if(signed_remainder(-1000,7)!=-6||signed_remainder(1000,7)!=6)return 18;
 left[1]=5;left[2]=17;left[3]=58;right[1]=7;right[2]=33;right[3]=13;
 if(sweep(1,3)||left[1]!=61||left[2]!=48||left[3]!=45||changed_index(1)!=28)return 19;
 left[0]=2;left[1]=3;left[2]=4;left[3]=5;
 if(cursor_words(left,right,2,1)!=93||right[0]!=9||right[1]!=89)return 20;
 if(cursor_words(left,left,2,1)!=93||left[0]!=9||left[1]!=89||left[2]!=4||left[3]!=5)return 21;
 if(reverse_words(left+3,3)!=98)return 22;
 if(paired_loop(num,7,8)!=EXPECTED_PAIR||paired_loop(num,257,8)!=0)return 23;
 countdown_wrap(0);
 if(countdown_ticks!=65536UL||countdown_break(9)!=6||countdown_ticks!=65544UL)return 24;
 if(countdown_break(1)!=0||countdown_ticks!=65546UL||countdown_observed(4)!=10)return 25;
 {const unsigned boundary[]={MIXED_DIVISORS},expected[]={MIXED_RESULTS};unsigned j;
  for(j=0;j<4;j++)if(mixed_pair_loop(num,boundary[j],8)!=expected[j])return 26;
  if(mixed_pair_loop(num,0,8)||mixed_pair_loop(num,1024,8))return 27;
 }
 left[0]=1000;left[1]=1001;
 if(changing_pair_loop(left,255,2)!=466||changing_pair_loop(left,256,2)!=464)return 40;
 left[0]=99;left[1]=1001;left[2]=1000;left[3]=31;right[2]=30;
 if(cursor_pair(left+2,right,2,7)!=135||right[0]!=142||right[1]!=143)return 41;
 if(cursor_pair(left+2,right,2,255)!=600||right[0]!=3||right[1]!=3)return 44;
 if(cursor_pair(left+2,right,2,257)!=588||right[0]!=3||right[1]!=3)return 42;
 if(cursor_pair(left+2,left+1,2,7)!=138||left[1]!=142||left[2]!=20)return 43;
 left[0]=61;left[1]=17;left[2]=99;
 if(cursor_remainder(left,right,2,7)!=130||right[0]!=8||right[1]!=48)return 45;
 if(cursor_remainder(left,right,2,257)!=195||right[0]!=0||right[1]!=15)return 46;
 left[1]=0x1234u;right[1]=0xabcdu;
 if(indexed_pair_add(seed&1)!=0xbe26u||
    indexed_pair_sub(seed&1)!=0x460eu||
    indexed_pair_reverse(seed&1)!=0xbbf6u)return 47;
 if(adjust_word(8,3,10,57)!=53||adjust_word(8,10,3,57)!=15||adjust_word(8,3,3,57)!=8)return 48;
 left[0]=5;left[1]=1;left[2]=9;
 if(adjust_loop(left,right,3,7)!=6||right[0]!=5||right[1]!=65532u||right[2]!=65529u)return 49;
 if(adjust_saved(left,right,3,7)!=6||right[0]!=0||right[1]!=0||right[2]!=65535u)return 50;
 left[0]=0xd735u;left[1]=2;
 if(join_shifts(left,0xa5b0u)!=0x7fccu||join_shifts(left+1,0x123u)!=0x1232u)return 52;
 left[2]=0xfffeu;
 if(masked_remainder_loop(left,right,29,3)!=110||right[0]!=474||right[1]!=60||right[2]!=564)return 53;
 if(masked_remainder_loop(left,left,237,3)!=122||left[0]!=58||left[1]!=7||left[2]!=69)return 54;
 if(signed_break(3,-3,4)!=0||countdown_ticks!=65547UL)return 28;
 if(signed_break(-4,2,3)!=-4||signed_break(-2,-4,0)!=-5||countdown_ticks!=65548UL)return 29;
 if(signed_break(-32767-1,-32767-1,1)!=-32767-1||
    signed_trips(32767,-32767-1)!=65535u||signed_trips(-5,-5)!=0)return 30;
 right[0]=5;right[1]=6;right[2]=7;right[3]=8;right[4]=9;
 if(fixed_clear(1,3)!=4||right[0]!=5||right[1]||right[2]||right[3]||right[4]!=9)return 31;
 if(fixed_pattern(2,4)!=4||right[1]||right[2]!=0xa156u||right[3]!=0xa156u||right[4]!=9)return 32;
 if(fixed_clear(4,3)!=4||fixed_pattern(3,3)!=3||right[3]!=0xa156u||right[4]!=9)return 33;
 if(byte_remainder_loop(num,251,8)!=EXPECTED_ROLLING||word_seed_loop(num,251,1,0x300)!=207)return 34;
 if(repeat(19)!=19||tick_count!=19||repeat(0)!=0||repeat(255)!=255||tick_count!=274||repeat_plus(5)!=5||tick_count!=279||changing(9)!=5||tick_count!=284)return 10;
 if(far_read(rom_bytes)!=9722u||far_word(&rom_word)!=0x89abcdefUL)return 11;
 if(!byte_equal(65)||byte_equal(64))return 13;
 if(chained(seed)!=64||chained(65535u)!=44||packed())return 12;
 if(descending(5)!=EXPECTED_Q)return 4;
 for(i=0;i<600;i++)if(data[i]!=expected[i])return 5;
 if(edge()!=15||above()!=16||ambiguous(9)!=1)return 6;
 if(private_branches(1)!=42||private_branches(0)!=34)return 7;
 if(stores(seed)!=38||unsafe(3,2)!=18||escaped(3)!=1200)return 8;
 {unsigned p=0;if(alias_case(&p)!=18||p!=11)return 9;}
 return 0;}
"""

def main():
 OUT.mkdir(parents=True,exist_ok=True);rnd=random.Random(65816)
 cases=[(n,d) for d in (1,2,10,127,255,256,257,511,512,5373,32768,65535) for n in (0,1,255,256,32767,32768,65534,65535)]
 cases += [(rnd.randrange(65536),rnd.randrange(1,65536)) for _ in range(512)]
 a=[2]*600
 for step in range(5):
  q=0
  for i in range(600,0,-1):x=(10*a[i-1]+q*i)&65535;k=3*i+7;q=(x//k)&255;a[i-1]=(x%k)&255
  a[0]=q%10
 source=SOURCE
 for key,values in [('NUM',[n for n,d in cases]),('DEN',[d for n,d in cases]),('QUO',[n//d for n,d in cases]),('REM',[n%d for n,d in cases]),('PROD',[((n&255)*d)&65535 for n,d in cases])]:source=source.replace(key,',\n'.join(','.join(map(str,values[i:i+32])) for i in range(0,len(values),32)))
 source=source.replace('COUNT',str(len(cases))).replace('EXPECTED_Q',str(q))
 source=source.replace('EXPECTED_PAIR',str(sum((n//7)^(n%7) for n,_ in cases[:8])&65535))
 rolling=0
 for n,_ in cases[:8]:rolling=(((rolling<<6)&65535)|n)%251
 source=source.replace('EXPECTED_ROLLING',str(rolling))
 divisors=(255,256,257,1023)
 source=source.replace('MIXED_DIVISORS',','.join(map(str,divisors)))
 source=source.replace('MIXED_RESULTS',','.join(str(sum((n//d)^(n%d) for n,_ in cases[:8])&65535) for d in divisors))
 source=source.replace('int main(void)', 'unsigned char expected[]={'+','.join(map(str,a))+'};\nint main(void)')
 wrapper=OUT/'wrapper.s';wrapper.write_text(""".setcpu "65816"
.a16
.i16
.importzp __arith_lhs,__arith_rhs
.import __udiv16,__mul16x8
.export _runtime_div,_register_error
.segment "BSS"
_register_error: .res 2
.segment "CODE"
_runtime_div:
 phy
 phx
 pha
 stx z:__arith_lhs
 and #$00FF
 sta z:__arith_rhs
 jsr .loword(__mul16x8)
 cmp z:__arith_lhs+8
 beq :+
 inc a:.loword(_register_error)
:
 pla
 plx
 stx z:__arith_lhs
 sta z:__arith_rhs
 ldx #$5AA5
 ldy #$A55A
 jsr .loword(__udiv16)
 cpx #$5AA5
 bne @bad
 cpy #$A55A
 beq @done
@bad:
 lda #1
 sta a:.loword(_register_error)
@done:
 lda z:__arith_lhs
 ply
 rts
""")
 obj=wrapper.with_suffix('.o');c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',obj,wrapper]);report={}
 for mode,flags in [('optimized',[]),('no-register',['--no-register-cursors']),('no-lines',['--no-line-passes']),('no-body',['--no-body-optimizations'])]:
  directory=OUT/mode;directory.mkdir(exist_ok=True);c.OUT=directory
  _,rom,sy=c.compile_case('program',source,extra_objects=[obj,ROOT/'build/integers.o',ROOT/'build/libc.a'],flags=flags)
  report[mode]=b.run(directory,rom,sy);asm=(directory/'program.s').read_text()
  if mode=='optimized':
   guarded=asm.split('_guarded_pair:\n',1)[1].split('__size_guarded_pair',1)[0]
   escaped=asm.split('_escaped_pair:\n',1)[1].split('__size_escaped_pair',1)[0]
   assert '__udiv8' in guarded and '__udiv16' not in guarded,guarded
   assert '__udiv16' in escaped and '__udiv8' not in escaped,escaped
   factor=asm.split('_masked_factor:\n',1)[1].split('__size_masked_factor',1)[0]
   quotient=asm.split('_guarded_quotient:\n',1)[1].split('__size_guarded_quotient',1)[0]
   reverse=asm.split('_masked_factor_reverse:\n',1)[1].split('__size_masked_factor_reverse',1)[0]
   assert 'two-bit word multiply' in factor and '__mul' not in factor,factor
   assert 'two-bit word multiply' in reverse and '__mul' not in reverse,reverse
   direct=asm.split('_direct_factor:\n',1)[1].split('__size_direct_factor',1)[0]
   assert re.search(r'    adc a:[^\n]*_left',direct) and re.search(r'    adc a:[^\n]*_right',direct),direct
   joined=asm.split('_join_shifts:\n',1)[1].split('__size_join_shifts',1)[0]
   assert re.search(r'    lsr a\n    lsr a\n    sta z:__arith_lhs\n    (?:lda [^\n]+|t[xy]a)\n(?:    asl a\n){4}    ora z:__arith_lhs',joined),joined
   masked=asm.split('_masked_remainder_loop:\n',1)[1].split('__size_masked_remainder_loop',1)[0]
   assert re.search(r'    sta f:\$004206\n    rep #\$20\n\.a16\n    (?:t[xy]a|lda [^\n]+)\n    and #\$0003\n    sta z:__arith_lhs\n',masked),masked
   assert '__uquot8' in quotient and '__uquot16' not in quotient,quotient
   sweep=asm.split('_sweep:\n',1)[1].split('__size_sweep',1)[0]
   assert sweep.count('    asl a\n')<=1,sweep
   assert '    dex\n    dex\n    dey\n    dec z:$0000\n' in sweep,sweep
   pair=asm.split('_paired_loop:\n',1)[1].split('__size_paired_loop',1)[0]
   assert pair.count('sta f:$004206')==1 and '__udiv8' not in pair,pair
   mixed_pair=asm.split('_mixed_pair_loop:\n',1)[1].split('__size_mixed_pair_loop',1)[0]
   assert mixed_pair.count('sta f:$004206')==1 and '__udiv16' in mixed_pair,mixed_pair
   assert mixed_pair.count('loop version for invariant divmod divisor')==1,mixed_pair
   changing_pair=asm.split('_changing_pair_loop:\n',1)[1].split('__size_changing_pair_loop',1)[0]
   assert 'loop version for invariant divmod divisor' not in changing_pair,changing_pair
   cursors=asm.split('_cursor_pair:\n',1)[1].split('__size_cursor_pair',1)[0]
   assert cursors.count('retain private word cursors in X and Y')==1,cursors
   assert 'sta f:$004206\n    rep #$20\n.a16\n    nop\n    nop\n    nop\n    dex\n    dex\n    lda f:$004214' in cursors,cursors
   assert re.search(r'    lda f:\$004216\n(?:;[^\n]*\n)*    clc\n',cursors),cursors
   assert re.search(r'    sep #\$20\n\.a8\n    lda \d+,s\n    sta f:\$004206',cursors),cursors
   carried=asm.split('_cursor_remainder:\n',1)[1].split('__size_cursor_remainder',1)[0]
   assert carried.count('carry private word in A across loop')==1,carried
   assert re.search(r'    lda f:\$004216\n    sta z:__arith_lhs\+\d+\n',carried),carried
   indexed_pair=asm.split('_indexed_pair_add:\n',1)[1].split('__size_indexed_pair_add',1)[0]
   assert 'eor a:.loword(_right' in indexed_pair and 'adc a:.loword(_left' in indexed_pair,indexed_pair
   adjusted=asm.split('_adjust_word:\n',1)[1].split('__size_adjust_word',1)[0]
   assert 'conditional word save' in adjusted and re.search(r'    adc \d+,s',adjusted),adjusted
   assert re.search(r'    sbc \d+,s\n(?:;[^\n]*\n)*    bpl ',adjusted),adjusted
   byte_shift=asm.split('_byte_remainder_loop:\n',1)[1].split('__size_byte_remainder_loop',1)[0]
   wide_shift=asm.split('_word_seed_loop:\n',1)[1].split('__size_word_seed_loop',1)[0]
   assert '    xba\n    lsr a\n    lsr a\n' in byte_shift,byte_shift
   assert wide_shift.count('    asl a\n')>=6,wide_shift
   for name in ('countdown_wrap','countdown_break','countdown_observed'):
    loop=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
    assert ('; loop lowering: register countdown' in loop)==(name=='countdown_wrap'),loop
    assert ('dec z:$0000' in loop)==(name=='countdown_break'),loop
   for name in ('signed_break','signed_trips'):
    loop=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
    assert 'dec z:$0000' in loop,loop
   for name in ('fixed_clear','fixed_pattern'):
    loop=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
    assert '; fixed-array word fill' in loop and 'dec z:$0000' in loop,loop
   assert 'arithmetic indexed region' in asm
   assert '__mul8x16' in asm and '__mul16x8' in asm
   equal=asm[asm.index('_byte_equal:'):asm.index('__size_byte_equal =')]
   assert 'sep #$20' not in equal, equal
   for name in ('unsafe','escaped'):
    body=asm[asm.index('_'+name+':'):asm.index('__size_'+name+' =')];assert '__mul16)' in body,name
  print('PASS arithmetic regions',mode,flush=True)
 # Builder stages regenerate call widths from the same typed choices
 for stage in (3,4):
  directory=OUT/('stage'+str(stage));directory.mkdir(exist_ok=True);paths=[]
  # Inline source cannot reference our test-only assembly adapter in this path
  text=source.replace('unsigned runtime_div(unsigned,unsigned);extern unsigned register_error;', 'unsigned runtime_div(unsigned x,unsigned y){return x/y;}unsigned register_error;')
  path=directory/'driver.c';path.write_text(text);stem=directory/'program'
  c.run([sys.executable,ROOT/'tools/build-rom.py',path,'--stage',stage,'-o',stem.with_suffix('.raw')])
  c.run([ROOT/'build/romtool.exe',stem.with_suffix('.raw'),stem.with_suffix('.sfc'),ROOT/'tests/title.txt'])
  sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
  report['stage'+str(stage)]=b.run(directory,stem.with_suffix('.sfc'),sy);print('PASS arithmetic regions stage',stage,flush=True)
 report['cases']=len(cases);report['compiler_sha256']=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest()
 (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
