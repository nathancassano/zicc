"""Index elimination (linear-function test replacement): each case runs as an
MSVC host program and as SNES ROMs built with and without
--no-index-elimination; main returns 0 only when every result matches. Each
case also states whether its index must be eliminated or kept."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'index-elimination-check'
spec = importlib.util.spec_from_file_location('checks', ROOT/'tests/check-strength.py')
checks = importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)
checks.OUT = OUT
support = checks.support
COMPILER = Path(os.environ.get('ZICC_COMPILER', ROOT/'build/zicc.exe'))
SORT = 'void sort(int *v,int n){int i,j,x;for(i=1;i<n;i++){x=v[i];j=i;while(j>0&&v[j-1]>x){v[j]=v[j-1];--j;}v[j]=x;}}\n'
CHECK = 'int sorted(int *v,int n){int i;for(i=1;i<n;i++)if(v[i-1]>v[i])return 0;return 1;}\n'
# name: (source, {index: True if eliminated})
CASES = {
 'insertion_sort': (SORT + CHECK + '''int a[9]={4,-7,4,0,32767,-32768,9,1,-1};int b[1]={5};
int main(void){sort(a,9);sort(b,1);sort(a,0);if(!sorted(a,9)||a[0]!=-32768||a[8]!=32767||b[0]!=5)return 1;return 0;}''', {'j': True}),
 'for_countdown': ('''int a[6]={1,2,3,4,5,6};
int tail(int *v,int n){int i,j,t=0;for(i=0;i<n;i++){for(j=i;j>0;--j)t+=v[j];}return t;}
int main(void){return tail(a,6)!=(2)+(2+3)+(2+3+4)+(2+3+4+5)+(2+3+4+5+6);}''', {'j': True}),
 'global_array': ('''int g[5]={9,8,7,6,5};
int shift(int k){int j,s=0;j=k;while(j!=0){s+=g[j-1];j--;}return s;}
int main(void){return shift(5)!=35||shift(0)!=0||shift(1)!=9;}''', {'j': False}),
 'kept_after_loop': ('''int a[4]={3,1,2,0};
int where(int *v,int n){int i,j;for(i=0;i<n;i++){j=i;while(j>0&&v[j-1]>0)--j;if(j==0)return i;}return -1;}
int main(void){return where(a,4)!=0;}''', {'j': False}),
 'extra_write': ('''int a[4]={5,6,7,8};
int odd(int *v,int n){int i,j,t=0;for(i=0;i<n;i++){j=i;while(j>0){t+=v[j];j=0;--j;}}return t;}
int main(void){return odd(a,4)!=6+7+8;}''', {'j': False}),
 'unproven_entry': ('''int a[4]={5,6,7,8};
int down(int *v,int k){int j,t=0;j=k;while(j>0){t+=v[j-1];--j;}return t;}
int main(void){return down(a,3)!=18||down(a,-2)!=0;}''', {'j': False}),
 'wide_stride': ('''long w[4]={1L,2L,3L,4L};
long sumw(long *v,int n){int i,j;long t=0;for(i=0;i<n;i++){j=i;while(j>0){t+=v[j];--j;}}return t;}
int main(void){return sumw(w,4)!=2L+(2L+3L)+(2L+3L+4L);}''', {'j': False}),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True); report = {}
    for name, (source, expected) in CASES.items():
        host = OUT/(name + '-host.c'); host.write_text(source, encoding='ascii'); exe = host.with_suffix('.exe')
        support.run([ROOT/'tools/msvc.cmd', '/nologo', '/std:c17', '/O2', '/Fo' + str(host.with_suffix('.obj')), '/Fe' + str(exe), host])
        assert subprocess.run([str(exe)], timeout=5).returncode == 0, name + ' host'
        on = checks.build(name + '_on', source, True, compiler=COMPILER)
        off = checks.build(name + '_off', source, True, compiler=COMPILER, extra_flags=['--no-index-elimination'])
        assert '; eliminated index' not in off['assembly'], name
        for index, eliminated in expected.items():
            got = f'; eliminated index {index}:' in on['assembly']
            assert got == eliminated, (name, index, eliminated, got)
        report[name] = dict(on=on['master_clocks'], off=off['master_clocks'])
        print(f"PASS index elimination {name}: {'eliminated' if any(expected.values()) else 'kept'}, "
              f"{off['master_clocks']} -> {on['master_clocks']} clocks", flush=True)
    (OUT/'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS index elimination: MSVC references, enabled/disabled ROMs, elimination expectations')


if __name__ == '__main__':
    main()
