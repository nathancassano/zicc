"""Test calls when the compiler knows the memory bank and when it must use the public entry point."""
import os
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'bank-call-check';c.OUT.mkdir(parents=True,exist_ok=True)
SOURCE=r'''
int cp(char *d,const char * __far s);
int __attribute__((__noclone__)) guarded(char *d,const char * __far s);
int reversed(const char * __far s,char *d);
int eq(const char * __far a,const char * __far b);
char a[20],b[20];
const char rom[4]={'a','b','c',0};
int main(void){
 char local[20];unsigned long keep=0x12345678UL;
 char * __far edge=(char * __far)0x7effffUL;
 extern int protected_copy(char *d,const char * __far s) __attribute__((noclone));
 if(guarded(local,rom)!=3||protected_copy(local,rom)!=3)return 9;
 if(cp(local,rom)!=3||reversed(rom,a)!=3)return 1;
 if(!eq(local,rom)||!eq(rom,local)||!eq(a,local))return 2;
 if(cp(b,local)!=3||!eq(b,local))return 3;
 if(keep+(unsigned)cp(local,"xyz")!=0x1234567bUL||keep!=0x12345678UL)return 4;
 if((unsigned)cp(a,"a")+(unsigned)cp(b,"bc")!=3)return 5;
 if(!eq("abc","abc")||eq("abc","abd"))return 6;
 edge[0]='X';edge[1]='Y';edge[2]=0;
 if(cp(local,edge)!=2||!eq(local,edge))return 7;
 if(cp(local,local)!=2||cp(local,local+1)!=1||local[0]!='Y')return 8;
 return 0;
}
/* Definitions deliberately follow the caller. No inlining is performed */
int cp(char *d,const char * __far s){int n=0;while(*s){*d++=*s++;++n;}*d=0;return n;}
int guarded(char *d,const char * __far s){int n=0;while(*s){*d++=*s++;++n;}*d=0;return n;}
int protected_copy(char *d,const char * __far s){int n=0;while(*s){*d++=*s++;++n;}*d=0;return n;}
int reversed(const char * __far s,char *d){int n=0;while(*s){*d++=*s++;++n;}*d=0;return n;}
int eq(const char * __far a,const char * __far b){while(*a&&*a==*b){++a;++b;}return (unsigned char)*a==(unsigned char)*b;}
'''
run=c.run;report={}
for mode in ('on','off'):
    def command(args,*a,**kw):
        if mode=='off' and Path(args[0]).name=='zicc.exe':args=[*args,'--no-bank-specialization']
        return run(args,*a,**kw)
    c.run=command
    _,rom,labels=c.compile_case(mode,SOURCE,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
    asm=rom.with_suffix('.s').read_text()
    if mode=='on':
        assert len(re.findall(r'^; bank specialization:',asm,re.M))==6
        for name in ('guarded','protected_copy'):
            assert f'    jsr .loword(_{name})' in asm
            assert not re.search(r'^; bank specialization:.* '+name+r' ',asm,re.M)
        assert '    jsr .loword(__bank_' in asm
        assert '    jsr .loword(_eq)' in asm and '    jsr .loword(_cp)' in asm
        assert '.bankbyte(_rom)' in asm and '*$10000,x' in asm
        # Each generated body remains an independent callable routine
        for body in asm.split('; bank specialization:')[1:]:assert '    rts\n' in body
    else:assert '; bank specialization:' not in asm
    report[mode]=c.emulate(rom,labels,0)
    report[mode]+=run([sys.executable,ROOT/'tests/check-libc.py','--pal-rom',rom],timeout=30).stdout
    print('PASS bank calls '+mode+' NTSC/PAL')
c.run=run
# Only a declaration in a separate translation unit marks guarded. Its twin
# must still specialize in the very same source-LTO build
declarations=c.OUT/'noclone-declarations.c'
declarations.write_text('int guarded(char *,const char * __far) __attribute__((noclone));')
provider=c.OUT/'noclone-provider.c'
provider.write_text(SOURCE.split('/* Definitions deliberately')[1].split('*/',1)[1])
driver=r'''
int cp(char *,const char * __far),guarded(char *,const char * __far);
char buffer[8];
int main(void){return cp(buffer,"abc")!=3||guarded(buffer,"abc")!=3||buffer[2]!='c';}
'''
_,rom,labels=c.compile_case('noclone_lto',driver,
    flags=['--no-inline','--lto-source',str(provider),'--lto-source',str(declarations)],
    extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
asm=rom.with_suffix('.s').read_text()
assert re.search(r'^; bank specialization:.* cp ',asm,re.M)
assert not re.search(r'^; bank specialization:.* guarded ',asm,re.M)
assert '    jsr .loword(_guarded)' in asm
report['noclone_lto']=c.emulate(rom,labels,0)
for name,text in [('object','int x __attribute__((noclone));'),
                  ('type','__attribute__((noclone)) struct s { int x; };')]:
    path=c.OUT/(name+'.c');path.write_text(text)
    result=run([ROOT/'build/zicc.exe',path,'-o',path.with_suffix('.s')],expected=1)
    assert 'noclone requires a function' in result.stderr
print('PASS noclone source LTO and rejected object/type declarations')
# An object split across banks must fail the private-entry containment proof
_,_,_=c.compile_case('containment',SOURCE,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
config=c.OUT/'cross.cfg';text=(ROOT/'linker/lorom32.cfg').read_text()
text=text.replace('MEMORY {','MEMORY {\n CROSS: start = $80FFFE, size = $1000, type = ro, file = "";')
text=text.replace('RODATA:     load = ROM,','RODATA:     load = CROSS,');config.write_text(text)
result=run([c.CC65/'ld65.exe','-C',config,'-o',c.OUT/'cross.raw',ROOT/'build/startup.o',c.OUT/'containment.o',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o',ROOT/'build/nmi.o',ROOT/'build/vectors.o',ROOT/'build/rom_header.o'],expected=1)
assert 'specialized ROM object crosses bank' in result.stderr,result.stderr
report['cross_bank_link_assertion']='PASS'
(c.OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
