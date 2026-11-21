"""Legacy C declarations, default promotions and frontend ABI normalization."""
import os
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'legacy-function-check'
spec=importlib.util.spec_from_file_location('legacy_support',ROOT/'tests/check-compiler.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)

KERNEL='''typedef Index;
static count=0;
visits(void){return count;}
narrow(a,b,c)
signed char a,c;
unsigned char b;
{signed char *p=&a;++count;*p=*p+1;if(sizeof(a)!=1)return -999;return a+b+c;}
byte(a) unsigned char a; {++count;return a;}
constant(c) const signed char c; {return c;}
long wide(a,b,c) long a,c;char b; {++count;return a+(long)b+c;}
float real(a,b) float a;char b; {++count;return b==3?a:0.0f;}
rows(a,n) int a[][3];int n;
{Index i,j,total=0;++count;for(i=0;i<n;++i)for(j=0;j<3;++j)total+=a[i][j];return total;}
recur(n) register n; {if(n<2)return n;return recur(n-1)+recur(n-2);}
defaulted(x,y) int x; {return x+y;}
int prior(int);
prior(c) char c; {return c;}
unchanged(x) int x; {return x+1;}
int unchanged(int renamed);
eight(a,b,c,d,e,f,g,h) char a,b,c,d,e,f,g,h; {return a+b+c+d+e+f+g+h;}
'''
DRIVER='''int narrow();int byte();long wide();float real();int rows();int recur();
int constant();int defaulted();int prior(int);int unchanged(int);int eight();int visits();
extern external;
external=5;
int call_late(void){return late((unsigned char)250);}
late(c) char c; {return c+1;}
main(){
 int matrix[2][3];int i,j;register local=7;
 for(i=0;i<2;++i)for(j=0;j<3;++j)matrix[i][j]=i*3+j+1;
 if(narrow(383,300,-130)!=42)return 1;
 if(byte((unsigned char)255)!=255||byte(300)!=44||byte(-1)!=255)return 2;
 if(wide(0x10001L,257,0x20002L)!=0x30004L)return 3;
 if(real(1.5f,259)!=1.5f)return 4;
 if(rows(matrix,2)!=21||recur(8)!=21)return 5;
 if(defaulted(3,4)!=7||prior(300)!=44||unchanged(8)!=9||constant(-130)!=126)return 6;
 if(eight(257,258,259,260,261,262,263,264)!=36)return 7;
 if(call_late()!=251||external!=5||local!=7||visits()!=7)return 8;
 return 0;
}
'''
BAD={
 'duplicate_names':('int f(a,a) int a; {return a;}','duplicate parameter'),
 'duplicate_decl':('int f(a) int a;char a;{return a;}','duplicate declaration'),
 'extra_decl':('int f(a) int b;{return a;}','non-parameter'),
 'initializer':('int f(a) int a=1;{return a;}','parameter cannot have an initializer'),
 'void':('int f(a) void a;{return 0;}','scalar or pointer'),
 'incomplete_aggregate':('struct S;int f(a) struct S a;{return 0;}','complete aggregate'),
 'body_missing':('int f(a,b);','require a function definition'),
 'mixed':('int f(a,int b){return 0;}','K&R parameter name'),
 'too_many':('int f('+','.join('p'+str(i) for i in range(128))+'){return 0;}','too many parameters'),
 'too_many_prototype':('int f('+','.join(['int']*128)+');','too many parameters'),
 'too_many_arguments':('int f();int g(void){return f('+','.join(['1']*257)+');}','too many function arguments'),
 'expression_depth':('int f(void){return '+'('*257+'1'+')'*257+';}','nesting exceeds compiler limit'),
 'declarator_depth':('int '+'('*257+'value'+')'*257+';','nesting exceeds compiler limit'),
 'pointer_depth':('int '+'*'*32+'value;','too many pointer levels'),
 'stack_arguments':('int f(long,...);int g(void){return f('+','.join(['1L']*256)+');}','exceeds stack byte budget'),
 'prototype_char':('int f();int f(char);','default argument promotions'),
 'prototype_float':('int f();int f(float);','default argument promotions'),
 'definition_char':('int f(char);int f(c) char c;{return c;}','conflicting parameter type'),
 'definition_float':('int f(float);int f(x) float x;{return 0;}','conflicting parameter type'),
 'definition_count':('int f(int,int);int f(a) int a;{return a;}','conflicting prototype'),
 'variadic':('int f();int f(int,...);','variadic prototype conflicts'),
 'modern_duplicate':('int f(int a,int a){return a;}','duplicate parameter'),
 'parameter_local':('int f(a) int a;{int a;return a;}','duplicate local'),
 'narrow_parameter_local':('int f(a) char a;{int a;return a;}','duplicate local'),
 'const_parameter':('int f(a) const char a;{a=2;return a;}','assignment requires a writable scalar'),
 'known_count':('int f(a) int a;{return a;}int main(void){return f();}','wrong argument count'),
 'known_promotion':('int f(a) int a;{return a;}int main(void){return f(3L);}','promoted K&R parameter'),
 'implicit_return_conflict':('int main(void){return f();}long f(void){return 1L;}','conflicting declaration'),
 'undeclared_variable':('int main(void){return unknown;}','undeclared identifier'),
 'case_outside':('int main(void){case 0:;}','case/default outside switch'),
}


def compile_source(name,source):
 path=OUT/(name+'.c');asm=OUT/(name+'.s');path.write_text(source)
 result=support.run([ROOT/'build/zicc.exe',path,'-o',asm])
 return path,asm,result.stderr


def main():
 OUT.mkdir(parents=True,exist_ok=True);support.OUT=OUT
 _,dialect_rom,dialect_labels=support.compile_case('c89-keywords',
  '__inline int inline(int n){return n+1;}int main(void){return inline(4)!=5;}',
  flags=('--c89-keywords',))
 support.emulate(dialect_rom,dialect_labels,0)
 _,alias_rom,alias_labels=support.compile_case('alternate-keywords', '''
  static __const__ __signed__ char value=-3;
  static __volatile int visits;
  __attribute((noinline)) __attribute__(()) int read(__const int x){
    __volatile__ __signed int sample=x;
    ++visits;
    return sample+value;
  }
  int main(void){return read(7)!=4||visits!=1;}
 ''')
 support.emulate(alias_rom,alias_labels,0)
 kernel,asm,warnings=compile_source('kernel',KERNEL)
 support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',OUT/'kernel.o',asm])
 # compile_case emits the driver independently; no translation-unit folding can
 # hide disagreement about the incoming register/stack argument representation
 _,rom,labels=support.compile_case('driver',DRIVER,extra_objects=[OUT/'kernel.o',
  ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
 log=support.emulate(rom,labels,0)
 _,_,driver_warnings=compile_source('driver-warning-check',DRIVER)
 warnings+=driver_warnings
 for required in ('implicit int type specifier','K&R identifier-list','implicit int for parameter',
                  'implicit declaration of function','without a prototype'):
  assert required in warnings,(required,warnings)
 assert re.search(r':\d+:\d+: warning:',warnings),warnings
 (OUT/'warnings.txt').write_text(warnings)
 # The host reference executes the same separate-TU C89 syntax and semantics
 host=OUT/'host.exe'
 support.run([ROOT/'tools/msvc.cmd','/nologo','/TC','/J','/O2','/Fo'+str(OUT)+'/',
              '/Fe'+str(host),OUT/'driver.c',kernel])
 support.run([host])
 # Int parameters, including pointer/array adjustment, need no new instructions
 pairs=[('word','int same(a,b) int a,b;{return a+b;}',
                'int same(int a,int b){return a+b;}'),
        ('narrow','int same(c) signed char c;{return c+1;}',
                  'int same(int incoming){signed char c=(signed char)incoming;return c+1;}'),
        ('array','int same(a) int a[][3];{return a[1][2];}',
                 'int same(int a[][3]){return a[1][2];}')]
 identical=[]
 for name,legacy,modern in pairs:
  _,a,_=compile_source(name+'-old',legacy);_,b,quiet=compile_source(name+'-modern',modern)
  assert not quiet,quiet
  def normalize(path):
   code=re.sub(r'^;.*\n','',path.read_text(),flags=re.M)
   return re.sub(r'cg_[a-z_]+_relax_', 'cg_fixture_relax_',code)
  assert normalize(a)==normalize(b),name
  identical.append(name)
 # A visible prototype continues to govern calls after a compatible K&R body,
 # and after a later non-prototype declaration
 _,p,diagnostic=compile_source('prototype-preserved',
  'int f(int);int f(c) char c;{return c;}int f();int main(void){return f(300)!=44;}')
 _,r,l=support.compile_case('prototype-runtime',(OUT/'prototype-preserved.c').read_text())
 support.emulate(r,l,0)
 # Keep the caller and callee separate so the backend must use the public ABI
 types=['int']*127
 types[8]='long'
 types[9]='const char * __far'
 types[126]='long'
 params=','.join(f'{t} p{i}' for i,t in enumerate(types))
 _,many_asm,_=compile_source('many-parameter-kernel',
  f'long many({params}){{return p0+p1+p8+p9[1]+p125+p126;}}')
 many_obj=OUT/'many-parameter-kernel.o'
 support.run([support.CC65/'ca65.exe','--cpu','65816','-o',many_obj,many_asm])
 args=['1']*127
 args[8]='65536L'
 args[9]='"ab"'
 args[126]='131072L'
 _,many_rom,many_labels=support.compile_case('many-argument-driver',
  f'long many({params});int main(void){{return many({",".join(args)})!=196709L;}}',
  extra_objects=[many_obj])
 support.emulate(many_rom,many_labels,0)
 compile_source('maximum-argument-count',
  'int f(int,...);int g(void){return f('+','.join(['1']*256)+');}')
 compile_source('nested-calls',
  'int f(int);int g(int x){return '+'f('*48+'x'+')'*48+';}')
 compile_source('nested-signature', 'void f(int (*callback)(int, int));')
 compile_source('stack-budget-fits',
  'int f(long,...);int g(void){return f('+','.join(['1L']*255)+');}')
 names=','.join(f'p{i}' for i in range(127))
 compile_source('many-kr-parameters',f'int many({names}) int {names};{{return p126;}}')
 for name,(source,message) in BAD.items():
  path=OUT/(name+'.c');path.write_text(source)
  # Match the binary64 ABI used by the positive K&R cases above
  result=subprocess.run([str(ROOT/'build/zicc.exe'),str(path),'-o',str(OUT/(name+'.s')),'--binary64'],
                        capture_output=True,text=True)
  assert result.returncode and message in result.stderr,(name,result.stderr)
  assert re.search(r':\d+:\d+: error:',result.stderr),result.stderr
 (OUT/'results.json').write_text(json.dumps(dict(runtime=log,warnings=warnings,
  identical_assembly=identical,rejected=list(BAD),
  compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest(),
  rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest()),indent=2)+'\n')
 print(f'PASS: separate-TU K&R/MSVC/Mesen promotions, char narrowing, wide/float/array/register/recursive/eight-argument calls; warnings; three identical typed lowerings; {len(BAD)} diagnostics')


if __name__=='__main__':main()
