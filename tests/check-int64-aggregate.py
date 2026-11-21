"""Exercise wide values in functions using aggregate ABI and bit-fields."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'int64-aggregate-check'
c.OUT.mkdir(parents=True, exist_ok=True)
kernel = c.OUT/'kernel.c'
kernel.write_text(r'''
typedef struct Pair { int a; unsigned b:4; } Pair;
volatile unsigned long sink;
volatile unsigned address_calls;
volatile unsigned mark_calls;
volatile unsigned index_calls;
volatile int narrow_sink=7;
volatile unsigned narrow_visits;
volatile long signed_sink=-100L;
volatile float pointer_float;
volatile int indexed_words[4];
volatile int matrix[4][4];
volatile unsigned long long indexed_wide[4];
struct Node { unsigned long long value; int marker; unsigned flag:4; };
struct Wrap { unsigned long long value; };
volatile struct Node indexed_nodes[4];
volatile unsigned long *destination(void){address_calls++;return &sink;}
unsigned long long mark_wide(unsigned long long x){mark_calls++;return x;}
unsigned long long next_index(void){index_calls++;return 2ULL;}
unsigned long long wide_comma(unsigned long long x){return (mark_wide(x),x+1ULL);}
int check_wide(unsigned long long x){mark_calls++;return x!=0;}
int choose_wide(unsigned long long x){return x?17:23;}
int logical_wide(unsigned long long x){return x&&check_wide(x);}
int or_wide(unsigned long long x){return x||check_wide(x);}
int pointer_choice(unsigned long long x){
    volatile int *p=x?&narrow_sink:&indexed_words[0];
    volatile int * __far far=x?&narrow_sink:&indexed_words[0];
    *p=71;
    *far+=1;
    return *p;
}
int pointer_comma(unsigned long long x){
    volatile int *p=(mark_wide(x),&narrow_sink);
    volatile int * __far far=(x++,&narrow_sink);
    return p==&narrow_sink&&far==&narrow_sink&&x==1ULL;
}
unsigned long long narrow_comma(unsigned long long x){return (check_wide(x),x+1ULL);}
struct Wrap wrap_value(unsigned long long x){struct Wrap w;w.value=x;return w;}
unsigned long long returned_member(unsigned long long x){return wrap_value(x).value;}
int read_pointer(volatile int *p){return *p;}
volatile int *narrow_destination(void){narrow_visits++;return &narrow_sink;}
volatile int * __far far_destination(void){narrow_visits++;return &narrow_sink;}
unsigned long long combine(Pair p,unsigned long long n){
    p.b++;
    return n+(unsigned long long)p.a+(unsigned long long)p.b;
}
Pair create(unsigned long long n,int a){
    Pair p;
    p.a=a;
    p.b=(unsigned)n;
    return p;
}
unsigned long long fields(unsigned long long x){
    Pair p;
    p.a=7;
    p.b=3;
    p.b++;
    return x+(unsigned long long)p.a+(unsigned long long)p.b;
}
double combine_double(Pair p,double x){return x+(double)p.a;}
unsigned long narrow_store(unsigned long long x){
    *destination()=(unsigned long)x;
    return sink;
}
int narrow_compound(unsigned long long x){
    *narrow_destination()+=(int)x;
    return narrow_sink;
}
int narrow_compound_wide(unsigned long long x){
    *narrow_destination()+=x;
    *far_destination()+=2.75;
    return narrow_sink;
}
int bitfield_compound(unsigned long long x){
    Pair p;
    p.b=3;
    p.b+=x;
    return p.b;
}
int signed_wide_compound(unsigned long long count){
    struct Signed { signed int bits:4; } p;
    volatile long * __far target=&signed_sink;
    p.bits=-4;
    p.bits/=2LL;
    *target/=3LL;
    if(p.bits!=-2||signed_sink!=-33L)return 0;
    *target+=2.75;
    if(signed_sink!=-30L)return 0;
    p.bits=1;
    p.bits<<=count;
    return p.bits==4;
}
unsigned long long nested_narrow(unsigned long long x){
    Pair p;
    return (unsigned long long)(p.a=(int)x);
}
int pointer_roundtrip(void){
    volatile int *near=&narrow_sink;
    volatile int * __far far=near;
    volatile unsigned long long *wide=&indexed_wide[0];
    volatile float *single=&pointer_float;
    unsigned long long address=(unsigned long long)near;
    if((volatile int *)address!=near||read_pointer((volatile int *)address)!=15)return 0;
    *(volatile int *)address=22;
    address=(unsigned long long)far;
    if((volatile int * __far)address!=far)return 0;
    *(volatile int * __far)address=23;
    address=(unsigned long long)wide;
    *(volatile unsigned long long *)address=0x123456789abcdef0ULL;
    address=(unsigned long long)single;
    *(volatile float *)address=1.5F;
    return narrow_sink==23&&indexed_wide[0]==0x123456789abcdef0ULL&&pointer_float==1.5F;
}
unsigned long long indexed(unsigned long long n,unsigned long long x){
    volatile int * __far far_words=indexed_words;
    volatile int *middle=indexed_words+2;
    volatile int *following;
    volatile unsigned long long *selected;
    volatile unsigned long long *selected_node;
    long long negative=-1LL;
    indexed_words[n]=37;
    indexed_wide[n]=x;
    indexed_nodes[n].value=x+1ULL;
    indexed_nodes[n].marker=9;
    indexed_nodes[n].flag=3;
    indexed_nodes[n].flag+=2ULL;
    indexed_nodes[next_index()].flag+=1ULL;
    if(indexed_nodes[n].value!=x+1ULL)return 0;
    if(indexed_nodes[n].marker!=9||indexed_nodes[n].flag!=6||index_calls!=1)return 0;
    selected_node=&indexed_nodes[n].value;
    if(*selected_node!=x+1ULL)return 0;
    selected=&indexed_wide[n];
    if(*selected!=x)return 0;
    if(*(indexed_words+n)!=37||far_words[n]!=37)return 0;
    far_words[n]=38;
    if(indexed_words[n]!=38)return 0;
    middle[negative]=19;
    if(indexed_words[1ULL]!=19)return 0;
    middle=indexed_words+n;
    *(n+indexed_words)=39;
    if(*middle!=39)return 0;
    middle-=n;
    middle+=n;
    far_words+=n;
    if(*middle!=39||*far_words!=39)return 0;
    following=(indexed_words+n)+1;
    *following=99;
    matrix[n][1]=81;
    if(indexed_words[3]!=99||matrix[n][1]!=81)return 0;
    return indexed_wide[n]+(unsigned long long)read_pointer(indexed_words+n)+
           (unsigned long long)indexed_nodes[n].marker+(unsigned long long)indexed_nodes[n].flag;
}
''')
driver = c.OUT/'driver.c'
driver.write_text(r'''
typedef struct Pair { int a; unsigned b:4; } Pair;
unsigned long long combine(Pair,unsigned long long);
Pair create(unsigned long long,int);
unsigned long long fields(unsigned long long);
double combine_double(Pair,double);
unsigned long narrow_store(unsigned long long);
int narrow_compound(unsigned long long);
int narrow_compound_wide(unsigned long long);
int bitfield_compound(unsigned long long);
int signed_wide_compound(unsigned long long);
unsigned long long nested_narrow(unsigned long long);
int pointer_roundtrip(void);
unsigned long long mark_wide(unsigned long long);
unsigned long long wide_comma(unsigned long long);
unsigned long long narrow_comma(unsigned long long);
int choose_wide(unsigned long long);
int logical_wide(unsigned long long);
int or_wide(unsigned long long);
int pointer_choice(unsigned long long);
int pointer_comma(unsigned long long);
unsigned long long returned_member(unsigned long long);
unsigned long long indexed(unsigned long long,unsigned long long);
extern volatile unsigned address_calls,mark_calls,narrow_visits;
typedef unsigned long long (*Combine)(Pair,unsigned long long);
typedef Pair (*Create)(unsigned long long,int);
Combine volatile combine_pointer=combine;
Create volatile create_pointer=create;
volatile unsigned long long value=0x1234567800000000ULL;
volatile double dvalue=1.5;
int main(void){
    Pair p,q;
    int i;
    p.a=7;p.b=3;
    if(combine(p,value)!=0x123456780000000bULL)return 1;
    if(fields(value)!=0x123456780000000bULL)return 2;
    q=create(value+13ULL,23);
    if(q.a!=23||q.b!=13)return 3;
    if(combine_pointer(p,value)!=0x123456780000000bULL)return 4;
    q=create_pointer(value+9ULL,31);
    if(q.a!=31||q.b!=9)return 5;
    if(combine_double(p,dvalue)!=8.5)return 6;
    if(narrow_store(value+0x87654321ULL)!=0x87654321UL||address_calls!=1)return 7;
    (void)(mark_wide(value)+2ULL);
    if(mark_calls!=1)return 8;
    for(i=0;i<2;(void)(mark_wide(value)+1ULL))i++;
    if(mark_calls!=3)return 9;
    if(indexed(2ULL,value)!=value+54ULL)return 10;
    if(narrow_compound(3ULL)!=10||narrow_visits!=1)return 11;
    if(bitfield_compound(4ULL)!=7)return 12;
    if(wide_comma(value)!=value+1ULL||mark_calls!=4)return 13;
    if(narrow_comma(value)!=value+1ULL||mark_calls!=5)return 14;
    if(nested_narrow(23ULL)!=23ULL)return 15;
    if(narrow_compound_wide(3ULL)!=15||narrow_visits!=3)return 16;
    if(!signed_wide_compound(2ULL))return 17;
    if(!pointer_roundtrip())return 18;
    if(returned_member(value)!=value)return 19;
    if(choose_wide(value)!=17||choose_wide(0ULL)!=23)return 20;
    if(logical_wide(0ULL)||mark_calls!=5)return 21;
    if(!logical_wide(value)||mark_calls!=6)return 22;
    if(!or_wide(value)||mark_calls!=6)return 23;
    if(or_wide(0ULL)||mark_calls!=7)return 24;
    if(pointer_choice(value)!=72||pointer_choice(0ULL)!=72)return 25;
    if(!pointer_comma(0ULL)||mark_calls!=8)return 26;
    return 0;
}
''')
for stage in (1, 2, 3, 4):
    raw = c.OUT/f'aggregate-{stage}.raw'
    c.run([sys.executable, ROOT/'tools/build-rom.py', driver, kernel, '--stage', str(stage),
           '-o', raw, '--no-inline'], timeout=300)
    labels = {n.removeprefix('_'): int(a,16) for a,n in
              re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
    rom = raw.with_suffix('.sfc')
    c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
    c.emulate(rom, labels, 0, timeout_seconds=60)
solo = c.OUT/'inline-only.c'
solo.write_text(r'''
volatile unsigned long long increment=2ULL;
volatile unsigned result=65535U;
volatile unsigned *address=&result;
int main(void){*address+=increment;return result!=1U;}
''')
for stage in (1, 2, 3, 4):
    raw=c.OUT/f'inline-only-{stage}.raw'
    c.run([sys.executable,ROOT/'tools/build-rom.py',solo,'--stage',str(stage),'-o',raw],timeout=300)
    labels={n.removeprefix('_'):int(a,16) for a,n in
            re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
    assert '_mul64' not in labels and '_dadd' not in labels
    rom=raw.with_suffix('.sfc')
    c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
    c.emulate(rom,labels,0,timeout_seconds=60)
print('PASS: aggregate ABI and bit-fields with wide values, stages 1/2/3/4')
