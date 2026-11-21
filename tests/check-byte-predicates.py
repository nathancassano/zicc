"""Check that byte conditions stop evaluating at the right time and keep the right values and flags."""
import os
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'byte-predicate-check'
spec = importlib.util.spec_from_file_location('checks', Path(__file__).with_name('check-strength.py'))
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

EQ = '''int same(const unsigned char *a,const unsigned char *b){
while(*a&&*a==*b){++a;++b;}return (unsigned char)*a==(unsigned char)*b;}
'''
CASES = {
    'strings': (checks.support.near_fixture((ROOT / 'samples/string_processing.c').read_text()), True, True),
    'equal_edges': (EQ + '''int main(void){unsigned char a[5],b[5];int i,j;
a[0]=0;a[1]=128;a[2]=255;a[3]=7;a[4]=0;
for(i=0;i<5;++i)b[i]=a[i];if(!same(a,a)||!same(a,b)||!same(a+1,b+1))return 1;
for(i=1;i<4;++i){b[i]=1;if(same(a+1,b+1)||same(b+1,a+1))return 2;b[i]=a[i];}
b[0]=1;if(same(a,b)||same(b,a))return 3;b[0]=0;
for(i=0;i<4;++i){for(j=0;j<5;++j)b[j]=a[j];b[i]=0;
if(i>0&&i<4&&same(a+1,b+1))return 4;}return 0;}''', True, True),
    'pages': (EQ + '''unsigned char a[302];unsigned char b[302];int main(void){int i;
for(i=0;i<301;++i){a[i]=255;b[i]=255;}a[301]=0;b[301]=0;
if(!same(a,b))return 1;b[256]=128;if(same(a,b))return 2;
b[256]=255;b[300]=0;if(same(a,b))return 3;return 0;}''', True, True),
    'comparison_first': ('''int same(const char *a,const char *b){
while(*a==*b&&*a){++a;++b;}return *a==*b;}
int main(void){if(!same("abc","abc")||!same("","")||same("abc","abd")||same("","a"))return 1;
return 0;}''', True, True),
    'three_tests': ('''int same(const char *a,const char *b){
while(*a&&*b&&*a==*b){++a;++b;}return *a==*b;}
int main(void){if(!same("abc","abc")||same("abc","")||same("","abc")||same("abc","abd"))return 1;
return 0;}''', True, True),
    'short_circuit': ('''int ended(const char *a,const char *b){
while(*a&&*b&&*a==*b){++a;++b;}return !*a;}
int main(void){if(!ended("",(const char *)0)||ended("abc","")||!ended("abc","abc")||ended("abc","abd"))return 1;
return 0;}''', True, True),
    'not_equal_result': ('''int different(const char *a,const char *b){
while(*a&&*a==*b){++a;++b;}return !((unsigned char)*a==(unsigned char)*b);}
int main(void){if(different("abc","abc")||!different("abc","abd")||different("","")||!different("","a"))return 1;
return 0;}''', True, True),
    'direct_compare': ('''int run(const char *a,const char *b){while(*a==*b){++a;++b;}return *a!=*b;}
int until_equal(const char *a,const char *b){while(*a!=*b){++a;++b;}return *a==*b;}
int main(void){char a[3],b[3];a[0]=1;a[1]=2;a[2]=3;b[0]=1;b[1]=2;b[2]=4;
if(!run(a,b))return 1;b[0]=4;b[1]=5;b[2]=3;if(!until_equal(a,b))return 2;return 0;}''', True, True),
    'signed_normalized': ('''int same(const signed char *a,const unsigned char *b){
while(*a&&(unsigned char)*a==*b){++a;++b;}return (unsigned char)*a==*b;}
int main(void){signed char a[4];unsigned char b[4];a[0]=-128;a[1]=-1;a[2]=1;a[3]=0;
b[0]=128;b[1]=255;b[2]=1;b[3]=0;if(!same(a,b))return 1;
b[1]=128;if(same(a,b))return 2;return 0;}''', True, True),
    'reverse_steps': ('''int run(const char *a,const char *b){while(*a&&*a==*b){--a;--b;}return *a==*b;}
int main(void){char a[4],b[4];a[0]=0;a[1]=1;a[2]=2;a[3]=3;b[0]=0;b[1]=1;b[2]=2;b[3]=3;
if(!run(a+3,b+3))return 1;b[2]=9;return run(a+3,b+3)!=0;}''', True, True),
    'same_pointer': ('''int ended(const char *a){while(*a){++a;}return !*a;}
int nonzero(const char *a){while(*a){++a;}return !!*a;}
int main(void){return !ended("abc")||!ended("")||nonzero("abc")||nonzero("");}''', True, True),
    'stack_arguments': ('''int run(int unused,const char *a,const char *b){while(*a&&*a==*b){++a;++b;}return *a==*b;}
int more(int unused,int unused2,const char *a,const char *b){while(*a&&*a==*b){++a;++b;}return *a==*b;}
int swapped(const char *b,const char *a){while(*a&&*a==*b){++a;++b;}return *a==*b;}
int main(void){return !run(123,"abc","abc")||run(456,"abc","abd")||!more(11,22,"abc","abc")||more(33,44,"abc","abd")||!swapped("abc","abc");}''', True, True),
    'dead_counter': ('''int run(const char *a,const char *b){int n=7;
while(*a&&*a==*b){++a;++b;++n;}return *a==*b;}
int main(void){return !run("abc","abc")||run("abc","abd");}''', True, True),
    'terminal_store': ('''int run(unsigned char *p,const unsigned char *q){int n=0;
while(*p&&*p==*q){++p;++q;++n;}*p=0;return n;}
int main(void){unsigned char a[4];a[0]=1;a[1]=2;a[2]=3;a[3]=0;
if(run(a,(const unsigned char *)"xx")!=0||a[0]!=0||a[1]!=2)return 1;return 0;}''', False, True),
    'raw_byte_result': ('''int run(const unsigned char *a,const unsigned char *b){while(*a&&*b){++a;++b;}return *a;}
int main(void){unsigned char a[2],b[2];a[0]=128;a[1]=0;b[0]=0;b[1]=0;return run(a,b)!=128;}''', False, True),
    'live_homes': ('''int run(const char *a,const char *b){const char *start=a;
while(*a&&*a==*b){++a;++b;}return (*a==*b)&&(a-start==3);}
int main(void){return !run("abc","abc")||run("abc","abd");}''', False, True),
    'signed_mixed': ('''int run(const signed char *a,const unsigned char *b){while(*a&&*a==*b){++a;++b;}return *a==*b;}
int main(void){signed char a[2];unsigned char b[2];a[0]=-1;a[1]=0;b[0]=255;b[1]=0;return run(a,b)!=0;}''', False, False),
    'condition_calls': ('''int called;int match(const char *a,const char *b){++called;return *a==*b;}
int run(const char *a,const char *b){while(*a&&match(a,b)){++a;++b;}return *a==*b;}
int main(void){if(!run("","")||called)return 1;if(!run("abc","abc")||called!=3)return 2;return 0;}''', False, False),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks.OUT = OUT
    checks.support.OUT = OUT
    results = {}
    for name, (source, native, region) in CASES.items():
        source=checks.support.near_fixture(source)
        cfile = OUT / (name + '-host.c')
        cfile.write_text(source)
        exe = cfile.with_suffix('.exe')
        checks.support.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/O2',
                            '/Fo' + str(cfile.with_suffix('.obj')), '/Fe' + str(exe), cfile])
        assert subprocess.run([str(exe)], timeout=5).returncode == 0, name
        pair = {mode: checks.build(name + '_' + mode, source, True, register_loops=mode == 'on')
                for mode in ('off', 'on')}
        assert '; register loop:' not in pair['off']['assembly'], name
        assert ('; native predicate loop leaf' in pair['on']['assembly']) == native, name
        assert ('; register loop:' in pair['on']['assembly']) == region, name
        for data in pair.values():
            assert '    tcs\n    tsc\n' not in data['assembly'], name
        if name == 'strings':
            equal = pair['on']['assembly'].split('_text_equal:', 1)[1].split('__size_text_equal', 1)[0]
            body = equal.split('.a8\n', 1)[1].split('    rep #$20', 1)[0]
            assert body.count('    lda a:$0000,x\n') == 1 and body.count('    cmp a:$0000,y\n') == 2, body
            assert not re.search(r'\b(?:pha|pla|sta|sep|rep)\b|,s|__arith_', body), body
            assert '    tsc\n' not in equal and '    tcs\n' not in equal, equal
            assert re.search(r'rep #\$20\n.a16\n    bne ', equal), equal
            assert pair['on']['master_clocks'] < pair['off']['master_clocks'], pair
        results[name] = {mode: {field: data[field] for field in ('master_clocks', 'code_bytes')}
                         for mode, data in pair.items()}
        print('PASS', name, results[name], flush=True)
    (OUT / 'results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
