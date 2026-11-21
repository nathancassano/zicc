"""Stack-relative frames: Y-frame functions rewritten to N,s addressing.

The same fixtures are compiled with the conversion and with
--no-stack-frames, executed in Mesen (return value and stack balance) and
checked against MSVC. Converted functions must not save, set or otherwise
write Y, so the ABI's Y preservation holds without PHY/PLY.
"""
import os
import importlib.util
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'stack-frame-check'
SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT

SOURCE = r'''
int calls;
int factorial(int n){if(n<2)return 1;return n*factorial(n-1);}
int fibonacci(int n){int left,right;if(n<2)return n;left=fibonacci(n-1);right=fibonacci(n-2);return left+right;}
int mix3(int a,int b,int c){calls++;return a*3+b*5-c;}
int stack_args(int a,int b,int c,int d){int t=a*b;t+=mix3(c,d,a);return t-c+d;}
int forward(int a,int b,int c){return mix3(a,b,c)+mix3(c,b,a);}
int large(int a){int x=a+1,y=a*3,z=a-7,w;w=mix3(x,y,z);w+=mix3(z,y,x);return x+y+z+w;}
int branches(int a,int b){int t=a-b;if(t>0){t=mix3(t,a,b);}else{t=mix3(b,t,a)+1;}return t+a;}
unsigned char bytes(unsigned char a,int b){unsigned char c=(unsigned char)(a+3);int r=mix3(b,c,a);c=(unsigned char)(c+r);return c;}
long wide(long a,int b){long t=a+b;t+=mix3(b,b,b);return t*2L;}
int args_sum(int a,int b,int c,int d){int t=mix3(a,b,c);t=mix3(t,c,d)+t;return t+c+d;}
int nested(int n){int s=0;while(n>0){s+=mix3(n,s,1);n=n-1;}return s;}
int bounded_choice(unsigned n,int x,int y,int z){
    unsigned b=n&3U;
    int t=mix3(x,y,z);
    return (b>100 ? x : t+y)+z;
}
void fill_local(int *words, int value){
    int *end=words+256;
    while(end!=words){
        *--end=value; *--end=value; *--end=value; *--end=value;
    }
}
int addressed_array(int value){
    int words[256];
    fill_local(words,value);
    return words[0];
}
int main(void){
 if(addressed_array(6)!=6)return 12;
 if(factorial(6)!=720||fibonacci(10)!=55)return 1;
 calls=0;if(stack_args(3,4,5,6)!=12+(15+30-3)-5+6||calls!=1)return 2;
 if(forward(1,2,3)!=(3+10-3)+(9+10-1)||calls!=3)return 3;
 if(large(10)!=11+30+3+(33+150-3)+(9+150-11))return 4;
 if(branches(9,4)!=mix3(5,9,4)+9)return 5;
 if(branches(4,9)!=mix3(9,-5,4)+1+4)return 6;
 if(bytes(250,2)!=(unsigned char)(253+mix3(2,253,250)))return 7;
 if(wide(100000L,7)!=(100007L+mix3(7,7,7))*2L)return 8;
 if(nested(4)!=2696)return 9;
 if(args_sum(1,2,3,4)!=mix3(10,3,4)+10+3+4)return 10;
 if(bounded_choice(1024,1,2,3)!=15)return 11;
 return 0;}
'''
CONVERTED = ('factorial', 'fibonacci', 'large', 'branches', 'bytes', 'nested', 'args_sum', 'wide', 'bounded_choice')
Y_WRITES = re.compile(r'^    (?:phy|ply|tay|txy|ldy|iny|dey)\b', re.M)


def body(assembly, name):
    return assembly.split('_' + name + ':\n', 1)[1].split('__size_' + name, 1)[0]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    extra = [ROOT / 'build' / (n + '.o') for n in ('arithmetic', 'integers', 'ieee_engine')]
    results = {}
    # Without direct-page homes every fixture keeps a frame to convert
    for name, flags in (('default', []), ('converted', ['--no-dp-homes']),
                        ('framed', ['--no-dp-homes', '--no-stack-frames'])):
        cfile, rom, labels = support.compile_case(name, SOURCE, extra_objects=extra, flags=flags)
        results[name] = support.emulate(rom, labels, 0)
        if name == 'converted':
            exe = OUT / 'host.exe'
            support.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/O2',
                         '/Fo' + str(OUT / 'host.obj'), '/Fe' + str(exe), cfile])
            assert subprocess.run([str(exe)], timeout=10).returncode == 0
    converted = (OUT / 'converted.s').read_text()
    framed = (OUT / 'framed.s').read_text()
    for name in CONVERTED:
        part = body(converted, name)
        # No Y frame; a frame read may even become TXA, leaving no N,s operand
        assert not Y_WRITES.search(part) and ',y\n' not in part, (name, part)
        assert '    tay\n' in body(framed, name), name
    # Wide results can also release a stack frame while keeping X intact;
    # the low word is saved in a frame word and recovered by PLA
    assert '    pla\n' in body(converted, 'wide')
    print(f'PASS: {len(CONVERTED)} stack-relative frames without Y writes; framed/converted Mesen and MSVC agree')


if __name__ == '__main__':
    main()
