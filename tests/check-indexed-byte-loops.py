"""Check loops that walk byte arrays, including signed limits and temporary values in register B."""
import os
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'indexed-byte-loop-check'
spec = importlib.util.spec_from_file_location('checks', Path(__file__).with_name('check-strength.py'))
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

SWAP = '''void rev(unsigned char *text,int length){int left=0,right=length-1;unsigned char saved;
while(left<right){saved=text[left];text[left]=text[right];text[right]=saved;++left;--right;}}
'''
CASES = {
    'strings': (ROOT / 'samples/string_processing.c').read_text(),
    'bounds': SWAP + '''int main(void){unsigned char a[7];int i,n;
for(i=0;i<7;++i)a[i]=i;
rev(a+1,0);rev(a+1,1);rev(a+1,-1);rev(a+1,-32767);
for(i=0;i<7;++i)if(a[i]!=i)return 1;
for(n=2;n<=5;++n){for(i=0;i<7;++i)a[i]=i;rev(a+1,n);
if(a[0]!=0||a[6]!=6)return 2;
for(i=0;i<n;++i)if(a[i+1]!=n-i)return 3;}
a[0]=0;a[1]=128;a[2]=255;a[3]=7;rev(a,4);
if(a[0]!=7||a[1]!=255||a[2]!=128||a[3]!=0)return 4;return 0;}''',
    'pages': SWAP + '''unsigned char a[302];int main(void){int i;
for(i=0;i<302;++i)a[i]=(unsigned char)i;
rev(a+1,300);for(i=0;i<300;++i)if(a[i+1]!=(unsigned char)(300-i))return 1;
if(a[0]!=0||a[301]!=(unsigned char)301)return 2;
rev(a+1,299);for(i=0;i<299;++i)if(a[i+1]!=(unsigned char)(i+2))return 3;
return 0;}''',
    'live_indices': '''int run(char *p,int n){int l=0,r=n-1,k=7;char saved;
while(l<r){saved=p[l];p[l]=p[r];p[r]=saved;++l;--r;++k;}
return l*100+r*10+k;}
int main(void){char a[5];a[0]=1;a[1]=2;a[2]=3;a[3]=4;a[4]=5;
if(run(a,4)!=219||a[0]!=4||a[1]!=3||a[2]!=2||a[3]!=1||a[4]!=5)return 1;
if(run(a,0)!=-3)return 2;return 0;}''',
    'stack_bounds': '''void range(char *p,int begin,int end){int l=begin,r=end;char saved;
while(l<r){saved=p[l];p[l]=p[r];p[r]=saved;++l;--r;}}
int main(void){char a[7];int i;for(i=0;i<7;++i)a[i]=i;
range(a,1,5);if(a[0]!=0||a[1]!=5||a[2]!=4||a[3]!=3||a[4]!=2||a[5]!=1||a[6]!=6)return 1;
range(a,5,1);if(a[1]!=5||a[5]!=1)return 2;
range(a+3,-2,2);if(a[1]!=1||a[2]!=2||a[3]!=3||a[4]!=4||a[5]!=5)return 3;
return 0;}''',
    'reordered': '''void rev(int n,char *p){int l=0,r=n-1;char s;
while(l<r){s=p[l];p[l]=p[r];p[r]=s;++l;--r;}}
int main(void){char a[4];a[0]=1;a[1]=2;a[2]=3;a[3]=4;rev(4,a);
return a[0]!=4||a[1]!=3||a[2]!=2||a[3]!=1;}''',
    'local_array': '''int main(void){unsigned char a[6];int l=0,r=5;unsigned char saved;
a[0]=0;a[1]=128;a[2]=255;a[3]=7;a[4]=8;a[5]=9;
while(l<r){saved=a[l];a[l]=a[r];a[r]=saved;++l;--r;}
if(l!=3||r!=2||a[0]!=9||a[1]!=8||a[2]!=7||a[3]!=255||a[4]!=128||a[5]!=0)return 1;
return 0;}''',
    'two_bases': '''void run(char *a,char *b,int end){int l=0,r=end;char saved;
while(l<r){saved=a[l];a[l]=b[r];b[r]=saved;++l;--r;}}
int main(void){char a[4],b[4];a[0]=1;a[1]=2;a[2]=3;a[3]=4;b[0]=5;b[1]=6;b[2]=7;b[3]=8;
run(a,b,3);return a[0]!=8||a[1]!=7||a[2]!=3||a[3]!=4||b[0]!=5||b[1]!=6||b[2]!=2||b[3]!=1;}''',
    'temp_arithmetic': '''void run(unsigned char *p,int n){int l=0,r=n-1;unsigned char s;
while(l<r){s=p[l];p[l]=p[r]+1;p[r]=s^128;++l;--r;}}
int main(void){unsigned char a[4];a[0]=255;a[1]=128;a[2]=127;a[3]=255;run(a,4);
return a[0]!=0||a[1]!=128||a[2]!=0||a[3]!=127;}''',
    'zero_origin': '''void run(unsigned char *p,int end){int l=0,r=end;unsigned char s;
while(l<r){s=p[l];p[l]=p[r];p[r]=s;++l;--r;}}
int main(void){unsigned char a[4];a[0]=1;a[1]=2;a[2]=3;a[3]=4;run(a,0);run(a,-1);
if(a[0]!=1||a[3]!=4)return 1;run(a,3);return a[0]!=4||a[1]!=3||a[2]!=2||a[3]!=1;}''',
    'unsigned_bounds': '''void run(unsigned char *p,unsigned short end){unsigned short l=0,r=end;unsigned char s;
while(l<r){s=p[l];p[l]=p[r];p[r]=s;++l;--r;}}
int main(void){unsigned char a[4];a[0]=1;a[1]=2;a[2]=3;a[3]=4;run(a,0);run(a,3);
return a[0]!=4||a[1]!=3||a[2]!=2||a[3]!=1;}''',
}
FALLBACKS = {
    'live_temporary': '''int run(char *p,int n){int l=0,r=n-1;char saved=42;
while(l<r){saved=p[l];p[l]=p[r];p[r]=saved;++l;--r;}return saved;}
int main(void){char a[4];a[0]=1;a[1]=2;a[2]=3;a[3]=4;
if(run(a,0)!=42||run(a,4)!=2||a[0]!=4||a[3]!=1)return 1;return 0;}''',
    'escaped_index': '''int *observed;
void observe(int *p){observed=p;}void run(char *p,int n){int l=0,r=n-1;char s;
observe(&l);while(l<r){s=p[l];p[l]=p[r];p[r]=s;++l;--r;}observed=0;}
int main(void){char a[2];a[0]=1;a[1]=2;run(a,2);return a[0]!=2||a[1]!=1;}''',
    'multiple_reads': '''void run(char *p,int n){int l=0,r=n-1;char s;
while(l<r){s=p[l];p[l]=s+1;p[r]=s;++l;--r;}}
int main(void){char a[2];a[0]=1;a[1]=2;run(a,2);return a[0]!=2||a[1]!=1;}''',
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks.OUT = OUT
    checks.support.OUT = OUT
    results = {}
    for name, source in {**CASES, **FALLBACKS}.items():
        cfile = OUT / (name + '-host.c')
        cfile.write_text(source)
        exe = cfile.with_suffix('.exe')
        checks.support.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/O2', '/D__far=',
                            '/Fo' + str(cfile.with_suffix('.obj')), '/Fe' + str(exe), cfile])
        assert subprocess.run([str(exe)], timeout=5).returncode == 0, name
        pair = {mode: checks.build(name + '_' + mode, source, True, register_loops=mode == 'on')
                for mode in ('off', 'on')}
        assert '; register loop:' not in pair['off']['assembly'], name
        assert ('; register loop:' in pair['on']['assembly']) == (name in CASES), name
        if name == 'strings':
            reverse = pair['on']['assembly'].split('_reverse_text:', 1)[1].split('__size_reverse_text', 1)[0]
            assert '; native indexed loop leaf' in reverse and '    tsc\n' not in reverse, reverse
            body = reverse.split('.a8\n', 1)[1].split('    rep #$20', 1)[0]
            assert body.count('    xba\n') == 2, body
            assert not re.search(r'\b(?:pha|pla|sep|rep)\b|,s|a:\$000[1-9],', body), body
            assert '    inx\n' in body and '    dey\n' in body, body
            assert pair['on']['master_clocks'] < pair['off']['master_clocks'], pair
        results[name] = {mode: {field: data[field] for field in ('master_clocks', 'code_bytes')}
                         for mode, data in pair.items()}
        print('PASS', name, results[name], flush=True)
    (OUT / 'results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
