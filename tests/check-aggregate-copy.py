"""Check that structure assignments copy the right bytes, even when an interrupt pauses the copy."""
import os
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'aggregate-copy-check'
spec=importlib.util.spec_from_file_location('copy_support',ROOT/'tests/check-compiler.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
spec=importlib.util.spec_from_file_location('copy_interrupts',ROOT/'tests/check-interrupts.py')
interrupts=importlib.util.module_from_spec(spec);spec.loader.exec_module(interrupts)

SOURCE='''struct Small {short x;};
struct Six {char bytes[5];};
struct Eight {short a[4];};
struct Triple {short a,b,c;};
struct Ten {short a[5];};
union Value {long number;char bytes[7];};
struct Record {char tag;short values[2][3];union Value variant;};
struct Small a2,b2;
struct Pair {int first,second;};
struct Pair pair,inputs[2];
int overwritten_member(void){int *p;pair.first=12345;p=&pair.first;pair=inputs[1];return *p;}
int observed_member(int n){pair.first=n;pair=pair;return pair.first;}
struct Six a6,b6;
struct Eight a8,b8;
const struct Eight argument_image={{-3,5,11,-13}};
struct Large {char bytes[40];};
struct Large a40,b40;
__noinline int receive_large(struct Large first,int seed,struct Large second,int tail){
 int i;
 if(tail!=19)return 1;
 for(i=0;i<40;++i)if(first.bytes[i]!=seed+i||second.bytes[i]!=i+1)return 1;
 return 0;
}
__noinline int send_large(int seed){
 struct Large local;int i;
 for(i=0;i<40;++i)local.bytes[i]=seed+i;
 return receive_large(local,seed,b40,19);
}
struct Record a,b,c;
const struct Record image={7,{{1,2,3},{4,5,6}},{0x12345678L}};
__dpage struct Small da,db;
int destination_calls,source_calls,recursive_calls;
struct Record *chosen;
short marker;
int address_checks;
int copy_address_calls;
struct Pair *pair_address(struct Pair *p){++copy_address_calls;return p;}
__noinline void copy_to_pointer(struct Pair *out,struct Pair value){
 *pair_address(out)=value;
}
__noinline void copy_from_pointer(struct Pair *in){
 pair=*pair_address(in);
}
__noinline int copy_to_pointer_result(struct Pair *out,struct Pair value){
 return (*pair_address(out)=value).second;
}
__noinline int copy_from_pointer_result(struct Pair *in){
 return (pair=*pair_address(in)).first;
}
struct Pair *pair_target;
__noinline struct Pair make_pair(int value){
 struct Pair result={value,-47};
 pair_target=&inputs[1];
 return result;
}
__noinline int copy_pair_call(int value){
 return (*pair_address(pair_target)=make_pair(value)).second;
}
struct Small make_small(short value){
 short *p=&marker,**unused=&p;
 struct Small result={value};
 if(p!=&marker)++address_checks;
 if(p==&marker)result.x+=2;
 return result;
}
int copy_arguments(struct Small small,struct Pair value){
 struct Small local;
 local=small;pair=value;
 return local.x+pair.first+pair.second;
}
int send_arguments(int seed){
 struct Small local;
 local.x=seed;
 return copy_arguments(local,inputs[1]);
}
int receive_words(struct Triple three,struct Eight four){
 return three.a+2*three.b+3*three.c+four.a[0]+2*four.a[1]+3*four.a[2]+4*four.a[3];
}
int forward_words(struct Triple three){return receive_words(three,argument_image);}
int send_words(int seed){struct Triple three={seed,-7,9};return forward_words(three);}
__noinline int take_ten(int before,struct Ten value,int after){
 int result=before+value.a[0]+2*value.a[1]+3*value.a[2]+4*value.a[3]+5*value.a[4]+6*after;
 value.a[4]=-99;
 return result+value.a[4];
}
__noinline int send_ten(int seed){
 struct Ten local={{seed,-7,9,-11,13}};
 return take_ten(3,local,17);
}
int ten_address_calls;
__noinline struct Ten *ten_address(struct Ten *p){++ten_address_calls;return p;}
__noinline int send_ten_indirect(struct Ten *p){return take_ten(3,*ten_address(p),17);}
__noinline void copy_next(struct Pair *p,struct Pair value){*++p=value;}
__noinline void copy_current(struct Pair *p,struct Pair value){*p++=value;}
__noinline struct Pair *copy_next_live(struct Pair *p,struct Pair value){*++p=value;return p;}
__noinline int copy_indexed_step(struct Pair value){
 struct Pair local[1];int i;
 for(i=0;i<1;local[i++]=value){}
 return i==1&&local[0].first==value.first&&local[0].second==value.second;
}
__noinline int copy_descending_step(struct Pair *out,struct Pair value,int end){
 int i;
 for(i=2;i>=end;out[i--]=value){}
 return i;
}
void copy_next_argument(struct Pair *p,struct Pair value){*++p=value;}
void copy_pointer_argument(struct Pair value,struct Pair *p){*p=value;}
struct Pair fixed_pairs[3],fixed_value;
union ShiftedPair {struct Pair value;struct {int pad;struct Pair value;} shifted;} shifted_pair;
__noinline void copy_fixed_next(void){copy_next_argument(fixed_pairs,fixed_value);}
__noinline void copy_fixed_exact(void){copy_pointer_argument(fixed_value,&fixed_pairs[2]);}
__noinline void copy_fixed_overlap(void){copy_pointer_argument(shifted_pair.value,&shifted_pair.shifted.value);}
__noinline void copy_effectful_pointer(void){copy_next_argument(pair_address(fixed_pairs),fixed_value);}
__noinline int receive_permuted(int a,int b,int c,struct Triple three){
 return a+2*b+3*c+three.a+4*three.b+5*three.c;
}
int forward_permuted(struct Triple three,int a,int b,int c){return receive_permuted(a,b,c,three);}
int forward_calls;
__noinline int effect_arg(void){++forward_calls;return 5;}
int send_permuted(int seed){struct Triple three={seed,-7,9};return forward_permuted(three,3,5,11);}
int send_effectful(int seed){struct Triple three={seed,-7,9};return forward_permuted(three,3,effect_arg(),11);}
volatile int projected_result;
__noinline void take_projected(int b,int extra){projected_result=2*b+extra;}
void project_call(struct Triple value,int extra){take_projected(value.b,extra);}
__noinline void use_projection(int seed){
 struct Triple record={seed,-7,9};
 project_call(record,seed);
}
__noinline void use_effectful_projection(int seed){
 struct Triple record={seed,-7,9};
 project_call(record,effect_arg());
}
struct Record *destination(void){++destination_calls;return chosen;}
const struct Record * __far source(void){++source_calls;chosen=&b;return &image;}
void copy(struct Record *d,const struct Record * __far s){*d=*s;}
void discarded(struct Large *d,struct Large *s){*d=*s;}
int used(struct Large *d,struct Large *s){return (*d=*s).bytes[39];}
void discarded_step(struct Large *d,struct Large *s){int i;for(i=0;i<1;*d=*s)++i;}
int mutate(void){a.values[0][0]=99;return 0;}
int recursive(int n){struct Record local;local=image;++recursive_calls;
 if(n&&recursive(n-1))return 1;
 return local.tag!=7||local.values[1][2]!=6||local.variant.number!=0x12345678L;}
int main(void){struct Record local,others[2];union Value u,v,w;int i,j;
 struct Ten argument={{19,-7,9,-11,13}};
 struct Pair steps[3]={{0,0},{0,0},{0,0}},words={41,-13};
 if(send_ten(19)!=59||send_ten_indirect(&argument)!=59||ten_address_calls!=1||argument.a[4]!=13)return 35;
 copy_next(steps,words);
 if(steps[0].first||steps[1].first!=41||steps[1].second!=-13||steps[2].first)return 36;
 copy_current(steps,words);
 if(steps[0].first!=41||steps[0].second!=-13)return 37;
 if(copy_next_live(steps+1,words)!=steps+2||steps[2].first!=41||steps[2].second!=-13)return 38;
 if(!copy_indexed_step(words))return 42;
 steps[1].first=0;steps[2].first=0;
 if(copy_descending_step(steps,words,1)!=0||steps[0].first!=41||
    steps[1].first!=41||steps[1].second!=-13||steps[2].first!=41||steps[2].second!=-13)return 43;
 fixed_value=words;copy_fixed_next();copy_fixed_exact();
 if(fixed_pairs[0].first||fixed_pairs[1].first!=41||fixed_pairs[1].second!=-13||
    fixed_pairs[2].first!=41||fixed_pairs[2].second!=-13)return 39;
 shifted_pair.value=words;copy_fixed_overlap();
 if(shifted_pair.shifted.value.first!=41||shifted_pair.shifted.value.second!=-13)return 40;
 fixed_pairs[1].first=0;copy_effectful_pointer();
 if(copy_address_calls!=1||fixed_pairs[1].first!=41||fixed_pairs[1].second!=-13)return 41;
 copy_address_calls=0;
 b2.x=29;a2=b2;if(a2.x!=29)return 1;
 inputs[1].first=41;inputs[1].second=-13;
 if(overwritten_member()!=41||pair.second!=-13)return 32;
 if(observed_member(19)!=19||pair.first!=19)return 33;
 if(send_arguments(7)!=35||pair.first!=41||pair.second!=-13)return 22;
 if(send_words(19)!=20)return 23;
 if(send_permuted(19)!=82||send_effectful(19)!=82||forward_calls!=1)return 34;
 use_projection(19);if(projected_result!=5)return 44;
 use_effectful_projection(19);if(projected_result!=-9||forward_calls!=2)return 45;
 a2=make_small(-7);if(a2.x!=-5||address_checks)return 24;
 inputs[1].first=0;inputs[1].second=0;
 copy_to_pointer(&inputs[1],pair);
 if(inputs[1].first!=41||inputs[1].second!=-13)return 25;
 pair.first=0;pair.second=0;
 copy_from_pointer(&inputs[1]);
 if(copy_address_calls!=2||pair.first!=41||pair.second!=-13)return 26;
 inputs[1].first=18;copy_from_pointer(&inputs[1]);
 if(copy_address_calls!=3||pair.first!=18||pair.second!=-13)return 27;
 inputs[0].first=0;inputs[0].second=0;
 if(copy_to_pointer_result(&inputs[0],pair)!=-13||inputs[0].first!=18||
    inputs[0].second!=-13||copy_address_calls!=4)return 28;
 inputs[0].first=32;inputs[0].second=16;
 if(copy_from_pointer_result(&inputs[0])!=32||pair.first!=32||
    pair.second!=16||copy_address_calls!=5)return 29;
 pair_target=&inputs[0];
 if(copy_pair_call(19)!=-47||copy_address_calls!=6||pair_target!=&inputs[1])return 30;
#ifdef __ZICC__
 if(inputs[0].first!=19||inputs[0].second!=-47||inputs[1].first!=18)return 31;
#endif
 for(i=0;i<5;++i)b6.bytes[i]=i+3;a6=b6;if(a6.bytes[4]!=7)return 2;
 for(i=0;i<4;++i)b8.a[i]=i+10;a8=b8;if(a8.a[3]!=13)return 3;
 for(i=0;i<40;++i)b40.bytes[i]=i+1;a40=b40;if(a40.bytes[39]!=40)return 4;
 if(send_large(11))return 32;
 a40.bytes[39]=0;discarded(&a40,&b40);if(a40.bytes[39]!=40)return 18;
 a40.bytes[39]=0;if(used(&a40,&b40)!=40||a40.bytes[39]!=40)return 20;
 a40.bytes[39]=0;discarded_step(&a40,&b40);if(a40.bytes[39]!=40)return 21;
 a=image;b=a;c=b;a=a;
 if(a.tag!=7||b.values[1][2]!=6||c.variant.number!=0x12345678L)return 5;
 chosen=&a;b.tag=99;*destination()=*source();
 if(destination_calls!=1||source_calls!=1||a.tag!=7||chosen!=&b)return 6;
#ifdef __ZICC__
 if(b.tag!=99)return 6;
#endif
 c=b=a=image;local=c;others[0]=local;others[1]=others[0];
 if((a=image).values[1][2]!=6||(a=image).variant.bytes[0]!=0x78)return 7;
 if(others[1].tag!=7||local.values[0][2]!=3)return 8;
 copy(&local,&image);if(local.variant.number!=0x12345678L)return 9;
 i=0;j=1;others[i++]=others[j++];if(i!=1||j!=2||others[0].tag!=7)return 15;
 {struct P {const short *p;};struct P x,y;y.p=&b2.x;x=y;if(x.p!=&b2.x)return 16;}
#ifdef __ZICC__
 {char *p=(char*)&local;char *q=(char*)&others[0];for(i=0;i<sizeof(local);++i)p[i]=(char)(i+23);
 others[0]=local;for(i=0;i<sizeof(local);++i)if(q[i]!=(char)(i+23))return 14;}
#endif
 for(i=0;i<7;++i)u.bytes[i]=i+11;w=v=u;
 if(v.bytes[6]!=17||w.bytes[0]!=11)return 10;
 db.x=123;da=db;if(da.x!=123)return 11;
 if(recursive(5)||recursive_calls!=6)return 12;
 for(i=0;i<2;++i)for(j=0;j<3;++j)if(a.values[i][j]!=i*3+j+1)return 13;
 #ifdef __ZICC__
 if((a=image).values[0][mutate()]!=1)return 17;
#else
 {struct Record snapshot;snapshot=(a=image);if(snapshot.values[0][mutate()]!=1)return 17;}
#endif
 return 0;}
'''
BAD={
 'identity':('struct A {int x;};struct B {int x;};int main(void){struct A a;struct B b;a=b;return 0;}','same type'),
 'const':('struct S {int x;};const struct S a;struct S b;int main(void){a=b;return 0;}','modifiable lvalue'),
 'nested_const':('struct I {const int x;};struct S {struct I a[2];};struct S a,b;int main(void){a=b;return 0;}','modifiable lvalue'),
 'union_const':('union U {const int x;long y;};union U a,b;int main(void){a=b;return 0;}','modifiable lvalue'),
 'const_pointer':('typedef int *P;struct S {const P p;};struct S a,b;int main(void){a=b;return 0;}','modifiable lvalue'),
 'result_address':('struct S {int x;};struct S a,b;int main(void){&(a=b);return 0;}','address-of'),
 'member_address':('struct S {int x;};struct S a,b;int main(void){&(a=b).x;return 0;}','address-of'),
 'result_store':('struct S {int x;};struct S a,b,c;int main(void){(a=b)=c;return 0;}','modifiable lvalue'),
 'member_store':('struct S {int x;};struct S a,b;int main(void){(a=b).x=7;return 0;}','writable scalar'),
 'array_store':('struct S {int x;};struct S a[2],b[2];int main(void){a=b;return 0;}','writable scalar'),
 'condition':('struct S {int x;};struct S a,b;int main(void){if(a=b)return 1;return 0;}','aggregate condition'),
 'initializer':('struct S {int x;};struct T {int x;};int main(void){struct T a;struct S b=a;return 0;}','incompatible aggregate initializer'),
}


def compile_case(name,source,disabled=False,extra_objects=()):
 original=support.run
 def compile_override(command,*args,**kw):
  if Path(command[0]).name=='zicc.exe' and disabled:command=[*command,'--no-copy-selection']
  return original(command,*args,**kw)
 support.run=compile_override
 try:return support.compile_case(name,source,extra_objects=extra_objects)
 finally:support.run=original


def handlers_source(dma):
 text='''struct Tiny {short x;};struct Medium {char bytes[5];};struct Big {char bytes[40];};
struct Tiny tiny,ts;struct Medium medium,ms;struct Big big,bs;
unsigned int counts[4],irq_status;
int test_driver(void);
'''
 for i,(kind,name) in enumerate(zip(interrupts.KINDS,interrupts.NAMES)):
  text+=f'__interrupt({kind}) void {name}(void){{'
  if kind=='irq':text+='irq_status=*(unsigned char * __far)0x4211UL;*(unsigned char * __far)0x4200UL=0;'
  text+=f'tiny=ts;medium=ms;big=bs;counts[{i}]++;'
  if kind=='nmi' and dma:text+='*(unsigned int * __far)0x4305UL=2;*(unsigned char * __far)0x420bUL=1;'
  text+='}\n'
 return text


def build_interrupts():
 home=OUT/'interrupts';home.mkdir(exist_ok=True)
 driver=home/'driver.s';driver.write_text(interrupts.driver(15,0))
 support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',driver.with_suffix('.o'),driver])
 original=support.OUT;support.OUT=home
 try:
  source=handlers_source(True)+'''int main(void){int i;ts.x=77;for(i=0;i<5;++i)ms.bytes[i]=i+1;
for(i=0;i<40;++i)bs.bytes[i]=i+10;
test_driver();if(tiny.x!=77||medium.bytes[4]!=5||big.bytes[39]!=49)return 1;return 0;}'''
  support.compile_case('handlers-15-clock-0',source,extra_objects=[driver.with_suffix('.o'),ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
  foreground=handlers_source(False)+'''struct Huge {char bytes[1024];};struct Huge back,front;
int main(void){int i;for(i=0;i<1024;++i)back.bytes[i]=(char)(i*13+1);
*(unsigned char * __far)0x4210UL;*(unsigned char * __far)0x4200UL=0x80;
for(i=0;i<100;++i)front=back;
*(unsigned char * __far)0x4200UL=0;
for(i=0;i<1024;++i)if(front.bytes[i]!=back.bytes[i])return 1;
if(!counts[0])return 2;return 0;}'''
  for disabled in (False,True):compile_case('foreground-'+str(int(disabled)),foreground,disabled,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
 finally:support.OUT=original


def worker(region,mode):
 home=OUT/'interrupts'
 if mode=='handlers':
  original=interrupts.Core
  class AuditCore(original):
   def load(self,rom,path,script):
    script=script.replace("require_value(active==nil,'unexpected nested interrupt');active=", "require_value(active==nil,'unexpected nested interrupt prior='..tostring(active)..' pc='..emu.getState()['cpu.pc']);active=")
    return super().load(rom,path,script)
  interrupts.Core=AuditCore;interrupts.OUT=home
  try:interrupts.worker(region,15,0)
  finally:interrupts.Core=original
  return
 stem=home/mode;sy=interrupts.labels(stem);run_home=home/(region+'-'+mode);run_home.mkdir(exist_ok=True)
 # Record interrupted return PC and require actual interruption within the
 # foreground copy. MVN resumes at its opcode with partially advanced X/Y/A
 data=stem.with_suffix('.sfc').read_bytes()
 mvns=[0x808000+i for i in range(len(data)-2) if data[i:i+3]==bytes.fromhex('547e7e')]
 script=f'''
local active=nil;local resumed=0;local block=0
local function word(a) return emu.read16(((a)&0x1ffff),emu.memType.snesWorkRam,false) end
emu.addMemoryCallback(function()
 assert(active==nil,'nested NMI');local s=emu.getState()
 local target=word(s['cpu.sp']+2)|(emu.read(((s['cpu.sp']+4)&0x1ffff),emu.memType.snesWorkRam,false)<<16)
 active={{state=s,target=target,dp=word(0),scratch={{}}}}
 for i=0x02,0x21 do active.scratch[i]=emu.read(((i)&0x1ffff),emu.memType.snesWorkRam,false) end
end,emu.callbackType.exec,{sy['vblank']&65535},{sy['vblank']&65535})
local function resume()
 if not active then return end
 local s=emu.getState();if s['cpu.pc']~=active.target%65536 then return end
 for _,k in ipairs({{'a','x','y','d','dbr','ps'}}) do assert(s['cpu.'..k]==active.state['cpu.'..k],'NMI preservation '..k) end
 assert(s['cpu.k']==active.target>>16,'NMI program bank')
 assert(s['cpu.sp']==active.state['cpu.sp']+4,'NMI stack')
 assert(word(0)==active.dp,'NMI DP0')
 for i=0x02,0x21 do assert(emu.read(((i)&0x1ffff),emu.memType.snesWorkRam,false)==active.scratch[i],'NMI scratch') end
 resumed=resumed+1
'''
 for pc in mvns:script+=f' if active.target=={pc} then block=block+1 end\n'
 script+=' active=nil\nend\n'
 # A callback at every foreground instruction handles inline-copy resumes too
 script+=f'emu.addMemoryCallback(resume,emu.callbackType.exec,{sy["main"]},{sy["main_exit"]-1 if sy["main_exit"]>sy["main"] else 0x80ffbf})\n'
 script+=f'''emu.addMemoryCallback(function()
 assert(emu.getState()['cpu.a']==0 and emu.getState()['cpu.sp']==1279,'main result/stack')
 assert(resumed>0,'no foreground copy interruptions')
 assert(block>0 or {str(mode.endswith('1')).lower()},'no interruption inside MVN')
 emu.log('PASS {region} {mode} resumed='..resumed..' mvn='..block);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
 core=interrupts.Core(run_home)
 try:
  config=interrupts.SnesConfig();config.Region=1 if region=='ntsc' else 2
  config.Port1.Type=1;config.DisableFrameSkipping=True;config.RamPowerOnState=1
  config.GsuClockSpeed=100;config.BsxCustomDate=-1
  for i in range(8):config.ChannelVolumes[i]=100
  core.bind('SetSnesConfig',None,interrupts.SnesConfig)(config)
  lua=run_home/'check.lua';lua.write_text(script);core.load(stem.with_suffix('.sfc'),lua,script);core.start();core.wait_for('PASS',25)
 finally:core.close_with_log(run_home/'check.log')


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--region');parser.add_argument('--mode');args=parser.parse_args()
 if args.region:worker(args.region,args.mode);return
 OUT.mkdir(parents=True,exist_ok=True);support.OUT=OUT;report={}
 for disabled in (False,True):
  name='reference' if disabled else 'selected'
  path,rom,sy=compile_case(name,SOURCE,disabled,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
  report[name]=support.emulate(rom,sy,0)
  asm=path.with_suffix('.s').read_text()
  if not disabled:
   for mode,size in [('inline',2),('loop',6),('loop',8),('mvn',40)]:assert f'aggregate copy: {mode} {size} bytes' in asm,(mode,size)
   def body(name):return asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
   sender=body('send_large')
   assert sender.count('; outgoing aggregate: mvn 40 bytes')==2,sender
   covered=body('overwritten_member')
   assert '$3039' not in covered and '#.loword(_pair' not in covered,covered
   assert '_address_checks' not in body('make_small'),body('make_small')
   for name in ('copy_to_pointer','copy_from_pointer','copy_to_pointer_result','copy_from_pointer_result'):
    part=body(name)
    assert '; aggregate copy: inline 4 bytes with one fixed address' in part,part
   assert '; aggregate copy: inline 4 bytes from a call result' in body('copy_pair_call'),body('copy_pair_call')
   sender=body('send_arguments');receiver=body('copy_arguments')
   assert re.search(r'lda a:\.loword\(_inputs\+\$0006\)\n    pha\n    lda a:\.loword\(_inputs\+\$0004\)\n    pha',sender),sender
   assert '[__arith_lhs]' not in sender and '    tay\n' not in receiver.split('; aggregate copy:',1)[1],(sender,receiver)
   forwarded=body('forward_words')
   assert '[__arith_lhs]' not in forwarded and 'lda f:_argument_image+$0006' in forwarded,forwarded
   for name in ('send_ten','send_ten_indirect'):
    part=body(name).split('jsr .loword(_take_ten)',1)[0]
    pushes = re.findall(r'^    (?:pha$|pea )',part,re.M)
    assert len(pushes)>=5 and '[__arith_lhs]' not in part,part
   for name in ('copy_next','copy_current'):
    part=body(name)
    assert '    sta 1,s' not in part,part
   indexed=body('copy_indexed_step')
   assert 'loop lowering:' not in indexed and '; aggregate copy: inline 4 bytes' in indexed,indexed
   assert '.loword(_copy_next_argument)' not in body('copy_fixed_next'),body('copy_fixed_next')
   assert '.loword(_copy_pointer_argument)' not in body('copy_fixed_exact'),body('copy_fixed_exact')
   assert '.loword(_copy_pointer_argument)' in body('copy_fixed_overlap'),body('copy_fixed_overlap')
   assert '.loword(_copy_next_argument)' in body('copy_effectful_pointer'),body('copy_effectful_pointer')
   assert '.loword(_receive_permuted)' in body('send_permuted'),body('send_permuted')
   assert '.loword(_forward_permuted)' not in body('send_permuted'),body('send_permuted')
   assert '.loword(_forward_permuted)' in body('send_effectful'),body('send_effectful')
   projected=body('use_projection')
   assert '.loword(_take_projected)' in projected and '.loword(_project_call)' not in projected,projected
   assert '.loword(_project_call)' in body('use_effectful_projection'),body('use_effectful_projection')
   for name in ('discarded','discarded_step'):
    part=body(name).split('; aggregate copy:',1)[1]
    assert '    pha\n' not in part and '    pla\n' not in part,part
   assert '    phy\n    pha\n    tay\n' in body('used'),body('used')
  else:assert 'aggregate copy: mvn' not in asm and 'aggregate copy: loop' not in asm and 'outgoing aggregate: mvn' not in asm
 host=OUT/'host.exe';support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/J','/D__dpage=','/D__noinline=__declspec(noinline)','/O2','/Fo'+str(OUT)+'/', '/Fe'+str(host),OUT/'selected.c'])
 support.run([host])
 for name,(source,message) in BAD.items():
  path=OUT/(name+'.c');path.write_text(source)
  p=subprocess.run([str(ROOT/'build/zicc.exe'),str(path),'-o',str(path.with_suffix('.s'))],capture_output=True,text=True)
  assert p.returncode and message in p.stderr,(name,p.stderr)
 build_interrupts()
 for region in ('ntsc','pal'):
  for mode in ('handlers','foreground-0','foreground-1'):
   support.run([sys.executable,__file__,'--region',region,'--mode',mode],timeout=45)
   print('PASS aggregate interrupts '+region+' '+mode,flush=True)
 (OUT/'results.json').write_text(json.dumps(dict(runtime=report,rejected=list(BAD),compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest()),indent=2)+'\n')
 print(f'PASS: selected/reference/MSVC aggregate semantics, three copy forms, {len(BAD)} diagnostics; NTSC/PAL all four handlers and interrupted foreground copies')


if __name__=='__main__':main()
