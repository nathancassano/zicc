"""Call functions through pointers, including callbacks in other banks and callbacks from sort and search."""
import os
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'callbacks-check'
spec = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

DRIVER = r'''
#include <stdlib.h>
#include <string.h>
typedef long (*Callback)(int, int, long);
long add(int,int,long);
Callback global=add;
extern Callback other;
long recurse(Callback fn, int n, long value);
int compare_records(const void *, const void *);
long (*choose(int n))(int,int,long);
long known_callback(int n);
long changed_callback(int n);
long escaped_callback(int n);
long volatile_callback(int n);
long static_callback(int n);
long static_callback_after_call(int n);

static long invoke(long fn(int,int,long),int x){
    return fn(x,2,65536L);
}
int main(void){
    Callback callbacks[2]={&add,global};
    char records[5][3]={{4,40,41},{2,20,21},{9,90,91},{2,22,23},{1,10,11}};
    char key=4;
    Callback empty=NULL;
    int (*strings)(const char * __far,const char * __far)=strcmp;
    if(empty!=NULL||NULL!=choose(0)||(key?NULL:global)!=NULL)return 7;
    if(strings("abc","abc")||strings("a","b")>=0)return 8;
    if(sizeof(Callback)!=4||global!=other||callbacks[0]!=callbacks[1])return 1;
    if(invoke(choose(1),1)!=65539L||(*callbacks[0])(1,2,3L)!=6L)return 2;
    if(recurse(callbacks[1],3,65536L)!=65545L)return 3;
    if(known_callback(3)!=65541L||changed_callback(0)!=65541L||
       changed_callback(3)!=65531L||escaped_callback(3)!=65531L||
       volatile_callback(3)!=65541L)return 9;
    if(static_callback(3)!=65541L||static_callback_after_call(3)!=65531L)return 10;
    qsort(records,5,3,compare_records);
    if(records[0][0]!=1||records[0][2]!=11||records[1][0]!=2||
       records[2][0]!=2||records[3][1]!=40||records[4][0]!=9)return 4;
    if(bsearch(&key,records,5,3,compare_records)!=&records[3])return 5;
    key=8;
    if(bsearch(&key,records,5,3,compare_records)!=0||
       bsearch(&key,records,0,3,compare_records)!=0)return 6;
    qsort(records,0,3,compare_records);
    return 0;
}
'''

KERNEL = r'''
typedef long (*Callback)(int, int, long);
long add(int a,int b,long c){return a+b+c;}
long subtract(int a,int b,long c){return c-a-b;}
__noinline void replace_callback(Callback *fn){*fn=subtract;}
long known_callback(int n){
    Callback fn=&add;
    return fn(n,2,65536L);
}
long changed_callback(int n){
    Callback fn=add;
    if(n)fn=subtract;
    return fn(n?n:3,2,65536L);
}
long escaped_callback(int n){
    Callback fn=add;
    replace_callback(&fn);
    return fn(n,2,65536L);
}
long volatile_callback(int n){
    volatile Callback fn=add;
    return fn(n,2,65536L);
}
static Callback static_target;
long static_callback(int n){
    static_target=add;
    return static_target(n,2,65536L);
}
long static_callback_after_call(int n){
    static_target=add;
    replace_callback(&static_target);
    return static_target(n,2,65536L);
}
Callback other=&add;
long (*choose(int n))(int,int,long){return n?add:0;}
long recurse(Callback fn,int n,long value){
    if(!n)return value;
    return recurse(fn,n-1,fn(n,1,value));
}
int compare_records(const void *a,const void *b){
    Callback fn=other;
    return (int)fn(*(const char *)a,-*(const char *)b,0L);
}
'''

BAD = {
    'assignment': ('int f(long); int main(void){int (*p)(int)=f;return 0;}', 'incompatible function pointer'),
    'argument': ('int f(int); int main(void){int (*p)(int)=f;return p();}', 'wrong argument count'),
    'arithmetic': ('int f(int); int main(void){int (*p)(int)=f;p++;return 0;}', 'function pointer arithmetic'),
    'object_cast': ('int f(int); int main(void){return (void *)f!=0;}', 'function and object pointers'),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    support.OUT = OUT
    driver, kernel = OUT / 'driver.c', OUT / 'kernel.c'
    driver.write_text(DRIVER)
    kernel.write_text(KERNEL)
    asm = OUT / 'kernel.s'
    support.run([ROOT / 'build/zicc.exe', kernel, '-o', asm])
    assembly = asm.read_text()
    def body(name):
        return assembly.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
    assert '.loword(_add)' in body('known_callback') and 'jml [' not in body('known_callback')
    assert 'jsr .loword(_add)' in body('static_callback') and 'jml [' not in body('static_callback')
    for name in ('changed_callback', 'escaped_callback', 'volatile_callback','static_callback_after_call'):
        assert 'jml [' in body(name), body(name)
    for stage, lto in ((1, False), (3, False), (4, True)):
        raw = OUT / f'stage{stage}.raw'
        support.run([sys.executable, ROOT / 'tools/build-rom.py', driver, kernel,
                     '--stage', str(stage), '-o', raw, *(['--lto'] if lto else [])])
        labels = {name.removeprefix('_'): int(addr, 16)
                  for addr, name in re.findall(r'^al (\w+) \.(\S+)$',
                                               raw.with_suffix('.labels').read_text(), re.M)}
        if stage == 3:
            assert labels['qsort'] >> 16 != labels['compare_records'] >> 16
            assert labels['bsearch'] >> 16 != labels['compare_records'] >> 16
        rom = raw.with_suffix('.sfc')
        support.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
        support.emulate(rom, labels, 0)
    for name, (source, diagnostic) in BAD.items():
        path = OUT / f'{name}.c'
        path.write_text(source)
        result = subprocess.run([str(ROOT / 'build/zicc.exe'), str(path), '-o',
                                 str(path.with_suffix('.s'))], capture_output=True, text=True)
        assert result.returncode and diagnostic in result.stderr, (name, result.stderr)
    print('PASS: direct and nested callbacks, cross-bank qsort/bsearch, source LTO and constraints')


if __name__ == '__main__':
    main()
