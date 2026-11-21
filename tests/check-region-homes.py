"""Region direct-page homes (Phase A v2): a function that keeps its Y frame
because it makes unresolved calls promotes hot frame words into free scratch
words around one loop whose body makes no unresolved call. Each case runs as an
MSVC host program and as SNES ROMs built with and without --no-region-homes;
main returns 0 only when every result matches. Each case names the function
and states whether that function must be promoted."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'region-homes-check'
spec = importlib.util.spec_from_file_location('checks', ROOT/'tests/check-strength.py')
checks = importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)
checks.OUT = OUT
support = checks.support
COMPILER = Path(os.environ.get('ZICC_COMPILER', ROOT/'build/zicc.exe'))
# hook calls itself, so it has no clobber summary and its callers keep their
# frames; only the loops between the calls can use the workspace
HOOK = 'long seen;int hook(int v){if(v>1000)return hook(v-1000)+1000;seen+=(long)v*6L/3L;return v;}\n'
MARK = '; region direct-page homes:'
CASES = {
 'private_lifetimes': (HOOK + '''volatile int pulse;
int work(int n,int seed){int r,i,a=seed,b=0,c=seed+3;hook(seed);for(r=0;r<3;r++){
 for(i=0;i<n;i++){a=i+c;b+=a;if(i==2)continue;c+=a;if(c>1000)break;}
 if(r==1)a+=c;b+=a;pulse=b;}hook(b);return a+b+c+i;}
int reference(int n,int seed){int r,i,a=seed,b=0,c=seed+3;for(r=0;r<3;r++){
 for(i=0;i<n;i++){a=i+c;b+=a;if(i==2)continue;c+=a;if(c>1000)break;}
 if(r==1)a+=c;b+=a;}return a+b+c+i;}
int main(void){int n;for(n=0;n<8;n++)if(work(n,11)!=reference(n,11))return 1;return 0;}''', 'work', True),
 'initialized': (HOOK + '''int data[16]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16};
int work(int n){int i,t=0,u=1;hook(n);for(i=0;i<n;i++){t+=data[i]*3;u^=t;}hook(t);return t+u+i;}
int main(void){return work(16)!=408+(1^3^9^18^30^45^63^84^108^135^165^198^234^273^315^360^408)+16||work(0)!=1||seen!=2L*(16+408);}''', 'work', True),
 'break_exit': (HOOK + '''int data[8]={3,1,4,1,5,9,2,6};
int find(int n,int key){int i,t=0,c=0;hook(n);for(i=0;i<n;i++){t+=data[i];c+=t;if(data[i]==key)break;}hook(c);return t*100+i*10+(c&7);}
int main(void){return find(8,5)!=1400+40+(38&7)||find(8,7)!=3100+80+(117&7);}''', 'find', True),
 'return_inside': (HOOK + '''int data[8]={3,1,4,1,5,9,2,6};
int first(int n,int lim){int i,t=0,c=0;hook(n);for(i=0;i<n;i++){t+=data[i];c^=t;if(t>lim)return t*16+c;}hook(t);return -t;}
int main(void){return first(8,10)!=14*16+(3^4^8^9^14)||first(8,99)!=-31;}''', 'first', True),
 'while_after': (HOOK + '''int fold(int n){int a=n,b=0,c=0;hook(a);while(a>0){b+=a;c+=b^a;a-=3;}hook(b);a+=b;c+=a;return c;}
int main(void){int a=10,b=0,c=0;while(a>0){b+=a;c+=b^a;a-=3;}a+=b;c+=a;return fold(10)!=c;}''', 'fold', True),
 # The entry test skips a zero-trip loop straight to its end label; the copy
 # out there must not store what the workspace still holds from the last run
 'zero_trip': (HOOK + '''long big(long a,long b){return a/b+a%b;}
int data[8]={7,7,7,7,7,7,7,7};
int skip(int n,int k){int j,t=k;hook(n);for(j=1;j<n;j+=2){if(j==3)continue;t+=data[j]+j;if(j==5)break;}hook(t);return t*8+j;}
int main(void){long q=big(123456789L,1234L);if(skip(7,0)!=(8+12)*8+5)return 1;if(skip(0,5)!=5*8+1)return 2;q+=big(-99999999L,77L);
 if(skip(1,3)!=3*8+1)return 3;return q!=123456789L/1234L+123456789L%1234L+(-99999999L/77L)+(-99999999L%77L);}''', 'skip', True),
 # An affine loop tests its entry before the body; with register loops off
 # that test jumps to the end label, so it must run inside the region
 'affine_zero_trip': (HOOK + '''int a[2][7];
int run(int m[][7],int row,int n){int j;hook(n);for(j=1;j<n;j+=2){if(j==3)continue;m[row][j]+=j;if(j==5)break;}return j;}
int main(void){if(run(a,1,7)!=5)return 1;if(run(a,1,0)!=1)return 2;if(a[1][1]!=1||a[1][3]!=0||a[1][5]!=5)return 3;return 0;}''',
  'run', True, ['--no-register-loops']),
 'call_in_loop': (HOOK + '''int calls(int n){int i,t=0;for(i=0;i<n;i++){t+=hook(i);t^=i;}return t;}
int main(void){int i,t=0;for(i=0;i<5;i++){t+=i;t^=i;}return calls(5)!=t;}''', 'calls', False),
 'address_taken': (HOOK + '''int *escaped;
void bump(int *p){escaped=p;*p+=2;}
int addr(int n){int i,t=0;hook(n);for(i=0;i<n;i++){bump(&t);t+=i;}escaped=0;return t;}
int main(void){return addr(4)!=8+6;}''', 'addr', False),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True); report = {}
    for name, (source, function, promoted, *flags) in CASES.items():
        flags = flags[0] if flags else []
        host = OUT/(name + '-host.c'); host.write_text(source, encoding='ascii'); exe = host.with_suffix('.exe')
        support.run([ROOT/'tools/msvc.cmd', '/nologo', '/std:c17', '/O2', '/Fo' + str(host.with_suffix('.obj')), '/Fe' + str(exe), host])
        assert subprocess.run([str(exe)], timeout=5).returncode == 0, name + ' host'
        on = checks.build(name + '_on', source, True, compiler=COMPILER, extra_flags=flags)
        off = checks.build(name + '_off', source, True, compiler=COMPILER, extra_flags=[*flags, '--no-region-homes'])
        assert MARK not in off['assembly'], name
        body = on['assembly'].split(f'\n_{function}:\n', 1)[1].split(f'\nreturn_{function} = *', 1)[0]
        got = MARK in body
        assert got == promoted, (name, promoted, got)
        report[name] = dict(on=on['master_clocks'], off=off['master_clocks'])
        print(f"PASS region homes {name}: {'promoted' if promoted else 'unchanged'}, "
              f"{off['master_clocks']} -> {on['master_clocks']} clocks", flush=True)
    (OUT/'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS region homes: MSVC references, enabled/disabled ROMs, promotion expectations')


if __name__ == '__main__':
    main()
