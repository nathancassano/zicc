"""Execute string loops and scalar updates; check compact copy lowering."""
import os
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'string-check'
spec = importlib.util.spec_from_file_location('support', Path(__file__).with_name('check-compiler.py'))
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

CASES = {
    'strings': support.near_fixture((ROOT / 'samples/string_processing.c').read_text()),
    'updates': '''int g;int *gp;
int main(void){int a[4];int *p=a;int n=0;unsigned int u=65535;
signed char c=127;long wide=65535L;int old;
a[0]=10;a[1]=20;a[2]=30;a[3]=40;
if(*p++!=10||p!=a+1)return 1;
if(*++p!=30||p!=a+2)return 2;
if(*p--!=30||p!=a+1)return 3;
if(*--p!=10||p!=a)return 4;
old=n++;if(old!=0||n!=1)return 5;
if(++n!=2||n--!=2||--n!=0)return 6;
++u;if(u!=0)return 7;--u;if(u!=65535)return 8;
if(c++!=127||c!=-128)return 9;
if(++wide!=65536L||wide--!=65536L||wide!=65535L)return 10;
gp=a;if(*gp++!=10||gp!=a+1)return 11;
g=0;if(g++||g!=1)return 12;
p=a;*p++=a[3];if(a[0]!=40||p!=a+1)return 13;
return 0;}''',
    'truth': '''int echo(int x){return x;}int main(void){
int a[3];int *p=a;int n=0;int result=0;
a[0]=0;a[1]=256;a[2]=-1;
if(*p++)return 1;if(!*p++)return 2;if(!*p)return 3;
if(n++)return 4;if(!n--)return 5;if(n)return 6;
if(echo(0))return 7;if(!echo(256))return 8;
if((n=0))return 9;if(!(n=256))return 10;
if((result=1)?0:1)return 11;
return 0;}''',
    'copy_edges': '''int copy(char *d,const char *s){int n=0;
while(*s){*d++=*s++;++n;}*d=0;return n;}
int main(void){char a[8];int n;
a[0]=128;a[1]=255;a[2]=7;a[3]=0;a[4]=99;
n=copy(a,a);if(n!=3||a[0]!=128||a[1]!=255||a[2]!=7||a[3]!=0||a[4]!=99)return 1;
a[0]=1;a[1]=2;a[2]=3;a[3]=0;a[4]=99;
n=copy(a,a+1);if(n!=2||a[0]!=2||a[1]!=3||a[2]!=0||a[3]!=0||a[4]!=99)return 2;
if(copy(a,"")||a[0]!=0||a[1]!=3)return 3;
if(copy(a,"x")!=1||a[0]!=120||a[1]!=0||a[2]!=0)return 4;
if(copy(a,"xy")!=2||a[2]!=0||a[3]!=0)return 5;
return 0;}''',
    # Real ROM literals: kept out of near_fixture, which copies them to RAM
    'shared_literals': '''const char * __far pick(int n){if(n==0)return "suffix";if(n==1)return "fix";return "a suffix";}
int main(void){const char * __far a="a suffix";const char * __far b="suffix";const char * __far c=pick(2);
if(a!=c||b!=a+2||pick(0)!=b||pick(1)!=a+5)return 1;
if(a[0]!=97||b[5]!=120||pick(1)[3]!=0)return 2;
return 0;}''',
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    support.OUT = OUT
    report = {}
    for name, source in CASES.items():
        if name != 'shared_literals':
            source=support.near_fixture(source)
        _, rom, labels = support.compile_case(name, source, extra_objects=[
            ROOT / 'build/arithmetic.o', ROOT / 'build/integers.o', ROOT / 'build/ieee_engine.o'])
        report[name] = support.emulate(rom, labels, 0)
    assembly = (OUT / 'strings.s').read_text()
    copy = assembly.split('_copy_text:', 1)[1].split('__size_copy_text', 1)[0]
    assert '; native loop leaf' in copy and '    tsc\n' not in copy and '    tcs\n' not in copy, copy
    assert copy.count('    sep #$20\n') == 1 and copy.count('    rep #$20\n') == 1, copy
    assert re.search(r'lda a:\$0000,x\s+beq ', copy), copy
    region = copy.split('.a8\n', 1)[1].split('    rep #$20', 1)[0]
    assert region.count('lda a:$0000,x') == 1 and 'sta a:$0000,y' in region, copy
    assert '    inx\n' in region and '    iny\n' in region, copy
    assert '    pha\n' not in region and '__arith_' not in region, copy
    assert '    sbc 1,s\n' in copy, copy
    # Equal literals and literal suffixes share the longest literal's bytes
    shared = (OUT / 'shared_literals.s').read_text()
    owners = re.findall(r'^str_\w+:$', shared, re.M)
    aliases = re.findall(r'^str_\w+ = str_\w+\+\$([0-9A-F]{4})$', shared, re.M)
    assert len(owners) == 1 and sorted(aliases) == ['0000', '0002', '0002', '0005'], shared
    (OUT / 'results.json').write_text(json.dumps(report, indent=2))
    print('PASS: string loops, byte boundaries/overlap, pre/post updates, truth flags; Mesen')


if __name__ == '__main__':
    main()
