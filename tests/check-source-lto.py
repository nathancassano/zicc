"""Check how optimization across C files handles preprocessing, names, storage and calls across banks."""
import os
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'source-lto-check'
spec=importlib.util.spec_from_file_location('inlining',ROOT/'tests/check-inlining.py')
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
c=t.c;b=t.b

HOST='''#ifndef __ZICC__
#define __noinline
#define __forceinline
#endif
'''
DRIVER=r'''
#ifdef VALUE
#error macro leaked from another translation unit
#endif
int take_a(int),take_b(int),get_a(void),get_b(void);
int automatic(int);int hinted(int);int blocked(int);
__noinline int automatic_case(int x){return automatic(x);}
__noinline int hinted_case(int x){return hinted(x);}
const char * __far literal_a(void);const char * __far pointer_a(void);
struct Node{int value;struct Node *next;};
int node_add(struct Node *,int);
volatile int seed=5;__noinline int input(void){return seed;}
int main(void){int x=input();struct Node a,z;const char * __far p;
 if(take_a(x)!=9||take_b(x)!=17||take_a(x)!=10||get_a()!=2||get_b()!=1)return 1;
 p=literal_a();if(p!=pointer_a()||p[0]!='A'||p[4]!='a')return 2;
 if(automatic_case(x)!=8||hinted_case(x)!=x+45||blocked(x)!=12)return 3;
 a.value=3;z.value=7;a.next=&z;z.next=&a;
 if(node_add(&a,2)!=12||a.value!=5||z.value!=7)return 4;
 return 0;}
'''
A=r'''
#define VALUE 3
static int counter;
struct Private{int value;};static struct Private private_value;
static int helper(int x){counter++;private_value.value=x;return private_value.value+VALUE+counter;}
__forceinline int take_a(int x){return helper(x);}
__noinline int get_a(void){return counter;}
__forceinline const char * __far literal_a(void){return "Alpha";}
__noinline const char * __far pointer_a(void){return literal_a();}
int automatic(int x){return x+3;}
extern inline int hinted(int x){x+=1;x+=2;x+=3;x+=4;x+=5;x+=6;x+=7;x+=8;x+=9;return x;}
__noinline int blocked(int x){return x+7;}
'''
B=r'''
#ifndef VALUE
#define VALUE 11
#endif
static int counter;
struct Private{long value;};static struct Private private_value;
static int helper(int x){counter++;private_value.value=x;return (int)private_value.value+VALUE+counter;}
__forceinline int take_b(int x){return helper(x);}
__noinline int get_b(void){return counter;}
struct Node{int value;struct Node *next;};
__forceinline int node_add(struct Node *p,int amount){p->value+=amount;return p->value+p->next->value;}
'''


def sources(name,texts):
    directory=OUT/name;directory.mkdir(parents=True,exist_ok=True);paths=[]
    for i,text in enumerate(texts):
        path=directory/('unit'+str(i)+'.c');path.write_text(HOST+text);paths.append(path)
    return directory,paths


def build(name,texts,stage=1,flags=(),host=False):
    directory,paths=sources(name,texts);stem=directory/'program'
    c.run([sys.executable,ROOT/'tools/build-rom.py',*paths,'--lto','--stage',str(stage),*flags,'-o',stem.with_suffix('.raw')])
    c.run([ROOT/'build/romtool.exe',stem.with_suffix('.raw'),stem.with_suffix('.sfc'),ROOT/'tests/title.txt'])
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
    manifest=json.loads(stem.with_suffix('.allocation.json').read_text());assert manifest['source_lto'] and len(manifest['lto_sources'])==len(paths)
    stage_dir=Path(manifest['evidence'])/('stage'+str(stage));assembly='\n'.join(p.read_text() for p in stage_dir.glob('*.s') if p.name.startswith('0_'))
    digest=b.run(directory,stem.with_suffix('.sfc'),sy)
    if host:
        exe=directory/'reference.exe';c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(directory)+'/', '/Fe'+str(exe),*paths]);c.run([exe])
    print('PASS source LTO',name,flush=True);return dict(rom_sha256=digest,stage=stage),assembly


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--case',choices=['semantics','linkage','recursion','assembly','diagnostics']);args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);report={}
    if not args.case or args.case=='semantics':
        for stage in (1,2,3,4):
            result,assembly=build('semantics-'+str(stage),[DRIVER,A,B],stage,host=stage==1)
            assert '; inlined call: main take_a' in assembly and '; inlined call: main take_b' in assembly
            assert '; inlined call: automatic_case automatic' in assembly and '; inlined call: hinted_case hinted' in assembly
            assert not re.search(r'; inlined call: \w+ blocked\b',assembly)
            assert re.search(r'\b(?:jsr .loword\(_blocked\)|jsl _blocked)',assembly)
            assert assembly.count('_private_value: .res')==2
            report['stage'+str(stage)]=result
        report['reversed'],_=build('reversed',[B,A,DRIVER])
    if not args.case or args.case=='linkage':
        a='inline int choice(int x){return x+1;}__noinline int from_a(int x){return choice(x);}'
        provider='int choice(int x){return x+7;}'
        for mode,flags,expected in [('inline',(),4),('fallback',('--no-inline',),10)]:
            driver=f'int from_a(int);int choice(int);int main(void){{return from_a(3)!={expected}||choice(3)!=10;}}'
            report[mode],assembly=build('link-'+mode,[driver,a,provider],flags=flags)
            assert len(re.findall(r'^_choice:',assembly,re.M))==1
        # A prohibition on the defining TU applies to calls in other TUs
        report['policy'],assembly=build('policy',['int f(int);int main(void){return f(3)!=4;}','__noinline int f(int x){return x+1;}'])
        assert '; inlined call: main f' not in assembly
        for stage in (3,4):
            driver='int strcmp(const char * __far,const char * __far);extern int calls;int main(void){return strcmp("x","y")!=37||calls!=1;}'
            provider='int calls;__noinline int strcmp(const char * __far a,const char * __far b){calls++;return 37;}'
            report['override-'+str(stage)],_=build('override-'+str(stage),[driver,provider],stage)
    if not args.case or args.case=='recursion':
        driver='int f(int),g(int);volatile int n=4;int main(void){return f(n)!=5||g(n)!=6;}'
        a='int g(int);int f(int n){if(!n)return 1;return g(n-1)+1;}'
        z='int f(int);int g(int n){if(!n)return 2;return f(n-1)+1;}'
        report['recursion'],assembly=build('recursion',[driver,a,z],host=True)
        assert '; inlined call: main f' not in assembly and '; inlined call: main g' not in assembly
    if not args.case or args.case=='assembly':
        directory,paths=sources('assembly',['int external_asm(int);int main(void){return external_asm(5)!=6;}','int unused(int n){return n+2;}'])
        c.OUT=directory;helper=directory/'helper.s';helper.write_text('.setcpu "65816"\n.a16\n.i16\n.export _external_asm\n.segment "CODE"\n_external_asm:\n txa\n inc a\n rts\n')
        c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',helper.with_suffix('.o'),helper])
        _,rom,sy=c.compile_case('mixed',paths[0].read_text(),extra_objects=[helper.with_suffix('.o')],flags=['--lto-source',str(paths[1])])
        report['assembly']=b.run(directory,rom,sy,expect_calls={'external_asm':1})
        assert '.import _external_asm' in (directory/'mixed.s').read_text()
        print('PASS source LTO external assembly ABI',flush=True)
    if not args.case or args.case=='diagnostics':
        cases=[
          ('duplicate',['int f(void){return 1;}','int f(void){return 2;}'],'duplicate definition'),
          ('object',['int x;','int x;'],'duplicate definition'),
          ('return',['int f(void);','long f(void){return 2;}'],'conflicting type'),
          ('pointer',['int f(int *);','int f(int * __far p){return *p;}'],'conflicting parameter'),
          ('aggregate',['struct S{int x;};int f(struct S *);','struct S{long x;};int f(struct S *p){return p->x;}'],'conflicting parameter'),
          ('same-size',['struct S{int x;};extern struct S value;','struct S{unsigned x;};struct S value;'],'conflicting type'),
          ('incomplete-bridge',['struct S;int f(struct S *);','struct S{int x;};int f(struct S *);','struct S{long x;};int f(struct S *);'],'conflicting parameter'),
          ('array-bridge',['extern int a[];','extern int a[3];','extern int a[4];'],'conflicting type'),
          ('policy',['__forceinline int f(int);','__noinline int f(int x){return x;}'],'conflicts'),
          ('placement',['extern __dpage int value;','int value;'],'conflicting placement'),
          ('recursive',['__forceinline int f(int);int g(int n){return f(n);}int main(void){return f(1);}','int g(int);int f(int n){return g(n);}'],'recursive expansion'),
          ('interrupt',['void handler(void);int main(void){handler();return 0;}','__interrupt(nmi) void handler(void){}'],'cannot be called')]
        for name,texts,message in cases:
            directory,paths=sources('bad-'+name,texts)
            command=[ROOT/'build/zicc.exe',paths[0],'-o',directory/'bad.s']+[item for p in paths[1:] for item in ['--lto-source',p]]
            r=c.run(command,expected=1);assert message in r.stderr,(name,r.stderr);report[name]=r.stderr
            print('PASS source LTO diagnostic',name,flush=True)
    report['inputs']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'build/zicc.exe',ROOT/'src/source_lto.inc',Path(__file__)]}
    (OUT/('results-'+(args.case or 'all')+'.json')).write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
