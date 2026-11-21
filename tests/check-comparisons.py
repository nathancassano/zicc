"""Check the flags from word comparisons, including overflow, and use the result in expressions and branches."""
import os
import importlib.util,json,re,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'comparison-check'
spec=importlib.util.spec_from_file_location('support',Path(__file__).with_name('check-compiler.py'));support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)

def mask(a,b):return int(a==b)|(int(a!=b)<<1)|(int(a<b)<<2)|(int(a<=b)<<3)|(int(a>b)<<4)|(int(a>=b)<<5)
def body(a,b):return f'({a}=={b})|(({a}!={b})<<1)|(({a}<{b})<<2)|(({a}<={b})<<3)|(({a}>{b})<<4)|(({a}>={b})<<5)'

def main():
 OUT.mkdir(parents=True, exist_ok=True);support.OUT=OUT;calls=[];expected=[]
 signed=[-32768,-32767,-1,0,1,9,32767];unsigned=[0,1,9,32767,32768,65535]
 for a in signed:
  for b in signed:calls.append(f'signed_mask((short){a},(short){b})');expected.append(mask(a,b))
 for a in unsigned:
  for b in unsigned:calls.append(f'unsigned_mask((unsigned short){a}U,(unsigned short){b}U)');expected.append(mask(a,b))
 for a in [*signed,8]:
  calls.append(f'constant_mask((short){a})');expected.append(mask(a,9))
  calls.append(f'memory_mask((short){a})');expected.append(mask(a,9))
  calls.append(f'call_mask((short){a},(short)-1)');expected.append(mask(a,-1))
 for a in signed:
  for bound,name in [(-1,'minus'),(0,'zero'),(1,'plus')]:
   calls.append(f'{name}_left((short){a})');expected.append(mask(bound,a))
   calls.append(f'{name}_right((short){a})');expected.append(mask(a,bound))
 for a,b in [(255,128),(0,255),(128,128)]:calls.append(f'byte_mask({a},{b})');expected.append(mask(a,b))
 for a in [-32768,-32767,-6,-5,0,8,9,32767]:
  calls.append(f'signed_range((short){a})');expected.append(int(-5<=a<9))
  calls.append(f'wide_range((short){a})');expected.append(int(-32768<a<=32767))
  calls.append(f'mixed_range((short){a})');expected.append(int(0<=a<5))
 for a in [0,1,32767,32768,65534,65535]:
  calls.append(f'unsigned_range((unsigned short){a}U)');expected.append(7 if a>32767 else 0)
 for a in [-128,-104,-1,0,127]:
  calls.append(f'equal_byte_call((signed char){a})');expected.append(int(a==-104))
  calls.append(f'unequal_byte_call((signed char){a})');expected.append(int(a!=-104))
  calls.append(f'outside_byte_call((signed char){a})');expected.append(0)
 for a in [0,1,32767,65534,65535]:
  calls.append(f'word_post_result({a}U)');expected.append(3 if a==65535 else 0)
 longs=[-2147483648,-65536,-1,0,1,65535,65536,2147483647]
 ulongs=[0,1,65535,65536,2147483647,2147483648,4294967295]
 for name,values,suffix in [('long_mask',longs,'L'),('ulong_mask',ulongs,'UL')]:
  for a in values:
   for b in values:
    calls.append(f'{name}({a}{suffix},{b}{suffix})');expected.append(mask(a,b))
 for a in longs:
  calls.append(f'constant_left({a}L)');expected.append(mask(-65536,a))
  calls.append(f'constant_right({a}L)');expected.append(mask(a,65536))
  for b in longs:
   calls.append(f'computed_mask({a}L,{b}L)');expected.append(mask(a,b))
 boundary='\n'.join(f'__noinline int {name}_{side}(short a){{return {body(left,right)};}}'
     for bound,name in [(-1,'minus'),(0,'zero'),(1,'plus')]
     for side,left,right in [('left',f'({bound})','a'),('right','a',f'({bound})')])
 source=f'''unsigned short results[{len(calls)}];short numbers[2];
{boundary}
volatile short signed_guard_input;
__noinline int signed_guard(void){{if(1>signed_guard_input)return 8;return 5;}}
int signed_mask(short a,short b){{return {body('a','b')};}}
int unsigned_mask(unsigned short a,unsigned short b){{return {body('a','b')};}}
int constant_mask(short a){{return {body('a','9')};}}
int memory_mask(short a){{return {body('a','numbers[1]')};}}
int identity(short x){{return x;}}
int call_mask(short a,short b){{return {body('a','identity(b)')};}}
int byte_mask(unsigned char a,unsigned char b){{return {body('a','b')};}}
__noinline int signed_range(short a){{return -5<=a&&a<9;}}
__noinline int wide_range(short a){{return a>(-32767-1)&&a<=32767;}}
__noinline int mixed_range(short a){{return a>=-3&&a<5U;}}
__noinline int unsigned_range(unsigned short a){{if(65535U>=a&&32767U<a)return 7;return 0;}}
__noinline signed char signed_result(signed char a,int b,unsigned long c){{return (signed char)(a+b+(int)c);}}
__noinline int equal_byte_call(signed char a){{return signed_result(a,0,0UL)==-104;}}
__noinline int unequal_byte_call(signed char a){{return -104!=signed_result(a,0,0UL);}}
__noinline int outside_byte_call(signed char a){{return signed_result(a,0,0UL)==152;}}
__noinline int word_post_result(unsigned short seed){{
 unsigned short value=seed;
 int before=value++==65535U;
 int after=value--==0U;
 return value==seed?before+2*after:4;
}}
__noinline int long_mask(long a,long b){{return {body('a','b')};}}
__noinline int ulong_mask(unsigned long a,unsigned long b){{return {body('a','b')};}}
__noinline long long_identity(long x){{return x;}}
__noinline int constant_left(long a){{return {body('(-65536L)','long_identity(a)')};}}
__noinline int constant_right(long a){{return {body('long_identity(a)','65536L')};}}
__noinline int computed_mask(long a,long b){{return {body('long_identity(a)','long_identity(b)')};}}
int main(void){{numbers[1]=9;
 signed_guard_input=-32768;if(signed_guard()!=8)return 1;
 signed_guard_input=0;if(signed_guard()!=8)return 2;
 signed_guard_input=1;if(signed_guard()!=5)return 3;
'''+''.join(f'results[{i}]={call};\n' for i,call in enumerate(calls))+'return 0;}\n'
 path,rom,labels=support.compile_case('word_comparisons',source,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
 constant=path.with_suffix('.s').read_text().split('_constant_mask:\n',1)[1].split('__size_constant_mask',1)[0]
 assert re.search(r'    bmi [^\n]+\n    cmp #\$0009',constant),constant
 asm=(OUT/'word_comparisons.s').read_text()
 guard=asm.split('_signed_guard:\n',1)[1].split('__size_signed_guard',1)[0]
 assert 'sbc ' not in guard and 'bvc ' not in guard and 'lda a:.loword(_signed_guard_input)' in guard,guard
 for name in ('signed_range','wide_range'):
  block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert '; contiguous word range' in block,block
 block=asm.split('_mixed_range:\n',1)[1].split('__size_mixed_range',1)[0]
 assert '; contiguous word range' not in block,block
 for name in ('equal_byte_call','unequal_byte_call'):
  block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert 'cmp #$98\n' in block,block
 for name in ('long_mask','constant_left','constant_right'):
  block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert 'cmp32)' not in block and 'sbc ' in block,block
 block=asm.split('_ulong_mask:\n',1)[1].split('__size_ulong_mask',1)[0]
 assert block.count('compare unsigned long high word first')==4 and 'cmp32)' not in block,block
 block=asm.split('_computed_mask:\n',1)[1].split('__size_computed_mask',1)[0]
 assert block.count('sbc z:__arith_rhs+2')==4 and block.count('eor z:__arith_rhs+2')==2 and 'cmp32)' not in block,block
 lua=OUT/'word-comparisons.lua'
 lua.write_text(f'''local expected={{{','.join(map(str,expected))}}}
emu.addMemoryCallback(function()
 for i=1,#expected do
  local actual=emu.read16((({labels['results']}+(i-1)*2)&0x1ffff),emu.memType.snesWorkRam,false)
  if actual~=expected[i] then error('comparison '..i..': '..actual..' expected '..expected[i]) end
 end
 print('PASS {len(expected)} complete comparison masks')
 emu.stop(0)
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
''',encoding='ascii')
 run=support.run([support.mesen_executable(OUT),'--testRunner','--doNotSaveSettings','--timeout=10',rom,lua]);assert 'PASS' in run.stdout,run.stdout
 wrapper=OUT/'host.c';wrapper.write_text('#include <stdio.h>\n#define main sample_main\n#include "word_comparisons.c"\n#undef main\nint main(void){int i;sample_main();for(i=0;i<'+str(len(calls))+';i++)printf("%u\\n",(unsigned)results[i]);return 0;}\n',encoding='ascii')
 support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/D__noinline=__declspec(noinline)','/O2','/Fo'+str(OUT/'host.obj'),'/Fe'+str(OUT/'host.exe'),wrapper])
 host=support.run([OUT/'host.exe']);assert list(map(int,host.stdout.split()))==expected
 source='int calls;int tick(void){calls++;return 1;}int test(short a,short b){if(a!=b&&tick())return 3;if(a==b||tick())return 4;return 5;}int main(void){int r;r=test(9,9);if(r!=4||calls!=0)return 1;r=test(1,2);if(r!=3||calls!=1)return 2;return 0;}'
 _,r,l=support.compile_case('short_circuit',source,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o']);support.emulate(r,l,0)
 source='''int calls;
__noinline int alternative(void){++calls;return 231;}
__noinline int signed_choice(signed char input){return input<=0?input:alternative();}
__noinline unsigned unsigned_choice(unsigned input){return input==0?alternative():input;}
int main(void){
 if(signed_choice(-128)!=-128||signed_choice(0)!=0||calls!=0)return 1;
 if(signed_choice(127)!=231||calls!=1)return 2;
 if(unsigned_choice(65535U)!=65535U||calls!=1)return 3;
 if(unsigned_choice(0)!=231||calls!=2)return 4;
 return 0;
}'''
 _,r,l=support.compile_case('zero_choice',source);support.emulate(r,l,0)
 source='''unsigned long current;
 __noinline void step_up(void){current+=4096UL;}
 __noinline void step_down(void){current-=4096UL;}
 int main(void){current=0xABCD1000UL;step_up();if(current!=0xABCD2000UL)return 1;
  step_down();if(current!=0xABCD1000UL)return 2;
  current=0xABCDFFFFUL;step_up();if(current!=0xABCE0FFFUL)return 3;
  step_down();if(current!=0xABCDFFFFUL)return 4;
  current=0xFFFFFFFFUL;step_up();if(current!=4095UL)return 5;
  step_down();if(current!=0xFFFFFFFFUL)return 6;
  return 0;}'''
 path,r,l=support.compile_case('long_step',source);support.emulate(r,l,0)
 assembly=path.with_suffix('.s').read_text()
 for name,branch in [('step_up','bcc'),('step_down','bcs')]:
  block=assembly.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert branch+' ' in block and '#$1000' in block,block
 source='''unsigned short pos;unsigned char limit;
__noinline int at_end(void){if(pos==(unsigned short)(limit-1))return 5;return 2;}
__noinline int next_byte(void){if(pos!=(unsigned char)(limit+1))return 7;return 0;}
int main(void){limit=0;pos=65535u;if(at_end()!=5)return 1;limit=4;if(at_end()!=2)return 2;
pos=3;if(at_end()!=5)return 3;
limit=255;pos=0;if(next_byte())return 4;
pos=256;if(next_byte()!=7)return 5;
limit=127;pos=128;if(next_byte())return 6;return 0;}'''
 _,r,l=support.compile_case('computed_equality',source);support.emulate(r,l,0)
 assembly=(OUT/'computed_equality.s').read_text()
 for name in ('at_end','next_byte'):
  comparison=assembly.split('\n_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert 'cmp a:.loword(_pos)' in comparison and '__arith_rhs' not in comparison,comparison
 source='''struct Sample{short spare,word;signed char byte;};
struct Sample live;
__noinline int count_shifts(short seed){struct Sample local;int count=3;local.word=seed;
 while(!(1&local.word)){local.word>>=1;++count;}return count;}
__noinline unsigned advance(short seed,unsigned count){live.word=seed;
 while((live.word&8)!=0){--count;live.word>>=1;}return count;}
__noinline int count_byte_shifts(int seed){struct Sample local;int count=3;local.byte=seed;
 while(!(1&local.byte)){local.byte>>=1;++count;}return count;}
__noinline unsigned advance_byte(short seed,unsigned count){live.byte=seed;
 while((live.byte&8)!=0){--count;live.byte>>=1;}return count;}
int main(void){if(count_shifts(3)!=3||count_shifts(-32767-1)!=18)return 1;
 if(advance(-24,9)!=8||live.word!=-12)return 2;
 if(advance(4,6)!=6||live.word!=4)return 3;
 if(count_byte_shifts(3)!=3||count_byte_shifts(384)!=10)return 4;
 if(advance_byte(-24,9)!=8||live.byte!=-12)return 5;
 if(advance_byte(4,6)!=6||live.byte!=4)return 6;
 return 0;}'''
 for enabled in (False,True):
  flags=[] if enabled else ['--no-register-cursors']
  path,r,l=support.compile_case(f'word_shift_scan_{int(enabled)}',source,flags=flags)
  asm=path.with_suffix('.s').read_text()
  for name,marker in [('count_shifts','; frameless word shift scan'),('advance','; register word shift scan'),
                      ('count_byte_shifts','; frameless word shift scan'),('advance_byte','; register word shift scan')]:
   scan=asm.split('\n_'+name+':\n',1)[1].split('__size_'+name,1)[0]
   assert (marker in scan)==enabled,scan
  support.emulate(r,l,0)
 source='''__noinline int find_power(unsigned n){
 int i,found=-1;
 for(i=0;i<10&&found<0;i++)if((1UL<<i)==n)found=i;
 return found;
}
__noinline int shifted_from(unsigned n){
 int i;
 for(i=8;i<=14;i++){if(n!=(2UL<<i))continue;return i;}
 return -1;
}
__noinline int needs_wide(unsigned n){
 int i;
 for(i=0;i<=16;i++)if((1UL<<i)==n)return i;
 return -1;
}
int main(void){
 if(find_power(1)!=0||find_power(64)!=6||find_power(512)!=9||find_power(1024)!=-1)return 1;
 if(shifted_from(512)!=8||shifted_from(32768U)!=14||shifted_from(256)!=-1)return 2;
 if(needs_wide(0)!=-1||needs_wide(32768U)!=15)return 3;
 return 0;
}'''
 path,r,l=support.compile_case('bounded_word_shift',source,
  extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
 support.emulate(r,l,0)
 asm=path.with_suffix('.s').read_text()
 for name in ('find_power','shifted_from','needs_wide'):
  scan=asm.split('\n_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert ('__shl32)' in scan)==(name=='needs_wide'),scan
 source='''int word;struct Bytes{unsigned char low;signed char high;} bytes;
 struct Words{unsigned short low;short high;} words;
 __noinline int negate_word(void){return !word;}
 __noinline void shift_bytes(void){bytes.low=bytes.low>>1;bytes.high>>=1;}
 __noinline void shift_words(void){words.low=words.low>>1;words.high>>=1;}
 __noinline void shift_cast(void){words.high=(unsigned short)words.high>>1;}
 int main(void){
  word=0;if(negate_word()!=1)return 1;
  word=-32767-1;if(negate_word()!=0)return 2;
  word=1;if(negate_word()!=0)return 3;
  bytes.low=254;bytes.high=-3;shift_bytes();
  if(bytes.low!=127||bytes.high!=-2)return 4;
  words.low=65534U;words.high=-3;shift_words();
  if(words.low!=32767||words.high!=-2)return 5;
  shift_cast();if(words.high!=32767)return 6;
  return 0;
 }'''
 path,r,l=support.compile_case('word_not_byte_shift',source)
 asm=path.with_suffix('.s').read_text()
 assert re.search(r'lda #0\s+cmp a:\.loword\(_word\)\s+rol a',asm),asm
 shift=asm.split('_shift_bytes:\n',1)[1].split('__size_shift_bytes',1)[0]
 assert '    lsr a\n' in shift and '    cmp #$80\n    ror a\n' in shift,shift
 shift=asm.split('_shift_words:\n',1)[1].split('__size_shift_words',1)[0]
 assert re.search(r'lda a:\.loword\(_words\+\$0000\)\n    lsr a\n    sta a:\.loword\(_words\+\$0000\)',shift),shift
 assert '    cmp #$8000\n    ror a\n' in shift,shift
 support.emulate(r,l,0)
 source='''volatile int change;
 __noinline void update(int *a){if(change)a[0]=8;}
 int main(void){int a[2];a[0]=9;update(a);if(a[0]!=9)return 1;return 0;}'''
 _,rom,labels=support.compile_case('frame_immediate',source,flags=['--no-dp-homes','--no-stack-frames'])
 asm=(OUT/'frame_immediate.s').read_text();assert re.search(r'(?:lda|sta) a:\$0001,y\s+(?:;[^\n]*\n\s*)*cmp #\$0009',asm),asm  # reload may be elided
 assert 'jsr .loword(__scmp16)' not in asm
 support.emulate(rom,labels,0)
 source='''volatile unsigned calls;
 struct wide {int tag; unsigned long long value;};
 static struct wide values[2]={{3,0x0123456789abcdefULL},{7,0xfedcba9876543210ULL}};
 __noinline struct wide *pick(int i){++calls;return values+i;}
 __noinline int take(unsigned long long v){return v==0xfedcba9876543210ULL;}
 __noinline int pass_field(int i){return take(pick(i)->value);}
 __noinline int pass_indirect(const unsigned long long *p){return take(*p);}
 __noinline int signed_mask(long long x){
  return (x<-0x1000000000000000LL)+2*(x>=-0x1000000000000000LL)
         +4*(x>-0x1000000000000001LL)+8*(-0x1000000000000001LL>=x);
 }
 __noinline int unsigned_mask(unsigned long long x){
  return (x<0x8000000000000000ULL)+2*(x>=0x8000000000000000ULL)
         +4*(x>0x7fffffffffffffffULL)+8*(0x7fffffffffffffffULL>=x);
 }
 __noinline int return_after_guard(int x,int y,long long a){
  int result=0;
  if(y>0){
   if(a<-0x1000000000000000LL)result=y;
   else result=x;
  }
  return result;
 }
 int main(void){
  if(!pass_field(1)||pass_field(0)||calls!=2)return 1;
  if(!pass_indirect(&values[1].value)||pass_indirect(&values[0].value))return 2;
  if(signed_mask(-0x1000000000000001LL)!=9||signed_mask(-0x1000000000000000LL)!=6||
     signed_mask(-0x0fffffffffffffffLL)!=6||signed_mask(0x7fffffffffffffffLL)!=6)return 3;
  if(unsigned_mask(0x7fffffffffffffffULL)!=9||unsigned_mask(0x8000000000000000ULL)!=6||
     unsigned_mask(0x8000000000000001ULL)!=6||unsigned_mask(0)!=9)return 4;
  if(return_after_guard(-1,3,-0x1000000000000001LL)!=3||
     return_after_guard(-1,3,-0x1000000000000000LL)!=-1||
     return_after_guard(7,0,0)!=0)return 5;
  return 0;
 }'''
 path,rom,labels=support.compile_case('wide_immediate_and_arguments',source,
     extra_objects=[ROOT/'build/integers.o'])
 asm=path.with_suffix('.s').read_text()
 for name in ('signed_mask','unsigned_mask'):
  block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert re.search(r'sbc #\$(?:F000|EFFF|8000|7FFF)',block) and 'sbc #$FFFF' not in block,block
 for name in ('pass_field','pass_indirect'):
  block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  assert re.search(r'lda a:\$0006,x\s+pha',block) and 'sta z:__arith_lhs+6' not in block,block
 support.emulate(rom,labels,0)
 source='''typedef const char * __far Pointer;
const char first[]="first",second[]="second";
Pointer const table[2]={first,second};
__noinline int matches(Pointer p){return table[1]==p && p!=table[0];}
int main(void){return !matches(second)||matches(first);}
'''
 path,rom,labels=support.compile_case('far_table_equality',source)
 asm=path.with_suffix('.s').read_text()
 block=asm.split('_matches:\n',1)[1].split('__size_matches',1)[0]
 assert 'lda f:_table+$0004' in block and 'lda f:_table+$0006' in block and 'cmp32)' not in block,block
 support.emulate(rom,labels,0)
 source='''union FloatBits {unsigned long bits;float value;};
 volatile union FloatBits input;
 __noinline int bounds(float x){return x<20 && -10L<=x;}
 __noinline int rounded(float x){return x==16777217UL;}
 __noinline int zero_mask(void){return (input.value==0)|((0.0f!=input.value)<<1);}
 float left,right,middle;
 __noinline float deferred_subtract(void){return left-(middle+right);}
 __noinline float change_left(void){left=1.0f;return 6.0f;}
 __noinline float after_call(void){return left-change_left();}
 __noinline unsigned fixed_order(float x){
  return (x<20.0f)|((x<=20.0f)<<1)|((x>20.0f)<<2)|((x>=20.0f)<<3)|
         ((-1.00000011920928955078125f<x)<<4)|((-1.00000011920928955078125f<=x)<<5)|
         ((-1.00000011920928955078125f>x)<<6)|((-1.00000011920928955078125f>=x)<<7);
 }
 __noinline int volatile_order(void){return input.value<20.0f;}
 __noinline unsigned fixed_equality(float x){
  return (20.0f==x)|((x!=-1.00000011920928955078125f)<<1);
 }
 __noinline int volatile_equality(void){return input.value==20.0f;}
 @ordered_cases@
 int main(void){
  unsigned i;
  if(!bounds(-10.0f)||!bounds(19.5f)||bounds(-10.5f)||bounds(20.0f))return 1;
  if(!rounded(16777216.0f)||rounded(16777218.0f))return 2;
  input.bits=0;if(zero_mask()!=1)return 3;
  input.bits=0x80000000UL;if(zero_mask()!=1)return 4;
  input.bits=1;if(zero_mask()!=2)return 5;
  input.bits=0x80000001UL;if(zero_mask()!=2)return 6;
  input.bits=0x7f800000UL;if(zero_mask()!=2)return 7;
  input.bits=0x7fc00000UL;if(zero_mask()!=2||bounds(input.value))return 8;
  for(i=0;i<sizeof cases/sizeof cases[0];++i){
   input.bits=cases[i].bits;
   if(fixed_order(input.value)!=cases[i].order||volatile_order()!=(cases[i].order&1))return 9;
   if(fixed_equality(input.value)!=cases[i].equality||volatile_equality()!=(cases[i].equality&1))return 10;
  }
  left=11.0f;middle=2.0f;right=5.0f;
  if(deferred_subtract()!=4.0f||after_call()!=5.0f||left!=1.0f)return 11;
  return 0;
 }
 '''
 def decode(bits):return struct.unpack('>f',bits.to_bytes(4,'big'))[0]
 def order(a,b):return int(a<b)|(int(a<=b)<<1)|(int(a>b)<<2)|(int(a>=b)<<3)
 bits=(0,0x80000000,1,0x80000001,0x419fffff,0x41a00000,0x41a00001,0x41a10000,
       0xbf7fffff,0xbf800000,0xbf800001,0xbf800002,0xbf810000,0x7f800000,0xff800000,
       0x7f800001,0xff800001,0x7fc00000,0xffc00000)
 rows=','.join('{0x%08xUL,%dU,%dU}'%(b,order(decode(b),20.0)|(order(decode(0xbf800001),decode(b))<<4),
                                      int(decode(b)==20.0)|(int(decode(b)!=decode(0xbf800001))<<1))
               for b in bits)
 source=source.replace('@ordered_cases@','static const struct {unsigned long bits;unsigned order,equality;} cases[]={'+rows+'};')
 for disabled in (False,True):
  flags=['--no-strength-reduction'] if disabled else []
  path,rom,labels=support.compile_case(f'binary32_compare_{int(disabled)}',source,flags=flags,
   extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
  asm=path.with_suffix('.s').read_text()
  for name in ('bounds','rounded','zero_mask','fixed_order','volatile_order','fixed_equality','volatile_equality'):
   block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
   assert ('float32)' in block)==(disabled and name in ('bounds','rounded','zero_mask')),block
   uses_helper = '__fcmp32)' in block or '__fcmp32_equal)' in block
   assert uses_helper == (disabled or name in ('volatile_order','volatile_equality')),block
   if name == 'volatile_equality':
    assert '__fcmp32_equal)' in block,block
  block=asm.split('_deferred_subtract:\n',1)[1].split('__size_deferred_subtract',1)[0]
  assert ('    pha\n' in block)==disabled,block
  support.emulate(rom,labels,0)
 source='''struct Sample {float values[2];};
 struct Sample sample={{0.0f,2.5f}};
 __noinline float update(float value){
  float old=value++;
  if(old!=3.5f||value!=4.5f)return -1.0f;
  return --sample.values[1];
 }
 __noinline float step(float value){
  for(;value<3;value++){}
  return value;
 }
 __noinline float indirect(float *value){return (*value)++;}
 int main(void){
  if(update(3.5f)!=1.5f||sample.values[1]!=1.5f)return 1;
  if(step(0.5f)!=3.5f||step(3.0f)!=3.0f)return 2;
  if(indirect(&sample.values[1])!=1.5f||sample.values[1]!=2.5f)return 3;
  return 0;
 }
 '''
 path,rom,labels=support.compile_case('binary32_update',source,
  extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
 asm=path.with_suffix('.s').read_text()
 step=asm.split('_step:\n',1)[1].split('__size_step',1)[0]
 assert '__fadd32)' in step and '    pha\n    tax\n' not in step and '    phx\n' not in step,step
 update=asm.split('_update:\n',1)[1].split('__size_update',1)[0]
 assert 'sta a:.loword(_sample+$0004)' in update,update
 support.emulate(rom,labels,0)
 source='''struct Words {unsigned long x,y;};
 struct Words words={0xffffUL,0x10000UL};
 unsigned long high_word_test;
 __noinline unsigned long high_update(unsigned long value){
  high_word_test=value;
  return high_word_test+=0x10000UL;
 }
 __noinline int below_boundary(long value){return value<-0x60000000L;}
 __noinline int above_top_word(unsigned long value){return value>0x1234ffffUL;}
 __noinline int update(unsigned long value){
  unsigned long old=value++;
  if(old!=0xffffffffUL||value!=0)return 1;
  if(--value!=0xffffffffUL)return 2;
  words.x++;
  if(words.y--!=0x10000UL||words.y!=0xffffUL||words.x!=0x10000UL)return 3;
  return 0;
 }
 int main(void){
  if(update(0xffffffffUL))return 1;
  if(high_update(0xffff7654UL)!=0x7654UL||high_word_test!=0x7654UL)return 2;
  if(!below_boundary(-2147483647L-1)||!below_boundary(-0x60000001L)||
     below_boundary(-0x60000000L)||below_boundary(0x7fffffffL))return 3;
  if(above_top_word(0x1234ffffUL)||!above_top_word(0x12350000UL))return 4;
  return 0;
 }
 '''
 for disabled in (False,True):
  flags=['--no-strength-reduction'] if disabled else []
  path,rom,labels=support.compile_case(f'long_update_{int(disabled)}',source,flags=flags,
   extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
  asm=path.with_suffix('.s').read_text().split('_update:\n',1)[1].split('__size_update',1)[0]
  if not disabled:
   assert 'sta a:.loword(_words+$0002)' in asm,asm
   assert ('sta a:.loword(_words+$0006)' in asm or
           'dec a:.loword(_words+$0006)' in asm),asm
   high=path.with_suffix('.s').read_text().split('_below_boundary:\n',1)[1].split('__size_below_boundary',1)[0]
   assert 'sbc #$A000' in high and 'sbc #$0000' not in high,high
  support.emulate(rom,labels,0)
 source='''int first,second;
 volatile unsigned effects;
 __noinline unsigned next_mask(void){return ++effects;}
 __noinline int disjoint(void){
  int left=first&1,right=second&2;
  if((signed char)(-2|(left&right))==(signed char)254)return 4;
  return 7;
 }
 __noinline int effectful(void){return (next_mask()&1)&(next_mask()&2);}
 __noinline int switched_mask(int index){
  int mask=255;
  switch(index){case 1: mask^=1;break;default:break;}
  return mask|(first&127);
 }
 __noinline int signed_mask_cast(int value){return (signed char)(value|0x80);}
 __noinline int positive_mask_cast(int value){return (signed char)(value&0xff7f);}
 __noinline int signed_truth_cast(int value){return (signed char)(0x99^(value!=0));}
 int main(void){
  first=-1;second=-1;
  if(disjoint()!=4)return 1;
  if(effectful()!=0||effects!=2)return 2;
  if(signed_mask_cast(0x1242)!=-62||signed_mask_cast(0x17f)!=-1)return 3;
  if(positive_mask_cast(-1)!=127||positive_mask_cast(0xff80)!=0)return 4;
  if(signed_truth_cast(0)!=-103||signed_truth_cast(1)!=-104)return 5;
  first=0;
  if(switched_mask(0)!=255||switched_mask(1)!=254)return 6;
  return 0;
 }
 '''
 for disabled in (False,True):
  flags=['--no-strength-reduction'] if disabled else []
  path,rom,labels=support.compile_case(f'known_mask_{int(disabled)}',source,flags=flags)
  asm=path.with_suffix('.s').read_text()
  disjoint=asm.split('_disjoint:\n',1)[1].split('__size_disjoint',1)[0]
  assert bool(re.search(r'    (?:cmp|ora) ',disjoint))==disabled,disjoint
  for name in ('signed_mask_cast','positive_mask_cast','signed_truth_cast'):
   block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
   assert ('cmp #$0080' in block)==disabled,block
  support.emulate(rom,labels,0)
 source='''unsigned source=0xb4;
 unsigned char byte=0xaf;
 volatile unsigned touched,device;
 __noinline unsigned choose(void){return touched++;}
 __noinline unsigned nested_identity(void){byte&=(source^=0);return byte;}
 __noinline unsigned indirect_identity(unsigned *p){return p[choose()]|=0;}
 __noinline unsigned volatile_identity(void){return device^=0;}
 __noinline float rising(void){
  float i,temporary;
  for(i=-3.0f;7>=i;i+=3)temporary=i;
  return i;
 }
 __noinline float falling(void){
  float i;
  for(i=3.0f;0<i;--i){}
  return i;
 }
 __noinline float zero_trip(void){
  float i;
  for(i=-0.0f;i<0.0f;i++){}
  return i;
 }
 __noinline float fractional(void){
  float i;
  for(i=0.5f;i<2;i++){}
  return i;
 }
 __noinline float inexact_end(void){
  float i;
  for(i=16777214.0f;i<16777216.0f;i+=3.0f){}
  return i;
 }
 __noinline float reversed_inequality(void){
  float i;
  for(i=0;3!=i;i++){}
  return i;
 }
 __noinline float observable(void){
  float i;
  for(i=0;i<3;i++)device++;
  return i;
 }
 int main(void){
  unsigned a[2]={91,92};
  union {float value;unsigned long bits;} sign;
  if(nested_identity()!=0xa4||source!=0xb4)return 1;
  if(indirect_identity(a)!=91||touched!=1||a[0]!=91)return 2;
  device=2;if(volatile_identity()!=2||device!=2)return 3;
  if(rising()!=9.0f||falling()!=0.0f)return 4;
  sign.value=zero_trip();if(sign.bits!=0x80000000UL)return 5;
  if(fractional()!=2.5f||inexact_end()!=16777216.0f||reversed_inequality()!=3.0f)return 6;
  if(observable()!=3.0f||device!=5)return 7;
  return 0;
 }
 '''
 for disabled in (False,True):
  flags=['--no-strength-reduction'] if disabled else []
  path,rom,labels=support.compile_case(f'identity_and_binary32_loops_{int(disabled)}',source,flags=flags,
   extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
  asm=path.with_suffix('.s').read_text()
  def function(name):
   return asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  block=function('nested_identity')
  assert ('; fixed byte assignment' in block)==(not disabled),block
  assert bool(re.search(r'    sta .*_source',block))==disabled,block
  assert re.search(r'    sta .*_device',function('volatile_identity')),function('volatile_identity')
  for name in ('rising','falling','zero_trip','fractional','inexact_end','observable','reversed_inequality'):
   block=function(name)
   assert bool(re.search(r'__(?:fadd32|fsub32)\)',block))==(disabled or name in
    ('fractional','inexact_end','observable','reversed_inequality')),block
  support.emulate(rom,labels,0)
 source='''struct Bytes {unsigned char first;signed char low;unsigned char high,last;};
 char array[4];
 volatile struct Bytes device;
 volatile unsigned calls;
 __noinline char *read_pointer(void){calls++;return array;}
 __noinline int same_near_address(void){
  char local[3];
  return (void *)&local[1]==(void *)(local+1);
 }
 __noinline int different_near_offsets(void){return (void *)&array[0]!=(void *)(array+1);}
 __noinline int effectful_address(void){return (void *)read_pointer()==(void *)array;}
 __noinline int matched_bytes(struct Bytes value){
  ++value.first;
  --value.last;
  if(value.first!=2||value.last!=3)return 0;
  return -7==value.low&&value.high==13;
 }
 __noinline int mismatched_bytes(struct Bytes value){return value.high!=13||value.low!=-7;}
 __noinline int volatile_bytes(void){return device.low==-7&&device.high==13;}
 int main(void){
  struct Bytes pair={1,-7,13,4};
  if(!same_near_address()||!different_near_offsets()||!effectful_address()||calls!=1)return 1;
  if(!matched_bytes(pair)||mismatched_bytes(pair))return 2;
  pair.low=-8;if(matched_bytes(pair)||!mismatched_bytes(pair))return 3;
  pair.low=-7;pair.high=14;if(matched_bytes(pair)||!mismatched_bytes(pair))return 4;
  device.low=-7;device.high=13;if(!volatile_bytes())return 5;
  device.low=-8;if(volatile_bytes())return 6;
  return 0;
 }
 '''
 for disabled in (False,True):
  flags=['--no-strength-reduction'] if disabled else []
  path,rom,labels=support.compile_case(f'frame_byte_checks_{int(disabled)}',source,flags=flags)
  asm=path.with_suffix('.s').read_text()
  def function(name):
   return asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
  same=function('same_near_address')
  assert bool(re.search(r'^    (?:cmp|cpx|cpy) ',same,re.M))==disabled,same
  for name in ('matched_bytes','mismatched_bytes','volatile_bytes'):
   block=function(name)
   assert ('cmp #$0DF9' in block)==(not disabled and name!='volatile_bytes'),block
  if not disabled:
   block=function('matched_bytes')
   assert re.search(r'    inc a:\$[0-9A-F]+,x',block) and re.search(r'    dec a:\$[0-9A-F]+,x',block),block
  support.emulate(rom,labels,0)
 source='''int values[16];
 __noinline int nonnegative_shift(int count){
  int slot=16;
  do{values[slot>>=1]=count;}while(--count);
  return slot;
 }
 __noinline int negative_shift(int count){
  int slot=-8;
  do{values[(slot>>=1)&15]=count;}while(--count);
  return slot;
 }
 __noinline int changing_shift(int count){
  int slot=16;
  do{values[(slot>>=1)&15]=count;if(count==2)slot=-8;}while(--count);
  return slot;
 }
 int main(void){
  if(nonnegative_shift(3)!=2||values[8]!=3||values[4]!=2||values[2]!=1)return 1;
  if(negative_shift(2)!=-2||values[12]!=2||values[14]!=1)return 2;
  if(changing_shift(3)!=-4||values[8]!=3||values[4]!=2||values[12]!=1)return 3;
  return 0;
 }
 '''
 for disabled in (False,True):
  flags=['--no-strength-reduction'] if disabled else []
  path,rom,labels=support.compile_case(f'shift_invariant_{int(disabled)}',source,flags=flags)
  asm=path.with_suffix('.s').read_text()
  for name in ('nonnegative_shift','negative_shift','changing_shift'):
   block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
   assert ('    lsr a' in block)==(not disabled and name=='nonnegative_shift'),block
   assert ('    ror a' in block)==(disabled or name!='nonnegative_shift'),block
  support.emulate(rom,labels,0)
 source='''__noinline signed char choose_byte(signed char a,signed char b){
  return a<=0?a:b*2;
 }
 volatile signed char product_input;
 __noinline unsigned char byte_product(signed char a){return 8*a;}
 __noinline signed char volatile_product(void){return product_input*2;}
 volatile unsigned choice_state;
 struct BytePair {unsigned char value,other;};
 struct BytePair lhs={157,1},rhs={157,2};
 __noinline int fixed_byte_pair(void){return lhs.value==rhs.value;}
 __noinline unsigned read_choice(void){return ++choice_state;}
 __noinline int guarded_negation(int value){return 0==value?0:-value;}
 __noinline unsigned guarded_subtraction(unsigned value){return value!=0?0U-value:0U;}
 __noinline int effectful_negation(void){return read_choice()==0?0:-(int)read_choice();}
 __noinline unsigned choose_above(unsigned a){return a>49U?a:a+1U;}
 __noinline unsigned choose_below(unsigned a){return a<=49U?a+1U:a;}
 __noinline unsigned choose_effect(void){return read_choice()>49U?read_choice():read_choice()+1U;}
 int main(void){
  if(choose_byte(-128,1)!=-128||choose_byte(0,1)!=0)return 1;
  if(choose_byte(1,3)!=6||choose_byte(1,64)!=-128||choose_byte(1,-65)!=126)return 2;
  if(choose_above(48)!=49||choose_above(50)!=50||choose_below(48)!=49||choose_below(50)!=50)return 3;
  choice_state=49;
  if(choose_effect()!=51||choice_state!=51)return 4;
  product_input=-65;
  if(byte_product(-17)!=120||byte_product(33)!=8||volatile_product()!=126)return 5;
  if(guarded_negation(-7)!=7||guarded_negation(0)!=0||guarded_negation(9)!=-9||
     guarded_subtraction(65535U)!=1||guarded_subtraction(0)!=0)return 6;
  choice_state=0;
  if(effectful_negation()!=-2||choice_state!=2)return 7;
  if(!fixed_byte_pair())return 8;
  rhs.value=158;
  if(fixed_byte_pair())return 9;
  return 0;
 }
 '''
 for disabled in (False,True):
  flags=['--no-strength-reduction'] if disabled else []
  path,rom,labels=support.compile_case(f'narrow_zero_choice_{int(disabled)}',source,flags=flags)
  asm=path.with_suffix('.s').read_text()
  block=asm.split('_choose_byte:\n',1)[1].split('__size_choose_byte',1)[0]
  assert block.count('and #$00FF')==(4 if disabled else 2),block
  assert ('sbc #$0080' in block)==(not disabled),block
  pair=asm.split('_fixed_byte_pair:\n',1)[1].split('__size_fixed_byte_pair',1)[0]
  assert re.search(r'    sep #\$20\n\.a8\n    lda a:\.loword\(_lhs\+\$0000\)\n    cmp a:\.loword\(_rhs\+\$0000\)',pair),pair
  if not disabled:
   for name in ('guarded_negation','guarded_subtraction'):
    negation=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
    assert not re.search(r'    b(?:eq|ne|ra) ',negation),negation
   for name in ('choose_above','choose_below'):
    block=asm.split('_'+name+':\n',1)[1].split('__size_'+name,1)[0]
    assert 'cmp #$0032\n    bcs ' in block,block
  support.emulate(rom,labels,0)
 source='''__noinline int check_words(const unsigned *data,int count){
  int i;
  for(i=0;i<count;++i)
   if(data[i]!=(i>=3&&i<8))return i+1;
  return 0;
 }
 static unsigned named[9]={0,1,2,3,4,5,6,7,8};
 static volatile int mismatches;
 static __noinline void mismatch(void){++mismatches;}
 __noinline int check_named(void){
  for(int i=0;i<9;++i)if(named[i]!=(unsigned)i)mismatch();
  return mismatches;
 }
 int main(void){
  unsigned payload[9]={0,0,0,1,1,1,1,1,0};
  if(check_words(payload,9)!=0)return 1;
  payload[3]=2;if(check_words(payload,9)!=4)return 2;
  payload[3]=1;payload[8]=1;if(check_words(payload,9)!=9)return 3;
  if(check_words(payload,0)||check_named())return 4;
  named[8]=12;
  return check_named()!=1;
 }
 '''
 for enabled in (False,True):
  flags=[] if enabled else ['--no-strength-reduction']
  path,rom,labels=support.compile_case(f'cursor_word_comparison_{int(enabled)}',source,flags=flags)
  block=path.with_suffix('.s').read_text().split('_check_words:\n',1)[1].split('__size_check_words',1)[0]
  assert ('cmp a:$0000,x' in block or 'cmp z:$0000,x' in block)==enabled,block
  if enabled:
   named_block=path.with_suffix('.s').read_text().split('_check_named:\n',1)[1].split('__size_check_named',1)[0]
   assert 'strength cursor' not in named_block,named_block
  support.emulate(rom,labels,0)
 (OUT/'results.json').write_text(json.dumps(dict(masks=len(expected),MSVC=True,Mesen=True,short_circuit=True),indent=2))
 print(f'PASS: {len(expected)} signed/unsigned/byte/call comparison masks vs Python and MSVC; signed overflow, frame/immediate operands, short circuit branches')

if __name__=='__main__':main()
