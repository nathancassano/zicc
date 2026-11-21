"""Check which switch case runs after integer conversion and where nested break and continue statements go."""
import os
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'switch-check'
spec=importlib.util.spec_from_file_location('switch_support',ROOT/'tests/check-compiler.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
spec=importlib.util.spec_from_file_location('switch_interrupts',ROOT/'tests/check-interrupts.py')
interrupts=importlib.util.module_from_spec(spec);spec.loader.exec_module(interrupts)

KERNEL='''int calls,input,selectors[2];
int post_dead(void){int *p=selectors;switch(*p++){case 0:return 7;default:return 9;}}
int post_dead_offset(void){int *p=selectors+1;switch(*p--){case 0:return 7;default:return 9;}}
int post_live_case(void){int *p=selectors;switch(*p++){case 0:return *p;default:return 9;}}
int post_live_after(void){int *p=selectors;switch(*p++){case 0:break;default:return 9;}return *p;}
int read_once(void){++calls;return input;}
int once(void){switch(read_once()){calls+=100;case 1:return 11;case 3:return 33;default:return 99;}}
int fall(int x){int r=0;switch(x){case 1:r=10;default:r+=3;case 2:r+=7;break;case 3:r=40;}return r;}
int stacked(int x){switch(x){case 1:case 2:return 7;default:return 9;}}
int wide(unsigned long x){switch(x){case 0:return 1;case 0x10000UL:return 2;
case 0x12345678UL:return 3;case 0xffff0000UL:return 4;case 0xffffffffUL:return 5;default:return 6;}}
int signed_word(int x){switch(x){case -32767-1:return 1;case -1:return 2;case 32767:return 3;}return 4;}
int signed_wide(long x){switch(x){case -2147483647L-1L:return 1;case -1L:return 2;default:return 3;}}
int bytes(char x){switch(x){case -1:return 1;case 255:return 2;default:return 3;}}
int signed_bytes(signed char x){switch(x){case -1:return 1;case 127:return 2;default:return 3;}}
enum E {One=1,Two=2};
int constants(int x){switch(x){case One+Two:return 3;case sizeof(char[5]):return 5;case (1?7:9):return 7;default:return 0;}}
int nested(int x,int y){int r=0;switch(x){case 1:switch(y){case 1:r=7;break;default:r=9;}r+=3;break;
case 2:return 8;default:return 4;}return r;}
int targets(void){int i,r=0;for(i=0;i<6;++i){switch(i){case 1:continue;case 3:break;default:r+=i;}r+=10;}return r;}
int outer_break(void){int i,r=0;for(i=0;i<9;++i){switch(i){case 2:continue;default:break;}++r;if(i==6)break;}return r;}
int loops(void){int i=0,r=0;do{++i;switch(i){case 2:continue;default:r+=i;}}while(i<4);
i=0;while(i<4){++i;switch(i){case 3:continue;default:r+=i;}}return r;}
int duff(int x){int r=0;switch(x){case 0:do{r+=1;case 1:r+=2;case 2:r+=4;x=0;}while(x);}return r;}
int false_loop(int x){int r=0;switch(x){while(0){case 1:r=12;break;}}return r;}
int false_if(int x){int r=0;switch(x){if(0){case 1:r=9;break;}default:r=3;}return r;}
int after_return(int x){switch(x){case 1:{return 1;case 2:return 2;}case 3:return 3;default:return 4;}}
int no_case(void){switch(read_once()){calls+=100;}return 4;}
int empty_default(int enabled){if(enabled){switch(read_once()){default:;}}return calls;}
int bare(int x){switch(x)case 3:return 8;return 9;}
int scope(int x){int r=0;switch(x){case 1:{int x=7;r=x;break;}default:r=x;}return r;}
int infinite(int x){for(;;){switch(x){case 1:break;default:return 4;}return 7;}return 99;}
static inline int *literal_address(void){int *p;switch(-1){
case 0:p=selectors;break;case -2:case -1:p=selectors+1;break;default:p=selectors;}return p;}
int literal_load(void){return *literal_address();}
int literal_fall(void){int r=0;switch(-1){++calls;case -2:case -1:r=10;default:r+=7;break;case 3:r=40;}return r;}
int literal_break(int stop){int r=1;switch(8){case 8:r+=3;if(stop)break;default:r+=7;}return r;}
int literal_nested_case(void){int r=0;switch(1){if(0){case 1:r=9;break;}default:r=3;}return r;}
int literal_wide(void){switch(0x100000000ULL){case 0:return 6;case 0x100000000ULL:return 9;default:return 4;}}
'''
KERNEL+='int big(int x){switch(x){'+''.join('case '+str(i)+':return '+str(i*3+1)+';' for i in range(64))+'default:return -1;}}\n'
KERNEL+='int big_negated(int add){switch(-read_once()){'+''.join('case '+str(i)+':return add+'+str(i*3+1)+';' for i in range(1,65))+'default:return -1;}}\n'
KERNEL+='''#ifdef __ZICC__
#define ROM_FAR __far
#else
#define ROM_FAR
#endif
int string_switch(int selector){
    const char * ROM_FAR name="fallback";
    switch(selector){
        case 7:name="xx";
        case 8:name="ab";break;
        case 9:name="cd";break;
        case 10:name="ef";break;
    }
    return name[1];
}
static int pure_selected_switch(long long key){
    switch(key){case 5:case 7:return 4;default:++calls;return 9;}
}
int literal_selected_switch(void){return pure_selected_switch(7);}
'''
KERNEL+='int nested_continue(void){int i,r=0;for(i=0;i<4;++i){switch(1){case 1:switch(i){case 1:continue;default:break;}r+=i;break;}r+=10;}return r;}\n'
KERNEL+='''int dense(int x){int r=0;switch(x){
case 3:r=1;case 4:r+=2;break;case 5:return 5;case 6:return 6;
case 7:return 7;case 8:return 8;case 9:return 9;default:return -1;}return r;}
'''
DRIVER='''extern int calls,input,selectors[2];
int post_dead(void);int post_dead_offset(void);int post_live_case(void);int post_live_after(void);
int once(void);int fall(int);int stacked(int);int wide(unsigned long);int signed_word(int);int signed_wide(long);
int bytes(char);int signed_bytes(signed char);int constants(int);int nested(int,int);int targets(void);
int outer_break(void);int loops(void);int duff(int);int false_loop(int);int false_if(int);int after_return(int);
int no_case(void);int empty_default(int);int bare(int);int scope(int);int infinite(int);int big(int);int nested_continue(void);int dense(int);
int literal_load(void);int literal_fall(void);int literal_break(int);int literal_nested_case(void);int literal_wide(void);
int big_negated(int);int string_switch(int);int literal_selected_switch(void);
int main(void){int i,expected;
 for(i=0;i<5;++i){input=i;calls=0;expected=i==1?11:i==3?33:99;if(once()!=expected||calls!=1)return 1;}
 if(fall(1)!=20||fall(2)!=7||fall(3)!=40||fall(9)!=10)return 2;
 if(stacked(1)!=7||stacked(2)!=7||stacked(3)!=9)return 3;
 if(wide(0UL)!=1||wide(0x10000UL)!=2||wide(0x12345678UL)!=3||wide(0xffff0000UL)!=4||wide(0xffffffffUL)!=5||wide(2UL)!=6)return 4;
 if(signed_word(-32767-1)!=1||signed_word(-1)!=2||signed_word(32767)!=3||signed_word(4)!=4)return 5;
 if(signed_wide(-2147483647L-1L)!=1||signed_wide(-1L)!=2||signed_wide(3L)!=3)return 6;
 if(bytes((char)255)!=2||signed_bytes(-1)!=1||signed_bytes(127)!=2)return 7;
 if(constants(3)!=3||constants(5)!=5||constants(7)!=7||constants(6)!=0)return 8;
 if(nested(1,1)!=10||nested(1,2)!=12||nested(2,1)!=8||nested(3,1)!=4)return 9;
 if(targets()!=61||outer_break()!=6||loops()!=15)return 10;
 if(duff(0)!=7||duff(1)!=6||duff(2)!=4||duff(3)!=0)return 11;
 if(false_loop(1)!=12||false_loop(0)!=0||false_if(1)!=9||false_if(2)!=3)return 12;
 for(i=1;i<=4;++i)if(after_return(i)!=i)return 13;
 calls=0;if(no_case()!=4||calls!=1||bare(3)!=8||bare(0)!=9)return 14;
 if(scope(1)!=7||scope(2)!=2||infinite(1)!=7||infinite(2)!=4)return 15;
 for(i=0;i<=64;++i)if(big(i)!=(i==64?-1:i*3+1))return 16;
 if(nested_continue()!=35)return 17;
 if(dense(-1)!=-1||dense(2)!=-1||dense(3)!=3||dense(4)!=2||dense(10)!=-1)return 18;
 for(i=5;i<=9;++i)if(dense(i)!=i)return 19;
 selectors[0]=0;selectors[1]=41;
 if(post_dead()!=7||post_dead_offset()!=9||post_live_case()!=41||post_live_after()!=41)return 20;
 selectors[0]=41;selectors[1]=0;
 if(post_dead()!=9||post_dead_offset()!=7||post_live_case()!=9||post_live_after()!=9)return 21;
 selectors[1]=52;calls=0;
 if(literal_load()!=52||literal_fall()!=17||calls!=0)return 22;
 if(literal_break(1)!=4||literal_break(0)!=11||literal_nested_case()!=9||literal_wide()!=9)return 23;
 calls=0;if(empty_default(0)!=0||empty_default(1)!=1)return 24;
 for(i=-65;i<=0;++i){
  input=i;calls=0;
  if(big_negated(9)!=(i>=-64&&i<0?10-3*i:-1)||calls!=1)return 25;
 }
 if(string_switch(6)!='a'||string_switch(7)!='b'||string_switch(8)!='b'||
    string_switch(9)!='d'||string_switch(10)!='f'||string_switch(11)!='a')return 26;
 calls=0;if(literal_selected_switch()!=4||calls)return 27;
 return 0;}
'''
BAD={
 'float':('int main(void){switch(1.5f){case 1:break;}return 0;}','integer expression'),
 'pointer':('int main(void){int *p;switch(p){}return 0;}','integer expression'),
 'void':('void f(void);int main(void){switch(f()){}return 0;}','integer expression'),
 'aggregate':('struct S {int x;};int main(void){struct S a;switch(a){}return 0;}','integer expression'),
 'case_outside':('int main(void){case 1:return 0;}','outside switch'),
 'default_outside':('int main(void){default:return 0;}','outside switch'),
 'duplicate':('int main(void){switch(1){case 2:break;case 2:break;}return 0;}','duplicate case'),
 'converted_duplicate':('int main(void){switch(1){case -1:break;case 65535U:break;}return 0;}','duplicate case'),
 'unsigned_duplicate':('int main(void){unsigned int x;switch(x){case -1:break;case 65535U:break;}return 0;}','duplicate case'),
 'wide_duplicate':('int main(void){unsigned long x;switch(x){case -1L:break;case 0xffffffffUL:break;}return 0;}','duplicate case'),
 'default_duplicate':('int main(void){switch(1){default:;default:;}return 0;}','duplicate default'),
 'runtime_case':('int main(void){int x;switch(1){case x:break;}return 0;}','case label requires'),
 'call_case':('int f(void);int main(void){switch(1){case f():break;}return 0;}','case label requires'),
 'assignment_case':('int main(void){int x;switch(1){case x=1:break;}return 0;}','case label requires'),
 'float_case':('int main(void){switch(1){case 1.0f:break;}return 0;}','case label requires'),
 'missing_colon':('int main(void){switch(1){case 1 break;}return 0;}',"':' after case/default"),
 'continue':('int main(void){switch(1){case 1:continue;}return 0;}','continue outside loop'),
 'break':('int main(void){break;return 0;}','break outside loop'),
 'unreachable_break':('int main(void){return 0;break;}','break outside loop'),
}


def build_interrupts():
 home=OUT/'interrupts';home.mkdir(exist_ok=True);original=support.OUT;support.OUT=home
 driver=home/'driver.s';driver.write_text(interrupts.driver(15,0))
 support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',driver.with_suffix('.o'),driver])
 source='unsigned int counts[4],irq_status;unsigned long wide=0x12345678UL;int test_driver(void);\n'
 for i,(kind,name) in enumerate(zip(interrupts.KINDS,interrupts.NAMES)):
  source+=f'__interrupt({kind}) void {name}(void){{'
  if kind=='irq':source+='irq_status=*(unsigned char * __far)0x4211UL;*(unsigned char * __far)0x4200UL=0;'
  source+=f'switch(counts[{i}]&1){{case 0:case 1:counts[{i}]+=2;break;'
  source+=''.join(f'case {j}:counts[{i}]=99;break;' for j in range(2,20))
  source+=f'default:counts[{i}]=99;}}'
  source+=f'switch(wide){{case 0x12345678UL:counts[{i}]-=1;break;default:counts[{i}]=99;}}'
  if kind=='nmi':source+='*(unsigned int * __far)0x4305UL=2;*(unsigned char * __far)0x420bUL=1;'
  source+='}\n'
 source+='int main(void){return test_driver();}'
 try:support.compile_case('handlers-15-clock-0',source,extra_objects=[driver.with_suffix('.o'),ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
 finally:support.OUT=original


def worker(region):
 interrupts.OUT=OUT/'interrupts';interrupts.worker(region,15,0)


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--region');args=parser.parse_args()
 if args.region:worker(args.region);return
 OUT.mkdir(parents=True,exist_ok=True);support.OUT=OUT
 kernel=OUT/'kernel.c';kernel.write_text(KERNEL)
 support.run([ROOT/'build/zicc.exe',kernel,'-o',kernel.with_suffix('.s')])
 assembly=kernel.with_suffix('.s').read_text()
 assert '; split dense word switch' in assembly
 big=assembly.split('_big:\n',1)[1].split('__size_big',1)[0]
 assert '; constant dense switch lookup table (64 entries)' in big,big
 big_negated=assembly.split('_big_negated:\n',1)[1].split('__size_big_negated',1)[0]
 assert '; bounded dense word switch' in big_negated and 'eor #$FFFF' not in big_negated,big_negated
 string_switch=assembly.split('_string_switch:\n',1)[1].split('__size_string_switch',1)[0]
 assert '; constant dense switch lookup table (4 entries)' in string_switch,string_switch
 literal_switch=assembly.split('_literal_selected_switch:\n',1)[1].split('__size_literal_selected_switch',1)[0]
 assert 'jsr' not in literal_switch and '#$0004' in literal_switch,literal_switch
 for name,offset in [('post_dead',0),('post_dead_offset',2)]:
  body=assembly.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert f'lda a:.loword(_selectors+${offset:04X})' in body,body
 literal=assembly.split('_literal_load:\n',1)[1].split('__size_literal_load',1)[0]
 assert 'lda a:.loword(_selectors+$0002)' in literal and 'jsr' not in literal,literal
 for name in ('literal_break','literal_nested_case'):
  body=assembly.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert '; linear switch dispatch:' not in body,body
 support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',kernel.with_suffix('.o'),kernel.with_suffix('.s')])
 _,rom,labels=support.compile_case('driver',DRIVER,extra_objects=[kernel.with_suffix('.o'),ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
 log=support.emulate(rom,labels,0)
 host=OUT/'host.exe';support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/J','/O2','/Fo'+str(OUT)+'/', '/Fe'+str(host),kernel,OUT/'driver.c'])
 support.run([host])
 for name,(source,message) in BAD.items():
  path=OUT/(name+'.c');path.write_text(source)
  p=subprocess.run([str(ROOT/'build/zicc.exe'),str(path),'-o',str(path.with_suffix('.s'))],capture_output=True,text=True)
  assert p.returncode and message in p.stderr,(name,p.stderr)
  assert re.search(r':\d+:\d+: error:',p.stderr),p.stderr
 build_interrupts()
 for region in ('ntsc','pal'):
  support.run([sys.executable,__file__,'--region',region],timeout=35)
  print('PASS switch interrupts '+region,flush=True)
 (OUT/'results.json').write_text(json.dumps(dict(runtime=log,rejected=list(BAD),compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest(),rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest()),indent=2)+'\n')
 print(f'PASS: separate-TU MSVC/Mesen switch semantics, 16/32-bit dispatch, fallthrough, nested/Duff labels, break/continue; {len(BAD)} diagnostics; NTSC/PAL all four handlers')


if __name__=='__main__':main()
