"""Direct-page homes: enabled/disabled differential runs against MSVC references.

Every case runs as an MSVC host program and as a SNES ROM built with and without
--no-dp-homes; main returns 0 only when every result matches. Each case also
states which functions must become frameless, keep a partial frame, or stay
unchanged, and the helper clobber table must match runtime/integers/*.s."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'dp-homes-check'
spec = importlib.util.spec_from_file_location('checks', ROOT/'tests/check-strength.py')
checks = importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)
checks.OUT = OUT
support = checks.support
COMPILER = Path(os.environ.get('ZICC_COMPILER', ROOT/'build/zicc.exe'))

# name: (source, {function: 'frameless' | 'partial' | 'unchanged'})
CASES = {
 'helpers': ('''
unsigned int ops(unsigned int a,unsigned int b){unsigned int q=a/b,r=a%b,m=a*b;return q+r*3+m;}
int sops(int a,int b){int q=a/b,r=a%b;return q*7-r;}
long lops(long a,long b){long m=a*b,q=a/b,s=a<<3;return m+q-s;}
unsigned long shifts(unsigned long v,int n){unsigned long l=v<<n,r=v>>n;return l^r;}
int main(void){
 if(ops(1000u,7u)!=142u+6u*3u+7000u)return 1;
 if(sops(-1000,7)!=-142*7+6)return 2;
 if(lops(100000L,-3L)!=-300000L-33333L-800000L)return 3;
 if(shifts(0x12345678UL,5)!=((0x12345678UL<<5)^(0x12345678UL>>5)))return 4;
 return 0;}''', {'ops': 'frameless', 'sops': 'frameless', 'lops': 'partial', 'shifts': 'partial'}),
 'loops': ('''
int values[12]={9,-3,7,7,0,-12,5,31,-8,2,2,1};
void sort(int *v,int count){int i,j,x;for(i=1;i<count;i++){x=v[i];j=i;while(j>0&&v[j-1]>x){v[j]=v[j-1];j--;}v[j]=x;}}
long grid(int rows,int cols){int r,c;long t=0;for(r=0;r<rows;r++)for(c=0;c<cols;c++)t+=(long)(r*cols+c)*(r-c);return t;}
int main(void){int i;long g;sort(values,12);
 for(i=1;i<12;i++)if(values[i-1]>values[i])return 1;
 if(values[0]!=-12||values[11]!=31)return 2;
 g=grid(9,11);{long h=0;int r,c;for(r=0;r<9;r++)for(c=0;c<11;c++)h+=(long)(r*11+c)*(r-c);if(g!=h)return 3;}
 return 0;}''', {'sort': 'frameless', 'grid': 'frameless'}),
 'divmod_cache': ('''
unsigned int digits(unsigned int v){unsigned int n=0,s=0;while(v){s+=v%10u;v=v/10u;n++;}return s*16u+n;}
int main(void){return digits(60001u)!=7u*16u+5u||digits(0u)!=0u;}''', {'digits': 'frameless'}),
 'wide_and_bytes': ('''
unsigned char bytes[6]={1,200,3,250,5,255};
unsigned long mix(unsigned char *p,int n){unsigned long t=0;unsigned char hi=0;int i;for(i=0;i<n;i++){if(p[i]>hi)hi=p[i];t=t*3UL+p[i];}return t+((unsigned long)hi<<16);}
char lower(char c){char d=c;if(d>='A'&&d<='Z')d=(char)(d+32);return d;}
int main(void){unsigned long t=0;int i;for(i=0;i<6;i++)t=t*3UL+bytes[i];
 if(mix(bytes,6)!=t+(255UL<<16))return 1;if(lower('Q')!='q'||lower('7')!='7')return 2;return 0;}''',
  {'mix': 'frameless', 'lower': 'frameless'}),
 'far_pointer': ('''
const int table[5]={3,1,4,1,5};
int sum_far(const int * __far p,int n){int i,t=0;for(i=0;i<n;i++)t+=p[i]*(i+1);return t;}
int main(void){return sum_far(table,5)!=3+2+12+4+25;}''', {}),
 'far_general': ('''
const int table[6]={3,1,4,1,5,9};
long far_mix(int n,int k){const int * __far p=(const int * __far)table;long t=0;int i;
 for(i=0;i<n;i++){t+=(long)p[i]*k;t-=p[i]/(i+1);}return t;}
int main(void){long t=0;int i;for(i=0;i<6;i++){t+=(long)table[i]*-7;t-=table[i]/(i+1);}return far_mix(6,-7)!=t;}''',
  {'far_mix': 'frameless'}),
 'pressure': ('''
long spill(int a,int b){int c=a+b,d=a-b,e=a*b,f=a^b,g=a|b,h=a&b,i=c*d,j=e+f,k=g-h,l=i^j,m=k+c,n=l-d;
 long p=(long)a*b,q=(long)c*d;return p+q+c+d+e+f+g+h+i+j+k+l+m+n;}
int main(void){int a=37,b=-11;int c=a+b,d=a-b,e=a*b,f=a^b,g=a|b,h=a&b,i=c*d,j=e+f,k=g-h,l=i^j,m=k+c,n=l-d;
 long p=(long)a*b,q=(long)c*d;return spill(37,-11)!=p+q+c+d+e+f+g+h+i+j+k+l+m+n;}''', {'spill': 'partial'}),
 'fallbacks': ('''
volatile int sink;
int vol(int a){volatile int v=a;v=v+1;return v;}
int addr(int a){int x=a;int *p=&x;*p=*p+5;return x;}
void bump_address(int *p){*p+=5;}
int escaped_addr(int a){int x=a;bump_address(&x);return x;}
// arr keeps its frame (v's address); its 4-trip loop is too short for region homes
int arr(int a){int v[4];int i;for(i=0;i<4;i++)v[i]=a+i;return v[a&3];}
struct pair{int a,b;};
int agg(int a){struct pair p,q;p.a=a;p.b=a*2;q=p;return q.a+q.b;}
int leaf(int a){int t=a*3;return t+1;}
int caller(int x,int y){int t=x*y;return t+leaf(x)*leaf(y)+(x/y)*leaf(t);}
int main(void){if(vol(4)!=5||addr(1)!=6||escaped_addr(1)!=6||arr(6)!=8||agg(5)!=15)return 1;
 return caller(9,4)!=36+28*13+2*109;}''',
  {'vol': 'unchanged', 'addr': 'frameless', 'escaped_addr': 'unchanged', 'arr': 'unchanged', 'agg': 'unchanged', 'caller': 'frameless',
   'leaf': 'unchanged'}),
 'recursion': ('''
int fact(int n){int r;if(n<2)return 1;r=n*fact(n-1);return r;}
int tri(int n){int t=0,i;for(i=1;i<=n;i++)t+=i;return t;}
int main(void){return fact(7)!=5040||tri(fact(4))!=300;}''', {'fact': 'unchanged', 'tri': 'frameless'}),
}


def body(assembly, name):
    m = re.search(r'^_' + name + r':\n(.*?)^__size_' + name + ' = ', assembly, re.M | re.S)
    assert m, name
    # Source-location comments name the per-mode C file; drop them
    return re.sub(r'^; .*\.c:\d+:\d+\n', '', m[1], flags=re.M)


def kind(enabled, disabled):
    if enabled == disabled: return 'unchanged'
    framed = lambda text: bool(re.search(r'^\s+tsc$|^\s+phy\n\s+(pha|phx)$', text, re.M)) or bool(re.search(r'a:\$[0-9A-F]{4},y', text))
    assert framed(disabled), 'promoted function had no frame'
    return 'partial' if framed(enabled) else 'frameless'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',action='append',choices=CASES);args=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    table = subprocess.run([sys.executable, ROOT/'tools/helper-clobbers.py', '--check'], capture_output=True, text=True)
    assert table.returncode == 0, table.stdout + table.stderr
    print('PASS', table.stdout.strip(), flush=True)
    report = {}
    for name, (source, expected) in CASES.items():
        if args.case and name not in args.case:continue
        host = OUT/(name + '-host.c'); host.write_text(source.replace(' __far', ''), encoding='ascii'); exe = host.with_suffix('.exe')
        support.run([ROOT/'tools/msvc.cmd', '/nologo', '/std:c17', '/O2', '/Fo' + str(host.with_suffix('.obj')), '/Fe' + str(exe), host])
        assert subprocess.run([str(exe)], timeout=5).returncode == 0, name + ' host'
        # Y frames keep the framed/frameless classification observable;
        # tests/check-stack-frames.py covers the stack-relative rewrite; line passes
        # (Y promotion) would read as frames
        on = checks.build(name + '_homes', source, True, compiler=COMPILER, extra_flags=('--no-stack-frames','--no-line-passes','--no-inline'))
        off = checks.build(name + '_frames', source, True, dp_homes=False, compiler=COMPILER, extra_flags=('--no-stack-frames','--no-line-passes','--no-inline'))
        assert '__dp_home_' not in on['assembly'], name
        for function, want in expected.items():
            got = kind(body(on['assembly'].replace(name + '_homes_on', 'UNIT'), function),
                       body(off['assembly'].replace(name + '_frames_on', 'UNIT'), function))
            print(f'  {name}.{function}: {got}', flush=True)
            assert got == want, (name, function, want, got)
            if name=='fallbacks' and function=='leaf':
                assert '; native word expression leaf' in body(on['assembly'],function)
                assert '; native word expression leaf' in body(off['assembly'],function)
        report[name] = dict(enabled={k: on[k] for k in ('master_clocks', 'code_bytes')},
                            disabled={k: off[k] for k in ('master_clocks', 'code_bytes')})
        print(f"PASS dp homes {name}: {off['master_clocks']} -> {on['master_clocks']} clocks, "
              f"{off['code_bytes']} -> {on['code_bytes']} bytes", flush=True)
    paths = [ROOT/'src/codegen/dp_homes.inc', ROOT/'src/codegen/codegen.inc', COMPILER, *sorted((ROOT/'runtime/integers').glob('*.s'))]
    report['inputs'] = {str(p.resolve().relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (OUT/'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS DP homes: MSVC references, enabled/disabled ROMs, promotion expectations, helper clobber table')


if __name__ == '__main__':
    main()
