"""Run 64-bit integer assignments between separately compiled C files."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'int64-codegen-check'
c.OUT.mkdir(parents=True,exist_ok=True)
MASK=(1<<64)-1
A=0xfedcba9876543210
B=0x123456789
SA=-0x123456789abcdef
SB=0x12345
Q=-(abs(SA)//SB)
EXPECTED={
 'sum':(A+B)&MASK,'difference':(A-B)&MASK,'product':(A*B)&MASK,
 'quotient':A//B,'remainder':A%B,'bits':(A&B)^(A|B),
 'shiftleft':(A<<13)&MASK,'shiftright':A>>13,'signedright':(SA>>13)&MASK,
 'signedquotient':Q&MASK,'signedremainder':(SA-Q*SB)&MASK,
 'widened':(-7)&MASK,'narrow_unsigned':65535,'nested':((A+B)*B)&MASK,
 'localresult':((A+B)^B)&MASK,
 'conditional':A,
 'wordparam':(-2147483647)&MASK,'uwordparam':0xfedcba98,'literal':0x8877665544332211,
 'loopresult':31,
 'narrowroundtrip':(-7)&MASK,
 'negated':(-SA)&MASK,'complemented':(~A)&MASK,
 'indirect':(A+B+1+A*B)&MASK,'farresult':(A+B)&MASK,'boxresult':(A+B)&MASK,
 'farodd':B,
 'nestedindirect':(A+A+B+1)&MASK,
 'widen_expression':(-22)&MASK,'widen_unsigned_expression':0x10000,
 'select_true':(A+B)&MASK,'select_false':B,'select_mixed':(-9)&MASK,
 'sequence_result':(A^B)&MASK,
 'nested_assign':(A+B+1)&MASK,'post_result':A,'pre_result':(A+2)&MASK,
 'post_indirect_result':(A+B+1+A*B)&MASK,
 'wide_from_bool':3,'wide_from_not':B,'wide_mixed_call':(A+2)&MASK,
 'goto_result':(A+18)&MASK,
 'sum_zero':0x12345678fffffff0,'sum_short':0x12345678fffffff6,
 'sum_many':0x123456790000011c,'sum_live':0x123456790000011d,
 'sum_early':0x12345678fffffff3,'sum_wide_body':0x1234567900000134,
 'sum_wide_index':0x12345678fffffff6,
 'sum_discard':0x123456790000011c,
}
KERNEL=r'''
extern unsigned sum_data[24];
unsigned long long mixed_discard(unsigned n,unsigned long long base){
    unsigned j,sum=0;
    for(j=0;j<n;(++j,0))sum+=sum_data[j];
    return base+sum;
}
unsigned long long mixed_sum(unsigned n,unsigned long long base){
    unsigned j,sum=0;
    for(j=0;j<n;++j)sum+=sum_data[j];
    return base+sum;
}
unsigned long long mixed_live(unsigned n,unsigned long long base){
    unsigned j,sum=0;
    unsigned long long saved=base+1ULL;
    for(j=0;j<n;++j)sum+=sum_data[j];
    return saved+sum;
}
unsigned long long mixed_early(unsigned n,unsigned long long base){
    unsigned j,sum=0;
    for(j=0;j<n;++j){if(j==2)return base+sum;sum+=sum_data[j];}
    return base+sum;
}
unsigned long long mixed_wide_body(unsigned n,unsigned long long base){
    unsigned j,sum=0;
    for(j=0;j<n;++j){sum+=sum_data[j];base+=1ULL;}
    return base+sum;
}
unsigned long long mixed_wide_index(unsigned n,unsigned long long base){
    unsigned j,sum=0;
    for(j=0;j<n;++j){sum+=sum_data[j];j=(unsigned)(base&0ULL)+j;}
    return base+sum;
}
extern volatile unsigned long long a,b;
extern volatile long long sa,sb;
long long wide_copy_source[2];
int word_shifts(void){
    unsigned long long u=a;
    long long s=sa;
    u <<= 16;
    s >>= 48;
    return u==0xba98765432100000ULL && s==-292 &&
        (a>>32)==0xfedcba98ULL && (b<<48)==0x6789000000000000ULL &&
        (sb>>16)==1 && (a>>0)==a;
}
void mask_wide_home(void){
    wide_copy_source[0]&=0xffffffffULL;
    wide_copy_source[0]^=0x123400000000ULL;
    wide_copy_source[0]=wide_copy_source[0]|0xffff000000000000ULL;
}
int zero_relations(long long x,unsigned long long u){
    return (x<0)+2*(0>x)+4*(0<=x)+8*(x<=0)+16*(0<x)+32*(x==0)+
        64*(u>0)+128*(0>=u)+256*(0<=u);
}
int zero_effect(unsigned long long *x){return ++*x<0;}
int fixed_relations(long long x,long long y){
    if(x<y)return 1;
    if(x==y)return 2;
    return x>y?4:0;
}
static int wide_compare_leaf(unsigned long long a,unsigned long long b){
    if(b<=a)return 9;
    return 4;
}
static __noinline int wide_compare_called(unsigned long long a,unsigned long long b){return a<b;}
int inline_wide_compare(long long a,long long b){return wide_compare_leaf(a,b)+wide_compare_called(a,b);}
int mixed_wide_equal(unsigned long long a,int b,unsigned long c){return (a==b)+2*(a==c);}
static unsigned long long wide_literal_target(unsigned x){
    unsigned long long value=(unsigned long long)x<<32;
    value|=x;
    return value+1ULL;
}
int optimize_wide_literal_call(void){return wide_literal_target(0x1234)==0x123400001235ULL;}
volatile unsigned long dead_long_ticks;
static __noinline long dead_long_effect(unsigned n){dead_long_ticks+=n;return 7;}
static long dead_long_pure(unsigned n){return 19339L/(long)(n|1);}
unsigned long long dead_long_update(unsigned n,unsigned long long wide){
    long unused=0x52ab1199L;
    unsigned long long unused_wide=0x53bd22aa00012345ULL;
    unused|=dead_long_effect(n);
    unused|=dead_long_pure(n);
    dead_long_pure(n);
    dead_long_pure(dead_long_effect(n));
    unused_wide+=dead_long_effect(n);
    return wide+1;
}
unsigned long empty_counter;
unsigned empty_loops(void){
    unsigned i,j;
    unsigned long zero_trip;
    for(empty_counter=1;empty_counter<=3;++empty_counter){
        for(i=0;i<1;++i)for(j=0;j<=1;++j){}
    }
    for(zero_trip=8;zero_trip<1;++zero_trip){}
    return empty_counter==4&&zero_trip==8;
}
unsigned long long joined_wide_literals(unsigned flag){
    unsigned long long selected;
    if(flag)selected=0x123400001234ULL;else selected=0x987600001234ULL;
    return selected^(flag?0x8000000000000000ULL:0ULL);
}
unsigned long long propagated_wide_alias(void){
    unsigned long long value,*alias=&value;
    *alias=-3;
    *alias=*alias**alias;
    return *alias;
}
unsigned wide_check_loop(void){
    unsigned long long value=0x60000000000ULL;
    unsigned i;
    for(i=0;i<8;++i)
        if(value/(0x200000000ULL<<i)!=(0x300u>>i))return i;
    return 8;
}
unsigned wide_check_loop_exit(void){
    unsigned long long value=0x60000000000ULL;
    unsigned i;
    for(i=0;i<8;++i)
        if(value/(0x200000000ULL<<i)!=(0x300u>>i)+(i==6))return i;
    return 8;
}
unsigned literal_conditional(void){
    unsigned long long high=0x100000000ULL;
    return high?(-0.0f?dead_long_effect(100):9):dead_long_effect(100);
}
unsigned literal_short_circuit(void){
    unsigned long long high=0x100000000ULL;
    unsigned zero=0;
    return (high||dead_long_effect(100))&&!(zero&&dead_long_effect(100));
}
static float scaled_from_word(unsigned n){return 2.0f*(float)n;}
static int check_float_delta(float a,float b){
    float delta=a-b;
    return delta==0.0f||a/delta>1000.0f;
}
int literal_nested_conversion(void){return check_float_delta(scaled_from_word(3),6.0f);}
void empty_public(unsigned ignored){return;}
unsigned long long discard_empty_argument(unsigned n,unsigned long long value){
    empty_public(dead_long_effect(n));
    return value;
}
static long literal_guarded_cast(float value){
    long result=(long)value;
    if(result==315L)return -31;
    if(!result)dead_long_effect(11);
    return result;
}
int guarded_conversion(void){return literal_guarded_cast(312.0f)==312L&&literal_guarded_cast(315.0f)==-31L;}
int live_guard_conversion(void){return literal_guarded_cast(0.0f)==0;}
static void literal_void_guard(unsigned long n){
    unsigned long value=n;
    value<<=8;
    if(value==0x30000000UL)dead_long_effect(13);
}
void dead_literal_void(void){literal_void_guard(0x100000UL);}
void live_literal_void(void){literal_void_guard(0x300000UL);}
static void opaque_void_guard(unsigned long mask){
    if(mask&(unsigned long)dead_long_effect(2))dead_long_effect(5);
}
void live_opaque_void(void){opaque_void_guard(8);}
static void check_wide_void(unsigned long long value,int flag){
    if(value==0x1234000000000000ULL){
        if(flag)dead_long_effect(6);
    }else if(!flag)dead_long_effect(7);
}
static int discarded_guarded_result(unsigned n,unsigned flag){
    if(n<3){if(flag)dead_long_effect(n);}else if(!flag)dead_long_effect(9);
}
void discarded_literal_calls(void){
    check_wide_void(0x1234000000000000ULL,0);
    discarded_guarded_result(2,0);
}
void live_wide_void(void){check_wide_void(0x1234000000000000ULL,1);}
static float wide_to_binary32(long long value){return (float)value;}
static long long binary32_to_wide(float value){return (long long)value;}
static unsigned long long binary32_to_unsigned_wide(float value){return (unsigned long long)value;}
int exact_wide_float_casts(void){
    return wide_to_binary32(-0x7fffffffffffffffLL-1)==-0x1p63f &&
           binary32_to_wide(-0x1p63f)==(-0x7fffffffffffffffLL-1) &&
           binary32_to_unsigned_wide(0x1.8p63f)==0xc000000000000000ULL &&
           binary32_to_unsigned_wide(-0.0f)==0;
}
int self_difference(int value){return value-value;}
unsigned long long self_xor(unsigned long long value){return value^value;}
int volatile_difference(volatile int *value){return *value-*value;}
int integral_zero_product(int value){return (int)((float)value*-0.0f/2.0f);}
unsigned long branch_long_masks(unsigned long value){
    unsigned long result=0;
    if(value&0x80000000UL)result|=1;
    if(value&0x00f00000UL)result|=2;
    if(0xffffUL&value)result|=4;
    return result;
}
unsigned long long shifted_literal(void){
    unsigned long long value=0x8000000000000000ULL;
    value>>=27;
    value<<=12;
    return value;
}
void double_indirect(unsigned *w,unsigned long *l,unsigned long long *q){
    *w+=*w; *l+=*l; *q+=*q;
}
unsigned long long shift_fixed_homes(unsigned long left,long right,unsigned long logical){
    left<<=1; right>>=1; logical>>=1;
    return (unsigned long long)left<<32 | (unsigned long)(right^logical);
}
static unsigned long long signed_wide_magnitude(long long value){return value<0?-value:value;}
unsigned long long widened_magnitude(int value){return signed_wide_magnitude(value);}
int same_widened_magnitude(int value,int expected){return signed_wide_magnitude(value)==(long long)expected;}
int magnitude_negative_literal(int value){return signed_wide_magnitude(value)==(-32767-1);}
unsigned long long negate_widened_unsigned(unsigned value){return -(unsigned long long)value;}
long long negate_widened_signed(int value){return -(long long)value;}
int signed_widened_sign(int value){return (long long)value<0;}
unsigned long long merged_high,merged_low,merged_result;
unsigned long long build_wide_halves(long high,long low){
    merged_high=high;merged_high<<=32;
    merged_low=low;merged_low&=0xffffffffULL;
    merged_result=merged_high|merged_low;return merged_result;
}
int literal_wide_halves(void){
    return 0xfffffffefffffffeULL < build_wide_halves(-2,-1);
}
static void set_qualified_tag(char *tag){*tag='q';}
int dead_qualified_loop(void){
    char tag=0;
    for(int i=0;i<39;++i){
        set_qualified_tag(&tag);
        if(*(const char *)&tag!='q')return 1;
    }
    return 0;
}
unsigned long long literal_word(unsigned long long x){return x^(unsigned char)255;}
unsigned long long literal_signed(unsigned long long x){return x ^ -2;}
unsigned long long literal_add(unsigned long long x){return 0x100000000ULL+x;}
unsigned long long fixed_wide_add(unsigned long long x,unsigned long long y){return x+y;}
int masked_wide_test(unsigned long long x){return (x&0x00100000ffff0001ULL)!=0;}
unsigned long long wide_updated;
void wide_discard_update(void){wide_updated++;}
void wide_shift_add(int word){wide_updated+=(unsigned long long)word<<32;}
void wide_shift_sub(unsigned long long value){wide_updated-=value<<16;}
unsigned long long wide_pre_update(void){return ++wide_updated;}
unsigned long long wide_post_update(void){return wide_updated--;}
unsigned long long unused_wide_array(unsigned long long x){
    unsigned long long dead[2]={0xa1b2c3d4e5f60718ULL,0x123456789abcdef0ULL};
    return x;
}
unsigned long long dead_indexed_array(unsigned long long x){
    unsigned long long dead[3];
    unsigned i;
    for(i=0;i<3;++i)dead[i]=0xa1b2c3d4e5f60718ULL;
    return x+i;
}
int immediate_relations(long long x,unsigned long long y){
    if(-0x100000001LL>x)return 1;
    if(0x8000000000000000ULL==y)return 2;
    return x<=-0x100000001LL?3:4;
}
unsigned long extract_long(long long x){return (unsigned long)(x>>32);}
unsigned extract_word(void){return (unsigned)(a>>48);}
unsigned char extract_byte(unsigned long long x){return (unsigned char)((x>>56)&255);}
unsigned extract_unaligned(void){return (unsigned)((a>>24)&65535);}
unsigned long long bounded_wide_loop(unsigned long long i){
    unsigned long long sum=0;
    for(i=2;i<=5;++i){
        if(i==3)continue;
        sum+=i;
    }
    return (sum<<16)+i;
}
unsigned long long wide_loop_index,wide_loop_result;
volatile unsigned wide_effect_a,wide_effect_b;
static long long widen_one(long long unused,int retained){return retained;}
long long widen_pure(int n){return widen_one(0x123456789abcdefLL,n);}
long long widen_with_effect(int n){return widen_one(wide_effect_a=29,n);}
static void accept_word(int value){if(value!=4099)wide_effect_b=31;}
static void accept_wide(unsigned long long value){if(value!=0x80000fffULL)wide_effect_b=32;}
int compose_literal_calls(void){
    int word;
    unsigned long long wide;
    accept_word((word=4096)+3);
    accept_wide((wide=4096)+0x7fffffffULL);
    return word+(int)wide;
}
void wide_loop_controls(unsigned value){
    for(wide_loop_index=15;wide_loop_index>=26;++wide_loop_index)++wide_effect_a;
    for(wide_loop_index=65531;wide_loop_index<65535;++wide_loop_index)
        wide_loop_result=wide_loop_index+value;
}
void wide_loop_repeat(void){
    for(wide_loop_index=11;wide_loop_index<=55;++wide_loop_index)wide_loop_result=0xABCDEFULL;
}
static unsigned long long wide_effect_sub(unsigned long long a,unsigned long long b){return a-b;}
int wide_effect_equal(int value){
    return wide_effect_sub((unsigned long long)(wide_effect_a=17)|0xffffffffffffffffULL,1)==(long long)value;
}
void discard_integer_test(unsigned value){
    ((wide_effect_a=value)|(wide_effect_b=value+1))!=0;
    (unsigned long long)(wide_effect_b=value+1);
}
long long wide_signed_long_product(long a,long b){return (long long)a*b;}
unsigned long long wide_signed_word_product(unsigned long long a,int b){return a*b;}
unsigned long long wide_unsigned_word_product(unsigned long long a,unsigned b){return a*b;}
unsigned long long wide_count_sum;
int signed_counted_wide(int count){
    int i;
    wide_count_sum=0;
    for(i=0;i<count;++i){
        if(i==2)continue;
        wide_count_sum+=(unsigned)i;
    }
    return i;
}
void indirect_wide_update(unsigned long long *p,unsigned word){
    *p=0x0000aaaa0000aaaaULL;
    *p=*p+word;
}
int wide_arg_check(long long,unsigned long long);
int push_wide_args(long long x){return wide_arg_check(x,0x12340000abcd9876ULL);}
int copy_wide_index(unsigned i){
    long long copy;
    copy=wide_copy_source[i];
    return wide_arg_check(copy,0x12340000abcd9876ULL);
}
static int wide_inactive_overflow=0 && -(-9223372036854775807LL-1LL);
unsigned long long wide_literal_ops(void){
    return (((~0ULL)>>33)+2)*3+(unsigned long long)(-0x100000001LL>>32)
        + (0x100000000ULL > -1L) + wide_inactive_overflow;
}
unsigned long long wide_magnitude(unsigned long long x){return (long long)x<0?-x:x;}
unsigned long long wide_rotate_words(unsigned long long x){return (x<<32)|(x>>32);}
unsigned long long wide_rotate_signed(unsigned long long x){return ((long long)x>>4)|(x<<60);}
unsigned long long wide_rotate_opposite(unsigned long long x){return (x<<4)|((long long)x>>60);}
unsigned long long div_power(unsigned long long x,unsigned shift){return x/(8ULL<<shift);}
unsigned long long div_power_constant(unsigned long long x){return x/0x100000000ULL;}
unsigned long long full_word_long(unsigned x,unsigned long y){return (unsigned long long)x*y;}
unsigned long long full_long_word(unsigned long x,unsigned y){return (unsigned long long)x*y;}
unsigned long long full_words(unsigned x,unsigned y){return (unsigned long long)x*y;}
extern volatile unsigned long long sum,difference,product,quotient,remainder,bits,shiftleft,shiftright,narrow_unsigned,nested,localresult;
extern volatile long long signedright,signedquotient,signedremainder,widened;
extern volatile unsigned long long conditional;
extern volatile long long wordparam;
extern volatile unsigned long long uwordparam,literal;
extern volatile unsigned long long loopresult;
extern volatile unsigned loopvisits;
extern volatile long long narrowroundtrip;
extern volatile long long negated;
extern volatile unsigned long long complemented;
struct box { unsigned tag; unsigned long long value; };
extern volatile struct box box;
extern volatile unsigned long long cells[3];
extern volatile unsigned long long indirect,farresult,boxresult,farodd,nestedindirect;
extern volatile unsigned address_calls,index_calls;
extern volatile long long widen_expression,select_mixed;
extern volatile unsigned long long widen_unsigned_expression,select_true,select_false,sequence_result;
extern volatile unsigned select_calls;
extern volatile unsigned mixed_result,mixed_call,mixed_condition,mixed_short,mixed_two_calls;
extern volatile unsigned switch_result,switch_calls;
extern volatile unsigned long long goto_result;
extern volatile unsigned goto_visits;
extern volatile unsigned long long nested_assign,post_result,pre_result,post_indirect_result;
extern volatile unsigned long long wide_from_bool,wide_from_not,wide_mixed_call;
int select_side(void){select_calls++;return 1;}
int combine(int x,int y){return x*10+y;}
unsigned long long wide_add_int(unsigned long long x,int n){return x+(long long)n;}
unsigned long long switch_value(void){switch_calls++;return a;}
void switch_kernel(void){
    switch(switch_value()){
    case 0x0000000076543210ULL:switch_result=100;break;
    case 0xfedcba9876543210ULL:switch_result=1;
    case 0x123456789abcdef0ULL:switch_result+=2;break;
    default:switch_result=200;
    }
    switch(sa){case -0x123456789abcdefLL:switch_result+=4;break;default:switch_result=300;}
    switch(b){case 0x100000001ULL:switch_result=400;break;default:switch_result+=8;}
}
void goto_kernel(void){
    unsigned long long value=a; int i=0;
    goto check;
step:
    value+=(unsigned long long)i;
check:
    goto_visits++;
    if(i++<5)goto step;
    goto inside;
    while(i<9){
inside:
        value+=1ULL;
        i++;
    }
    goto_result=value;
    goto done;
    goto_result=0ULL;
done:
    return;
}
volatile unsigned long long *next_pointer(void){address_calls++;return &indirect;}
unsigned next_index(void){index_calls++;return 1;}
void kernel(unsigned int count,int small,long word,unsigned long uword){
    unsigned long long local;
    int narrowlocal;
    sum=a+b; difference=a-b; product=a*b;
    quotient=a/b; remainder=a%b; bits=(a&b)^(a|b);
    shiftleft=a<<count; shiftright=a>>count;
    signedright=sa>>count; signedquotient=sa/sb; signedremainder=sa%sb;
    widened=small; narrow_unsigned=(unsigned int)65535U;
    nested=(a+b)*b;
    local=a+b; local^=b; localresult=local;
    if(sa<sb) conditional=a; else conditional=b;
    if(sa>sb) conditional=b; else conditional=a;
    wordparam=word; uwordparam=uword; literal=0x8877665544332211ULL;
    narrowlocal=(int)widened; narrowroundtrip=narrowlocal;
    negated=-sa; complemented=~a;
    widen_expression=(long long)(small*3-1);
    widen_unsigned_expression=(unsigned long long)((unsigned long)65535+1UL);
    select_true=(a>b && select_side()) ? a+b : b;
    select_false=(sa>sb && select_side()) ? a : b;
    select_mixed=(count==13) ? -9 : sa;
    sequence_result=(select_side(),a^b);
    local=a; post_result=local++; pre_result=++local;
    nested_assign=(local=a+b)+1ULL;
    mixed_result=(a>b)+(sa<sb)*3+((unsigned int)a&15);
    mixed_call=combine((a>b),(int)b);
    mixed_two_calls=combine((a>b),(b>a));
    mixed_condition=((a>b)+1==2)?17:19;
    mixed_short=(sa>sb && select_side()) || (a>b && select_side());
    wide_from_bool=(unsigned long long)((a>b)+(sa<sb)*2);
    wide_from_not=b+(!a);
    wide_mixed_call=wide_add_int(a,(a>b)+(sa<sb));
    cells[1]=a+b; cells[2]=cells[1]^b; box.value=cells[2];
    cells[0]=1ULL; cells[0]++;
}
int signed_compare(void){return sa<sb;}
int unsigned_compare(void){return a>b;}
unsigned long long dynamic_rhs(void);
long long dynamic_signed_rhs(void);
int dynamic_compare(void){return a>dynamic_rhs();}
int dynamic_signed_compare(void){return sa<dynamic_signed_rhs();}
int equal_compare(void){return a==a;}
int widened_complement(unsigned char byte,int word){if(~byte+(long long)word)return 7;return 11;}
int widened_difference(int left,int right){return 0LL==(long long)left-right;}
int widened_bool(signed char byte,int word){return (_Bool)((long long)word+byte);}
int widened_signed_limit(int left,int right){return (_Bool)((long long)left+right);}
int widened_unsigned_limit(unsigned left,unsigned right){return (_Bool)((unsigned long long)left+right);}
int wide_bool(unsigned long long value){return (_Bool)value;}
int mixed_compare(void){return sa>0xffffffffUL;}
int expression_compare(void){return (a-b)<a;}
int pointer_compare(void){return *next_pointer()==indirect;}
long narrow_result(void){unsigned long long local;local=a+b;return -2147483647L;}
int narrow16(void){return (int)a;}
unsigned long narrow32(void){return (unsigned long)a;}
void loop_kernel(void){
    unsigned long long i=0;
    unsigned j=0;
    loopresult=0;
    for(i=0;i<10ULL;i++){
        loopvisits++;
        if(i==3ULL)continue;
        loopresult+=i;
        if(i==7ULL)break;
    }
    while(i){loopvisits++;i--;}
    do{loopvisits++;i++;}while(i<3ULL);
    if(i && !(i==0ULL))loopresult+=i;
    while(j<3){loopvisits++;loopresult+=1ULL;j++;}
}
void pointer_kernel(void){
    volatile unsigned long long * __far fp=(volatile unsigned long long * __far)0x7efffcUL;
    volatile struct box * __far bp=&box;
    *next_pointer()=a;
    *next_pointer()+=b;
    cells[next_index()]=*next_pointer()^b;
    (*next_pointer())++;
    nestedindirect=a+*next_pointer();
    *next_pointer()+=a*b;
    post_indirect_result=(*next_pointer())++;
    (*next_pointer())--;
    *fp=a; *fp+=b; farresult=*fp;
    fp=(volatile unsigned long long * __far)0x7effffUL; *fp=b; farodd=*fp;
    bp->value=a; bp->value+=b; boxresult=bp->value;
}
'''
DRIVER=r'''
unsigned sum_data[24];
volatile unsigned long long sum_zero,sum_short,sum_many,sum_live,sum_early,sum_wide_body,sum_wide_index;
volatile unsigned long long sum_discard;
unsigned long long mixed_discard(unsigned,unsigned long long);
unsigned long long mixed_sum(unsigned,unsigned long long);
unsigned long long mixed_live(unsigned,unsigned long long);
unsigned long long mixed_early(unsigned,unsigned long long);
unsigned long long mixed_wide_body(unsigned,unsigned long long);
unsigned long long mixed_wide_index(unsigned,unsigned long long);
void mixed_checks(void){
    unsigned i;
    for(i=0;i<24;++i)sum_data[i]=i+1;
    sum_zero=mixed_sum(0,0x12345678fffffff0ULL);
    sum_short=mixed_sum(3,0x12345678fffffff0ULL);
    sum_many=mixed_sum(24,0x12345678fffffff0ULL);
    sum_live=mixed_live(24,0x12345678fffffff0ULL);
    sum_early=mixed_early(24,0x12345678fffffff0ULL);
    sum_wide_body=mixed_wide_body(24,0x12345678fffffff0ULL);
    sum_wide_index=mixed_wide_index(3,0x12345678fffffff0ULL);
    sum_discard=mixed_discard(24,0x12345678fffffff0ULL);
}
volatile unsigned long long a=0xfedcba9876543210ULL,b=0x123456789ULL;
unsigned long long dynamic_rhs(void){return b;}
long long dynamic_signed_rhs(void){return -1LL;}
volatile long long sa=-0x123456789abcdefLL,sb=0x12345LL;
volatile unsigned long long sum,difference,product,quotient,remainder,bits,shiftleft,shiftright,narrow_unsigned,nested,localresult;
volatile long long signedright,signedquotient,signedremainder,widened;
volatile unsigned long long conditional;
volatile long long wordparam;
volatile unsigned long long uwordparam,literal;
volatile unsigned long long loopresult;
volatile unsigned loopvisits;
volatile long long narrowroundtrip;
volatile long long negated;
volatile unsigned long long complemented;
struct box { unsigned tag; unsigned long long value; };
volatile struct box box;
volatile unsigned long long cells[3];
volatile unsigned long long indirect,farresult,boxresult,farodd,nestedindirect;
volatile unsigned address_calls,index_calls;
volatile long long widen_expression,select_mixed;
volatile unsigned long long widen_unsigned_expression,select_true,select_false,sequence_result;
volatile unsigned select_calls;
volatile unsigned mixed_result,mixed_call,mixed_condition,mixed_short,mixed_two_calls;
volatile unsigned switch_result,switch_calls;
volatile unsigned long long goto_result;
volatile unsigned goto_visits;
volatile unsigned long long nested_assign,post_result,pre_result,post_indirect_result;
volatile unsigned long long wide_from_bool,wide_from_not,wide_mixed_call;
void kernel(unsigned int,int,long,unsigned long);
int word_shifts(void);int zero_relations(long long,unsigned long long);
int zero_effect(unsigned long long *);
int fixed_relations(long long,long long);
unsigned long long literal_word(unsigned long long);
unsigned long long literal_signed(unsigned long long);
unsigned long long literal_add(unsigned long long);
unsigned long long fixed_wide_add(unsigned long long,unsigned long long);
int masked_wide_test(unsigned long long);
extern unsigned long long wide_updated;
void wide_shift_add(int);void wide_shift_sub(unsigned long long);
int literal_wide_halves(void);
void wide_discard_update(void);
unsigned long long wide_pre_update(void),wide_post_update(void);
unsigned long long unused_wide_array(unsigned long long);
unsigned long long dead_indexed_array(unsigned long long);
int immediate_relations(long long,unsigned long long);
int inline_wide_compare(long long,long long);
int mixed_wide_equal(unsigned long long,int,unsigned long);
int optimize_wide_literal_call(void);
extern volatile unsigned long dead_long_ticks;
unsigned long long dead_long_update(unsigned,unsigned long long);
unsigned empty_loops(void);
unsigned long long joined_wide_literals(unsigned);
unsigned long long propagated_wide_alias(void);
unsigned wide_check_loop(void);
unsigned wide_check_loop_exit(void);
unsigned literal_conditional(void);
unsigned literal_short_circuit(void);
int literal_nested_conversion(void);
unsigned long long discard_empty_argument(unsigned,unsigned long long);
int guarded_conversion(void),live_guard_conversion(void),dead_qualified_loop(void);
void dead_literal_void(void),live_literal_void(void);
void live_opaque_void(void);
void discarded_literal_calls(void),live_wide_void(void);
int exact_wide_float_casts(void);
int integral_zero_product(int);
unsigned long branch_long_masks(unsigned long);
unsigned long long shifted_literal(void),shift_fixed_homes(unsigned long,long,unsigned long);
void double_indirect(unsigned *,unsigned long *,unsigned long long *);
unsigned long long widened_magnitude(int),negate_widened_unsigned(unsigned);
long long negate_widened_signed(int);
int same_widened_magnitude(int,int),signed_widened_sign(int);
int magnitude_negative_literal(int);
extern unsigned long long merged_high,merged_low,merged_result;
unsigned long long build_wide_halves(long,long);
int push_wide_args(long long);
int copy_wide_index(unsigned);
extern long long wide_copy_source[2];
void mask_wide_home(void);
unsigned long long wide_literal_ops(void);
unsigned long long wide_magnitude(unsigned long long);
unsigned long long wide_rotate_words(unsigned long long);
unsigned long long wide_rotate_signed(unsigned long long);
unsigned long long wide_rotate_opposite(unsigned long long);
unsigned long long div_power(unsigned long long,unsigned);
unsigned long long div_power_constant(unsigned long long);
unsigned long long full_word_long(unsigned,unsigned long);
unsigned long long full_long_word(unsigned long,unsigned);
unsigned long long full_words(unsigned,unsigned);
int wide_arg_check(long long x,unsigned long long y){
    return x==-0x123456789abcdefLL && y==0x12340000abcd9876ULL;
}
unsigned long extract_long(long long);unsigned extract_word(void);
unsigned char extract_byte(unsigned long long);unsigned extract_unaligned(void);
unsigned long long bounded_wide_loop(unsigned long long);
extern unsigned long long wide_loop_index,wide_loop_result;
extern volatile unsigned wide_effect_a,wide_effect_b;
long long widen_pure(int),widen_with_effect(int);
int compose_literal_calls(void);
void wide_loop_controls(unsigned);void wide_loop_repeat(void);
int wide_effect_equal(int);void discard_integer_test(unsigned);
long long wide_signed_long_product(long,long);
unsigned long long wide_signed_word_product(unsigned long long,int);
unsigned long long wide_unsigned_word_product(unsigned long long,unsigned);
extern unsigned long long wide_count_sum;
int signed_counted_wide(int);
void indirect_wide_update(unsigned long long *,unsigned);
int signed_compare(void);int unsigned_compare(void);int dynamic_compare(void);int dynamic_signed_compare(void);
int equal_compare(void);int mixed_compare(void);int expression_compare(void);int pointer_compare(void);
int widened_complement(unsigned char,int);int widened_difference(int,int);int widened_bool(signed char,int);
int widened_signed_limit(int,int);int widened_unsigned_limit(unsigned,unsigned);int wide_bool(unsigned long long);
long narrow_result(void);
int narrow16(void);unsigned long narrow32(void);
void loop_kernel(void);
void pointer_kernel(void);
void switch_kernel(void);
void goto_kernel(void);
static volatile unsigned long long mixed_selector;
static volatile unsigned mixed_effects;
static __noinline unsigned long long mixed_tick(void){
    ++mixed_effects;
    return mixed_selector;
}
static int nested_mixed_checks(void){
    unsigned long x[2]={6,2};
    unsigned long *p=x;
    volatile unsigned long * __far banked_slot=(volatile unsigned long * __far)0x7f1900UL;
    volatile unsigned long * __far *which=&banked_slot;
    mixed_selector=0x100000000ULL;
    mixed_effects=0;
    *p++ ^= (((mixed_tick()|4ULL)>6ULL ? x : x+1)==x);
    if(x[0]!=7||p!=x+1||mixed_effects!=1)return 1;
    *banked_slot=9;
    **(mixed_tick() ? which : which+1) += (mixed_tick()>7ULL);
    if(**(mixed_tick() ? which : which+1)!=10||mixed_effects!=4)return 2;
    return 0;
}
int main(void){if(nested_mixed_checks())return 8;mixed_checks();kernel(13,-7,-2147483647L,0xfedcba98UL);loop_kernel();pointer_kernel();switch_kernel();goto_kernel();
    if(widened_complement(255,256)!=11 || widened_complement(255,-32768)!=7 || widened_complement(0,1)!=11)return 3;
    if(!widened_difference(-32768,-32768) || widened_difference(-32768,32767) || widened_difference(32767,-32768))return 4;
    if(widened_bool(-128,128) || !widened_bool(-128,-32768) || !widened_bool(127,32767))return 5;
    if(!widened_signed_limit(-32768,-32768) || widened_signed_limit(-1,1) ||
       !widened_unsigned_limit(65535U,1) || widened_unsigned_limit(0,0) || !wide_bool(1ULL<<48) || wide_bool(0))return 6;
    { unsigned long long n=5;
      if(zero_relations(-1,0)!=395 || zero_relations(0,1)!=364 ||
         zero_relations(1,1)!=340 || zero_effect(&n) || n!=6)return 7; }
    if(fixed_relations(-0x100000001LL,0x100000001LL)!=1 ||
       fixed_relations(0x100000001LL,0x100000001LL)!=2 ||
       fixed_relations(0x100000001LL,0x100000000LL)!=4)return 8;
    if(literal_word(0x123456789abcdef0ULL)!=0x123456789abcde0fULL ||
       literal_signed(0x123456789abcdef0ULL)!=0xedcba9876543210eULL ||
       literal_add(0x0000ffff12345678ULL)!=0x0001000012345678ULL ||
       fixed_wide_add(0x12345678ffffffffULL,1)!=0x1234567900000000ULL)return 9;
    if(immediate_relations(-0x100000002LL,0)!=1 ||
       immediate_relations(0,0x8000000000000000ULL)!=2 ||
       immediate_relations(-0x100000001LL,1)!=3 || immediate_relations(1,1)!=4)return 10;
    if(extract_long(-0x123456789abcdefLL)!=0xfedcba98UL || extract_word()!=0xfedcU)return 11;
    if(extract_byte(0xfedcba9876543210ULL)!=0xfeU || extract_unaligned()!=0x9876U)return 15;
    if(bounded_wide_loop(0xfedcba9876543210ULL)!=0xb0006ULL)return 16;
    wide_effect_a=9;
    wide_loop_controls(5);
    if(wide_loop_index!=65535ULL||wide_loop_result!=65539ULL||wide_effect_a!=9)return 47;
    wide_loop_repeat();
    if(wide_loop_index!=56ULL||wide_loop_result!=0xABCDEFULL)return 48;
    if(!wide_effect_equal(-2)||wide_effect_a!=17||wide_effect_equal(3))return 49;
    discard_integer_test(23);
    if(wide_effect_a!=23||wide_effect_b!=24)return 50;
    if(widen_pure(-3)!=-3||widen_with_effect(-7)!=-7||wide_effect_a!=29||
       compose_literal_calls()!=8192||wide_effect_b!=24)return 55;
    if(wide_signed_long_product(-2147483647L-1,-2147483647L-1)!=0x4000000000000000LL||
       wide_signed_long_product(-2147483647L-1,2147483647L)!=-0x3fffffff80000000LL||
       wide_signed_long_product(1,-65535L)!=-65535LL||
       wide_signed_long_product(-65535L,-65535L)!=0xfffe0001LL)return 51;
    if(wide_signed_word_product(0x12345678ULL,-32768)!=0xfffff6e5d4c40000ULL||
       wide_unsigned_word_product(0xfedcba9876543210ULL,16)!=0xedcba98765432100ULL||
       wide_unsigned_word_product(~0ULL,3)!=0xfffffffffffffffdULL||
       wide_unsigned_word_product(~0ULL,0))return 52;
    if(signed_counted_wide(-32768)||wide_count_sum||signed_counted_wide(0)||wide_count_sum||
       signed_counted_wide(5)!=5||wide_count_sum!=8ULL)return 53;
    indirect_wide_update(&wide_count_sum,65535);
    if(wide_count_sum!=0x0000aaaa0001aaa9ULL)return 54;
    if(!push_wide_args(-0x123456789abcdefLL) || push_wide_args(0))return 12;
    wide_copy_source[1]=-0x123456789abcdefLL;
    if(!copy_wide_index(1)||copy_wide_index(0))return 17;
    if(inline_wide_compare(-1,1)!=9||inline_wide_compare(1,-1)!=5)return 22;
    if(mixed_wide_equal(~0ULL,-1,0xffffffffUL)!=1||
       mixed_wide_equal(0xffffffffULL,-1,0xffffffffUL)!=2||mixed_wide_equal(5,5,5)!=3)return 26;
    if(!optimize_wide_literal_call())return 28;
    if(dead_long_update(7,0x123400000000ULL)!=0x123400000001ULL||dead_long_ticks!=21)return 29;
    if(!empty_loops()||joined_wide_literals(0)!=0x987600001234ULL||
       joined_wide_literals(1)!=0x8000123400001234ULL||propagated_wide_alias()!=9)return 30;
    if(wide_check_loop()!=8||wide_check_loop_exit()!=6)return 31;
    if(literal_conditional()!=9||!literal_short_circuit()||
       !literal_nested_conversion()||dead_long_ticks!=21)return 32;
    if(discard_empty_argument(7,0x987612346789ULL)!=0x987612346789ULL||dead_long_ticks!=28)return 33;
    if(!guarded_conversion()||dead_long_ticks!=28||
       !live_guard_conversion()||dead_long_ticks!=39||dead_qualified_loop())return 34;
    dead_literal_void();
    if(dead_long_ticks!=39||!exact_wide_float_casts())return 35;
    live_literal_void();
    if(dead_long_ticks!=52)return 36;
    live_opaque_void();
    if(dead_long_ticks!=54)return 40;
    discarded_literal_calls();
    if(dead_long_ticks!=54)return 44;
    live_wide_void();
    if(dead_long_ticks!=60)return 45;
    if(integral_zero_product(-32768)||branch_long_masks(0x80f00000UL)!=3||
       branch_long_masks(0x00008000UL)!=4||branch_long_masks(0x11010000UL)!=0||
       shifted_literal()!=0x1000000000000ULL)return 37;
    { unsigned w=0x8800; unsigned long l=0x00808000UL; unsigned long long q=0x4000900080008000ULL;
      double_indirect(&w,&l,&q);
      if(w!=0x1000||l!=0x01010000UL||q!=0x8001200100010000ULL)return 38; }
    if(shift_fixed_homes(0x12349100UL,-0x70000003L,0x81000002UL)!=0x24692200877fffffULL)return 39;
    if(widened_magnitude(-32768)!=32768ULL||!same_widened_magnitude(-32767,32767)||
       same_widened_magnitude(-32768,-32768)||same_widened_magnitude(0,-1)||
       !same_widened_magnitude(0,0)||magnitude_negative_literal(-32768))return 41;
    if(negate_widened_unsigned(65535U)!=0xffffffffffff0001ULL||negate_widened_unsigned(0)!=0||
       negate_widened_signed(-32768)!=32768LL||negate_widened_signed(32767)!=-32767LL||
       !signed_widened_sign(-32768)||signed_widened_sign(32767))return 42;
    if(build_wide_halves(-2,-1)!=0xfffffffeffffffffULL||merged_high!=0xfffffffe00000000ULL||
       merged_low!=0xffffffffULL||merged_result!=0xfffffffeffffffffULL)return 43;
    merged_high=merged_low=merged_result=0;
    if(!literal_wide_halves()||merged_high!=0xfffffffe00000000ULL||
       merged_low!=0xffffffffULL||merged_result!=0xfffffffeffffffffULL)return 46;
    if(masked_wide_test(0xffefffff0000fffeULL)||!masked_wide_test(1)||
       !masked_wide_test(0x0010000000000000ULL)||!masked_wide_test(0x0000000080000000ULL))return 23;
    wide_updated=0xfffffffffffffffeULL;
    wide_discard_update();
    if(wide_updated!=~0ULL||wide_pre_update()||wide_post_update()||wide_updated!=~0ULL)return 24;
    wide_updated=0x1000000012345678ULL;wide_shift_add(-3);
    if(wide_updated!=0x0ffffffd12345678ULL)return 44;
    wide_shift_sub(0x0ffffffd1235ULL);
    if(wide_updated!=0xffffffffffff5678ULL)return 45;
    if(unused_wide_array(0x3000ffeeddccbbaaULL)!=0x3000ffeeddccbbaaULL)return 25;
    if(dead_indexed_array(0x3000ffeeddccbbaaULL)!=0x3000ffeeddccbbadULL)return 27;
    if(wide_literal_ops()!=0x180000001ULL)return 18;
    wide_copy_source[0]=-0x123456789abcdf0LL;
    mask_wide_home();
    if((unsigned long long)wide_copy_source[0]!=0xffff123476543210ULL)return 21;
    if(wide_magnitude(0xffff0000aaaaffffULL)!=0xffff55550001ULL||
       wide_magnitude(0x700012340000ffffULL)!=0x700012340000ffffULL||
       wide_magnitude(0x8000000000000000ULL)!=0x8000000000000000ULL)return 19;
    if(wide_rotate_words(0x1122334455667788ULL)!=0x5566778811223344ULL||
       wide_rotate_signed(0x1122334455667788ULL)!=0x8112233445566778ULL||
       wide_rotate_signed(0x9122334455667788ULL)!=0xf912233445566778ULL||
       wide_rotate_opposite(0x1122334455667788ULL)!=0x1223344556677881ULL||
       wide_rotate_opposite(0x9122334455667788ULL)!=0xfffffffffffffff9ULL)return 20;
    if(div_power(0xfedcba9876543210ULL,1)!=0x0fedcba987654321ULL ||
       div_power(0xfedcba9876543210ULL,60)!=1 ||
       div_power_constant(0xfedcba9876543210ULL)!=0xfedcba98ULL)return 13;
    if(full_word_long(65535U,0xffffffffUL)!=0xfffeffff0001ULL ||
       full_long_word(0xffffffffUL,65535U)!=0xfffeffff0001ULL ||
       full_words(65535U,65535U)!=0xfffe0001ULL || full_word_long(0,0xffffffffUL)!=0)return 14;
    return !word_shifts() || signed_compare()!=1 || unsigned_compare()!=1 ||
    equal_compare()!=1 || mixed_compare()!=0 || expression_compare()!=1 || dynamic_compare()!=1 ||
    dynamic_signed_compare()!=1 || narrow_result()!=-2147483647L ||
    narrow16()!=0x3210 || narrow32()!=0x76543210UL || loopvisits!=21 || pointer_compare()!=1 || address_calls!=9 || index_calls!=1 || select_calls!=3 ||
    mixed_result!=4 || mixed_call!=0x6793 || mixed_two_calls!=10 || mixed_condition!=17 || mixed_short!=1 || switch_result!=15 || switch_calls!=1 || goto_visits!=6;}
'''


def main():
    src=c.OUT/'kernel.c';src.write_text(KERNEL)
    asm=c.OUT/'kernel.s';obj=c.OUT/'kernel.o'
    c.run([ROOT/'build/zicc.exe',src,'-o',asm])
    text=asm.read_text()
    for function in ('mixed_sum','mixed_live'):
        body=text.split(f'_{function}:\n',1)[1].split(f'__size_{function}',1)[0]
        loop=body.split('; register cursor sum_data[j] in X, displacement 0\n',1)[1]
        loop=loop.split('    bne ',1)[0]
        assert '    lda a:$0000,x\n' in loop and '    inx\n    inx\n' in loop,loop
        assert '    asl a\n' not in loop and '    tax\n' not in loop,loop
    for function in ('mixed_early','mixed_wide_body','mixed_wide_index'):
        body=text.split(f'_{function}:\n',1)[1].split(f'__size_{function}',1)[0]
        assert '; register cursor ' not in body,function
    for helper in ('__mul64','__uquot64','__umod64','__sdiv64','__smod64','__shl64','__ushr64','__sshr64','__scmp64','__ucmp64'):
        assert '.import '+helper in text,helper
    shifts=text.split('_word_shifts:\n',1)[1].split('__size_word_shifts',1)[0]
    assert all(helper not in shifts for helper in ('__shl64','__ushr64','__sshr64')),shifts
    assert re.search(r'lda a:\$[0-9A-F]+,y\n    sta a:\$[0-9A-F]+,y',shifts),shifts
    mask=text.split('_mask_wide_home:\n',1)[1].split('__size_mask_wide_home',1)[0]
    assert '__arith_lhs' not in mask and 'stz a:.loword(_wide_copy_source+' in mask,mask
    fixed=text.split('_fixed_relations:\n',1)[1].split('__size_fixed_relations',1)[0]
    assert '__arith_lhs' not in fixed and 'cmp ' in fixed,fixed
    inlined=text.split('_inline_wide_compare:\n',1)[1].split('__size_inline_wide_compare',1)[0]
    assert '_wide_compare_leaf' not in inlined and '_wide_compare_called' in inlined,inlined
    mixed=text.split('_mixed_wide_equal:\n',1)[1].split('__size_mixed_wide_equal',1)[0]
    assert 'cmp a:' in mixed and 'cmp64' not in mixed,mixed
    constant=text.split('_optimize_wide_literal_call:\n',1)[1].split('__size_optimize_wide_literal_call',1)[0]
    assert '_wide_literal_target' not in constant and '__arith_lhs' not in constant,constant
    dead=text.split('_dead_long_update:\n',1)[1].split('__size_dead_long_update',1)[0]
    assert '_dead_long_effect' in dead and '$52AB' not in dead and '$1199' not in dead,dead
    assert '_dead_long_pure' not in dead,dead
    assert '$53BD' not in dead and '$22AA' not in dead,dead
    loops=text.split('_empty_loops:\n',1)[1].split('__size_empty_loops',1)[0]
    assert '; loop lowering:' not in loops,loops
    alias=text.split('_propagated_wide_alias:\n',1)[1].split('__size_propagated_wide_alias',1)[0]
    assert '__mul64' not in alias,alias
    checked=text.split('_wide_check_loop:\n',1)[1].split('__size_wide_check_loop',1)[0]
    assert 'div64' not in checked,checked
    selection=text.split('_literal_conditional:\n',1)[1].split('__size_literal_conditional',1)[0]
    assert '_dead_long_effect' not in selection,selection
    short=text.split('_literal_short_circuit:\n',1)[1].split('__size_literal_short_circuit',1)[0]
    assert '_dead_long_effect' not in short,short
    conversion=text.split('_literal_nested_conversion:\n',1)[1].split('__size_literal_nested_conversion',1)[0]
    assert not any('jsr' in line for line in conversion.splitlines()),conversion
    empty=text.split('_discard_empty_argument:\n',1)[1].split('__size_discard_empty_argument',1)[0]
    assert '_empty_public' not in empty and '_dead_long_effect' in empty,empty
    guarded=text.split('_guarded_conversion:\n',1)[1].split('__size_guarded_conversion',1)[0]
    assert 'jsr' not in guarded,guarded
    void_guard=text.split('_dead_literal_void:\n',1)[1].split('__size_dead_literal_void',1)[0]
    assert 'jsr' not in void_guard,void_guard
    discarded=text.split('_discarded_literal_calls:\n',1)[1].split('__size_discarded_literal_calls',1)[0]
    assert 'jsr' not in discarded,discarded
    exact_casts=text.split('_exact_wide_float_casts:\n',1)[1].split('__size_exact_wide_float_casts',1)[0]
    assert 'jsr' not in exact_casts,exact_casts
    difference=text.split('_self_difference:\n',1)[1].split('__size_self_difference',1)[0]
    xor_self=text.split('_self_xor:\n',1)[1].split('__size_self_xor',1)[0]
    volatile_diff=text.split('_volatile_difference:\n',1)[1].split('__size_volatile_difference',1)[0]
    assert 'sbc' not in difference and 'eor' not in xor_self and 'sbc' in volatile_diff
    zero_product=text.split('_integral_zero_product:\n',1)[1].split('__size_integral_zero_product',1)[0]
    assert 'jsr' not in zero_product,zero_product
    doubling=text.split('_double_indirect:\n',1)[1].split('__size_double_indirect',1)[0]
    assert doubling.count('asl a:$0000,x')==3 and doubling.count('rol a:')==4,doubling
    magnitude=text.split('_widened_magnitude:\n',1)[1].split('__size_widened_magnitude',1)[0]
    assert 'jsr' not in magnitude,magnitude
    qualified=text.split('_dead_qualified_loop:\n',1)[1].split('__size_dead_qualified_loop',1)[0]
    assert '; loop lowering:' not in qualified and 'jsr' not in qualified,qualified
    literal=text.split('_literal_word:\n',1)[1].split('__size_literal_word',1)[0]
    assert literal.count('    eor #$00FF\n')==1 and '__arith_lhs+8' not in literal,literal
    arithmetic=text.split('_fixed_wide_add:\n',1)[1].split('__size_fixed_wide_add',1)[0]
    assert arithmetic.count('    adc a:')==4 and '    lda z:__arith_lhs' not in arithmetic,arithmetic
    masked=text.split('_masked_wide_test:\n',1)[1].split('__size_masked_wide_test',1)[0]
    assert '__arith_lhs' not in masked and '    and #$0010\n' in masked,masked
    update=text.split('_wide_discard_update:\n',1)[1].split('__size_wide_discard_update',1)[0]
    assert '__arith_lhs' not in update and 'bcc ' in update,update
    add_shift=text.split('_wide_shift_add:\n',1)[1].split('__size_wide_shift_add',1)[0]
    sub_shift=text.split('_wide_shift_sub:\n',1)[1].split('__size_wide_shift_sub',1)[0]
    assert add_shift.count('    adc z:')==2 and '__arith_lhs+4' not in add_shift,add_shift
    assert sub_shift.count('    sbc z:')==3,sub_shift
    literal_halves=text.split('_literal_wide_halves:\n',1)[1].split('__size_literal_wide_halves',1)[0]
    assert 'jsr' not in literal_halves and '__arith_lhs' not in literal_halves,literal_halves
    dead=text.split('_unused_wide_array:\n',1)[1].split('__size_unused_wide_array',1)[0]
    assert '#$A1B2' not in dead and 'tcs' not in dead,dead
    indexed=text.split('_dead_indexed_array:\n',1)[1].split('__size_dead_indexed_array',1)[0]
    assert '#$A1B2' not in indexed and 'cg_' not in indexed,indexed
    extract=text.split('_extract_long:\n',1)[1].split('__size_extract_long',1)[0]
    assert '__arith_lhs' not in extract and 'shr64' not in extract,extract
    extract=text.split('_extract_byte:\n',1)[1].split('__size_extract_byte',1)[0]
    assert '__arith_lhs' not in extract and 'shr64' not in extract,extract
    induction=text.split('_bounded_wide_loop:\n',1)[1].split('__size_bounded_wide_loop',1)[0]
    assert '; bounded wide induction: low word only' in induction,induction
    controls=text.split('_wide_loop_controls:\n',1)[1].split('__size_wide_loop_controls',1)[0]
    assert '_wide_effect_a' not in controls and '; bounded wide induction: low word only' in controls,controls
    repeat=text.split('_wide_loop_repeat:\n',1)[1].split('__size_wide_loop_repeat',1)[0]
    assert 'bounded wide induction' not in repeat and repeat.count('sta a:.loword(_wide_loop_result)')==1,repeat
    equal=text.split('_wide_effect_equal:\n',1)[1].split('__size_wide_effect_equal',1)[0]
    assert '__scmp64' not in equal and 'jsr' not in equal and '_wide_effect_a' in equal,equal
    widen=text.split('_widen_pure:\n',1)[1].split('__size_widen_pure',1)[0]
    assert '_widen_one' not in widen,widen
    composed=text.split('_compose_literal_calls:\n',1)[1].split('__size_compose_literal_calls',1)[0]
    assert '_accept_word' not in composed and '_accept_wide' not in composed,composed
    signed_product=text.split('_wide_signed_long_product:\n',1)[1].split('__size_wide_signed_long_product',1)[0]
    assert '__smul32wide' in signed_product and '__mul64' not in signed_product,signed_product
    signed_loop=text.split('_signed_counted_wide:\n',1)[1].split('__size_signed_counted_wide',1)[0]
    assert '; signed count with unsigned back edge' in signed_loop,signed_loop
    push=text.split('_push_wide_args:\n',1)[1].split('__size_push_wide_args',1)[0]
    assert '__arith_lhs' not in push and '    pea $1234\n' in push,push
    copy=text.split('_copy_wide_index:\n',1)[1].split('__size_copy_wide_index',1)[0]
    assert '    lda a:$0006,x\n    sta a:' in copy and '__arith_lhs+2' not in copy,copy
    folded=text.split('_wide_literal_ops:\n',1)[1].split('__size_wide_literal_ops',1)[0]
    assert all(helper not in folded for helper in ('__mul64','__ushr64','__sshr64','__ucmp64')),folded
    magnitude=text.split('_wide_magnitude:\n',1)[1].split('__size_wide_magnitude',1)[0]
    assert 'sbc z:__arith_lhs' not in magnitude and 'sbc a:' in magnitude,magnitude
    assert magnitude.index('bpl ')<magnitude.index('sta z:__arith_lhs'),magnitude
    for function in ('wide_rotate_words','wide_rotate_signed','wide_rotate_opposite'):
        rotation=text.split(f'_{function}:\n',1)[1].split(f'__size_{function}',1)[0]
        assert '_shr64' not in rotation and '_shl64' not in rotation,rotation
    divisor=text.split('_div_power:\n',1)[1].split('__size_div_power',1)[0]
    assert '__ushr64' in divisor and '__uquot64' not in divisor,divisor
    assert all(f'__arith_lhs+{offset}' not in divisor for offset in (10,12,14)),divisor
    for function,count in [('full_word_long',2),('full_long_word',2),('full_words',1)]:
        product=text.split(f'_{function}:\n',1)[1].split(f'__size_{function}',1)[0]
        assert product.count('__mul16wide')==count and '__mul64' not in product,product
    for function in ('signed_compare','unsigned_compare','equal_compare','zero_relations','zero_effect','immediate_relations'):
        body=text.split(f'_{function}:\n',1)[1].split(f'__size_{function}',1)[0]
        assert 'cmp64' not in body, function
    for function in ('widened_complement','widened_difference','widened_bool','widened_signed_limit','widened_unsigned_limit'):
        body=text.split(f'_{function}:\n',1)[1].split(f'__size_{function}',1)[0]
        assert ('word zero test of widened arithmetic' in body)==(not function.endswith('_limit')),body
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',obj,asm])
    workspace=c.OUT/'workspace.s'
    workspace.write_text('.exportzp __arith_lhs,__arith_rhs\n.segment "DP_SCRATCH": zeropage\n'
                         '__arith_lhs: .res 4\n__arith_rhs: .res 28\n')
    c.run([c.CC65/'ca65.exe','-o',c.OUT/'workspace.o',workspace])
    _,rom,labels=c.compile_case('driver',DRIVER,extra_objects=[obj,c.OUT/'workspace.o',ROOT/'build/libc.a',ROOT/'build/integers.o'])
    def verify(rom,labels):
        lines=['local checks=0','local kernel_calls=0',
               f"emu.addMemoryCallback(function() kernel_calls=kernel_calls+1 end,emu.callbackType.exec,{labels['kernel']},{labels['kernel']})",
               'emu.addMemoryCallback(function()',' if checks~=0 then return end']
        for name,value in EXPECTED.items():
            address=labels[name]&0x1ffff
            for i in range(8):
                lines.append(f" require_value(emu.read({address+i},emu.memType.snesWorkRam,false)=={(value>>(8*i))&255},'{name} byte {i}')")
            lines.append(' checks=checks+1')
        for name,offset,value in [('cells',0,2),('cells',8,((A+B)^B)&MASK),
                                  ('cells',16,((A+B)^B)&MASK),('box',2,(A+B)&MASK)]:
            address=(labels[name]&0x1ffff)+offset
            for i in range(8):
                lines.append(f" require_value(emu.read({address+i},emu.memType.snesWorkRam,false)=={(value>>(8*i))&255},'{name}+{offset} byte {i}')")
        for i in range(8):
            lines.append(f" require_value(emu.read({0xffff+i},emu.memType.snesWorkRam,false)=={(B>>(8*i))&255},'far boundary byte {i}')")
        lines.append(f" require_value(checks=={len(EXPECTED)} and kernel_calls==1,'result and kernel call count')")
        lines.append(f"end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})")
        c.emulate(rom,labels,0,extra_checks='\n'.join(lines))
    verify(rom,labels)
    for stage in (3,4):
        raw=c.OUT/f'banked-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',c.OUT/'driver.c',src,'--stage',str(stage),'-o',raw],timeout=120)
        labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(
            r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        rom=raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        verify(rom,labels)
    print(f'PASS: {len(EXPECTED)} separate-unit 64-bit arithmetic, local and conversion results')


if __name__=='__main__':main()
