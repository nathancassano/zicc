"""Compare loops that keep values in registers, change register widths or advance an index."""
import os
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'register-loop-check'
spec = importlib.util.spec_from_file_location('checks', Path(__file__).with_name('check-strength.py'))
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

CASES = {
    'strings': checks.support.near_fixture((ROOT / 'samples/string_processing.c').read_text()),
    'scan': '''int scan(const signed char *p){int n=7,m=100;while(*p){++p;++n;--m;}
return n*10+m;}int main(void){signed char a[4];a[0]=-128;a[1]=-1;a[2]=1;a[3]=0;
if(scan(a)!=197||scan(a+3)!=170)return 1;return 0;}''',
    'boundaries': '''unsigned char a[300];unsigned char b[300];
int copy(unsigned char *d,const unsigned char *s){int n=0;
while(*s){*d++=*s++;++n;}*d=0;return n;}
int main(void){int i;for(i=0;i<299;++i)a[i]=255;a[299]=0;
if(copy(b,a)!=299||b[0]!=255||b[255]!=255||b[298]!=255||b[299]!=0)return 1;
return 0;}''',
    'overlap': '''unsigned char empty[1]={0};
int cp(unsigned char *d,const unsigned char *s){int n=0;while(*s){*d++=*s++;++n;}*d=0;return n;}
int main(void){unsigned char a[8];a[0]=1;a[1]=128;a[2]=255;a[3]=0;a[4]=99;
if(cp(a,a)!=3||a[0]!=1||a[1]!=128||a[2]!=255||a[3]!=0||a[4]!=99)return 1;
if(cp(a,a+1)!=2||a[0]!=128||a[1]!=255||a[2]!=0||a[3]!=0||a[4]!=99)return 2;
if(cp(a,empty)||a[0]!=0||a[1]!=255)return 3;return 0;}''',
    'counted': '''int cp(char *d,const char *s,unsigned int n){int done=9;
for(;n!=0;--n){*d++=*s++;++done;}return done;}
int main(void){char a[5];a[0]=99;a[1]=99;a[2]=99;a[3]=99;a[4]=99;
if(cp(a,"xyz",0)!=9||a[0]!=99)return 1;
if(cp(a,"xyz",3)!=12||a[0]!=120||a[1]!=121||a[2]!=122||a[3]!=99)return 2;
return 0;}''',
    'fill': '''int fill(unsigned char *p,int n){int total=20;
while(n){*p++=255;--n;--total;}return n+total;}
int main(void){unsigned char a[5];a[0]=7;a[1]=7;a[2]=7;a[3]=7;a[4]=7;
if(fill(a,0)!=20||a[0]!=7)return 1;
if(fill(a,4)!=16||a[0]!=255||a[3]!=255||a[4]!=7)return 2;return 0;}''',
    'reverse': '''int fill(char *p,int n){int k=0;while(n){*p--=42;--n;++k;}return k;}
int main(void){char a[5];a[0]=99;a[4]=99;
if(fill(a+3,3)!=3||a[0]!=99||a[1]!=42||a[2]!=42||a[3]!=42||a[4]!=99)return 1;
return 0;}''',
    'transform': '''void run(unsigned char *d,const unsigned char *s){
while(*s){*d++=((*s++^128)+3)&255;}*d=0;}
int main(void){unsigned char a[5],b[5];a[0]=1;a[1]=128;a[2]=255;a[3]=0;b[4]=99;
run(b,a);if(b[0]!=132||b[1]!=3||b[2]!=130||b[3]!=0||b[4]!=99)return 1;
return 0;}''',
    'in_place': '''int run(unsigned char *p){int n=0;
while(*p){*p=*p+1;++p;++n;}return n;}
int main(void){unsigned char a[4];a[0]=255;a[1]=127;a[2]=1;a[3]=0;
if(run(a)!=3||a[0]!=0||a[1]!=128||a[2]!=2||a[3]!=0)return 1;return 0;}''',
    'for_steps': '''int run(char *d,const char *s){int k=0;
for(;*s;++s){*d++=*s;k+=1;}*d=0;return k;}
int main(void){char a[4];if(run(a,"abc")!=3||a[0]!=97||a[2]!=99||a[3]!=0)return 1;
return 0;}''',
    'live_homes': '''int later(int x){return x+1;}
int main(void){char a[5];char *d=a;const char *s="abc";int n=4;unsigned short down=1;
while(*s){*d++=*s++;++n;--down;}*d=0;
if(d!=a+3||*s!=0||n!=7||down!=65534||later(n)!=8)return 1;
while(d!=a){--d;*d=42;}
if(a[0]!=42||a[2]!=42||a[3]!=0)return 2;return 0;}''',
    'nested_calls': '''int run(const char *p,int depth){int n=0;while(*p){++p;++n;}
if(depth)return n+run("xy",depth-1);return n;}
int main(void){return run("abcd",2)!=8;}''',
    'prefix_source': '''void run(char *d,const char *s,int n){while(n){*d++=*++s;--n;}}
int main(void){char a[4];a[3]=99;run(a,"abcd",3);
return a[0]!=98||a[1]!=99||a[2]!=100||a[3]!=99;}''',
    'argument_moves': '''int first(const char *s,char *d){int n=0;while(*s){*d++=*s++;++n;}*d=0;return n;}
int stacked(int unused,int unused2,char *d,const char *s){int n=2;while(*s){*d++=*s++;++n;}*d=0;return n;}
int mixed(const char *s,int n,char *d){int done=7;while(n){*d++=*s++;--n;++done;}return done;}
int main(void){char a[5];a[4]=99;
if(first("abc",a)!=3||a[0]!=97||a[2]!=99||a[3]!=0||a[4]!=99)return 1;
if(stacked(11,22,a,"xy")!=4||a[0]!=120||a[1]!=121||a[2]!=0)return 2;
if(mixed("abc",3,a)!=10||a[0]!=97||a[2]!=99||a[3]!=0)return 3;return 0;}''',
    'induction_results': '''int triple(const char *p){int n=7;while(*p){++p;n+=1;++n;++n;}return n;}
int subtract(const char *p){int n=100;while(*p){++p;--n;--n;}return n;}
int unchanged(const char *p){int n=42;while(*p){++p;++n;--n;}return n;}
int wrapped(const char *p){unsigned short n=65534;while(*p){++p;++n;}return n;}
int main(void){if(triple("abcd")!=19||subtract("abc")!=94||unchanged("abcd")!=42||wrapped("abc")!=1)return 1;
return 0;}''',
    'anchor_y': '''int run(char *d,char *s){int n=9;while(*s){*d++=*s;*s=0;++n;}return n;}
int main(void){char a[2],b[2];a[0]=42;a[1]=0;b[1]=99;
if(run(b,a)!=10||a[0]!=0||b[0]!=42||b[1]!=99)return 1;return 0;}''',
    'pointer_result': '''char *fill(char *p,int n){while(n){*p++=42;--n;}return p;}
int main(void){char a[5];a[3]=99;a[4]=99;
if(fill(a,3)!=a+3||a[0]!=42||a[2]!=42||a[3]!=99||a[4]!=99)return 1;
if(fill(a,0)!=a)return 2;return 0;}''',
    'cast_result': '''int run(char *d,const char *s){while(*s){*d++=*s++;}return (unsigned char)256;}
int scan(const char *s){int n=256;while(*s){++s;++n;}return (unsigned char)n;}
int main(void){char a[4];a[3]=99;if(run(a,"abc")!=0||a[0]!=97||a[2]!=99||a[3]!=99)return 1;
return scan("abc")!=3;}''',
}

FALLBACKS = {
    'global_short_trips': '''#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
int counter,total;
unsigned char wrapping;
signed char signed_count;
volatile unsigned char irq_count,irq_result;
NEVER void wrap_up(int x){for(;wrapping;wrapping++)total=x==3;}
NEVER void wrap_down(int x){for(;wrapping;wrapping-=1)total=x;}
NEVER void signed_down(int x){for(;signed_count;--signed_count)total=x;}
NEVER void watch_count(int x){for(;irq_count;--irq_count)total=x;}
NEVER void watch_result(int x){for(;wrapping;--wrapping)irq_result=x;}
NEVER void one_trip(int input){for(counter=0;counter<1;counter++)total=input+counter;}
NEVER void descending(void){for(counter=3;0<counter;--counter)total=total*2+counter;}
NEVER void indirect(int *p){for(counter=0;counter<2;++counter)*p+=2;}
NEVER void update(void){counter+=2;}
NEVER void calls(void){for(counter=0;counter<2;++counter)update();}
NEVER void early_break(void){for(counter=0;counter<2;++counter){if(total)break;++total;}}
int main(void){one_trip(17);if(total!=17||counter!=1)return 1;
 total=0;descending();if(total!=17||counter)return 2;
 indirect(&counter);if(counter!=3)return 3;
 calls();if(counter!=3)return 4;
 early_break();if(counter||total!=17)return 5;
 wrap_up(3);if(total!=17)return 6;
 wrapping=254;wrap_up(3);if(wrapping||total!=1)return 7;
 wrapping=4;wrap_down(23);if(wrapping||total!=23)return 8;
 signed_count=4;signed_down(9);if(signed_count||total!=9)return 9;
 irq_count=4;watch_count(11);if(irq_count||total!=11)return 10;
 wrapping=4;watch_result(13);if(wrapping||irq_result!=13)return 11;
 return 0;}''',
    'escaped': '''char **observed;
void observe(char **p){observed=p;}int run(char *p){int n=0;
observe(&p);while(*p){++p;++n;}observed=0;return n;}
int main(void){return run("abc")!=3;}''',
    'observed_counter': '''int main(void){char a[4];char *p=a;int n=0;
a[0]=1;a[1]=1;a[2]=1;a[3]=0;while(*p){*p++=n;++n;}
return n!=3||a[0]!=0||a[1]!=1||a[2]!=2;}''',
    'calls': '''int bump(int x){return x+1;}int main(void){const char *p="abc";int n=0;
while(*p){++p;n=bump(n);}return n!=3;}''',
    'breaks': '''int main(void){const char *p="abc";int n=0;
while(*p){if(n==2)break;++p;++n;}return n!=2;}''',
    'three_pointers': '''int main(void){char a[4],b[4];char *p=a,*q=b;const char *s="abc";
while(*s){*p++=*s;*q++=*s++;}return a[0]!=97||a[2]!=99||b[0]!=97||b[2]!=99;}''',
    'globals': '''const char *p;int main(void){int n=0;p="abc";while(*p){++p;++n;}return n!=3;}''',
    'word_loop': '''int main(void){int a[4],n=3;int *p=a;a[3]=99;
while(n){*p++=42;--n;}return a[0]!=42||a[2]!=42||a[3]!=99;}''',
    'cast_truncation': '''int main(void){unsigned int n=256;char a[2];char *p=a;a[0]=7;
while((unsigned char)n){*p++=9;--n;}return n!=256||a[0]!=7;}''',
    'counted_pointer_guard': '''#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
volatile int mismatches;
NEVER void mismatch(void){++mismatches;}
NEVER int compare(const unsigned char *p,int count,int expected){
 const unsigned char *start=p;int i;
 for(i=0;i<count;++p,++i)if(expected!=*p)mismatch();
 return 8*i+(int)(p-start);}
NEVER int scan(const signed char *p,int count){
 const signed char *start=p;int i;
 for(i=0;i<count;++i,++p)if(*p!=-7)mismatch();
 return 8*i+(int)(p-start);}
int main(void){unsigned char a[]={255,0,255};signed char b[]={-7,2,-7,3};
 if(compare(a,3,255)!=27||mismatches!=1)return 1;
 if(compare(a,3,511)!=27||mismatches!=4)return 2;
 if(scan(b,4)!=36||mismatches!=6)return 3;
 if(compare(a,0,255)||scan(b,-1)||mismatches!=6)return 4;
 return 0;}''',
    'counted_indexed_guard': '''#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
volatile int mismatches;
signed char signed_bytes[16]={0,-7,-7,9,8,-7,-7,-7,-7,-7,-7,-7,-7,-7,-7,-7};
unsigned char bytes[16]={0,255,255,0,255,255,255,255,255,255,255,255,255,255,255,255};
NEVER void mismatch(void){++mismatches;signed_bytes[4]=-7;}
NEVER int signed_scan(void){
 int i;
 for(i=1;i<=14;++i)if(-7!=signed_bytes[i])mismatch();
 return i;
}
NEVER unsigned int offset_scan(void){
 unsigned int i;
 for(i=0;i<12;i+=1)if(bytes[i+1]!=255)mismatch();
 return i;
}
NEVER void outside_byte(void){
 int i;
 for(i=1;i<15;++i)if(bytes[i]!=511)mismatch();
}
int main(void){
 if(signed_scan()!=15||mismatches!=1||signed_bytes[4]!=-7)return 1;
 if(offset_scan()!=12||mismatches!=2)return 2;
 outside_byte();
 if(mismatches!=16)return 3;
 return 0;}''',
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks.OUT = OUT
    checks.support.OUT = OUT
    results = {}
    for name, source in {**CASES, **FALLBACKS}.items():
        source=checks.support.near_fixture(source)
        cfile = OUT / (name + '-host.c')
        cfile.write_text(source)
        exe = cfile.with_suffix('.exe')
        checks.support.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/O2',
                            '/Fo' + str(cfile.with_suffix('.obj')), '/Fe' + str(exe), cfile])
        assert subprocess.run([str(exe)], timeout=5).returncode == 0, name
        pair = {mode: checks.build(name + '_' + mode, source, True, register_loops=(mode == 'on'))
                for mode in ('off', 'on')}
        assert '; register loop:' not in pair['off']['assembly'], name
        assert ('; register loop:' in pair['on']['assembly']) == (name in CASES), name
        if name == 'strings':
            copy = pair['on']['assembly'].split('_copy_text:', 1)[1].split('__size_copy_text', 1)[0]
            body = copy.split('.a8\n', 1)[1].split('    rep #$20', 1)[0]
            assert len(re.findall(r'lda a:\$0000,x', body)) == 1, body
            assert not any(x in body for x in ('__arith_', ',s', 'pha', ',y\n    inc a')), body
            assert pair['on']['master_clocks'] < pair['off']['master_clocks'], pair
        if name == 'counted_pointer_guard':
            assert pair['on']['assembly'].count('; loop lowering: counted pointer guard') == 2
            assert '; loop lowering: counted pointer guard' not in pair['off']['assembly']
        if name == 'counted_indexed_guard':
            marker = '; loop lowering: counted indexed byte guard'
            assert pair['on']['assembly'].count(marker) == 2, pair['on']['assembly']
            assert marker not in pair['off']['assembly']
        if name == 'global_short_trips':
            assembly = pair['on']['assembly']
            for function in ('one_trip', 'descending', 'wrap_up', 'wrap_down'):
                body = assembly.split('_' + function + ':', 1)[1].split('__size_' + function, 1)[0]
                assert '; loop lowering:' not in body, body
            for function in ('signed_down','watch_count','watch_result'):
                body = assembly.split('_' + function + ':', 1)[1].split('__size_' + function, 1)[0]
                assert '; loop lowering:' in body, body
        results[name] = {mode: {field: data[field] for field in ('master_clocks', 'code_bytes')}
                         for mode, data in pair.items()}
        print('PASS', name, results[name], flush=True)
    (OUT / 'results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
