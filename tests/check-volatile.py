"""Watch volatile memory reads and writes on the SNES and check how linking the console changes NMI startup."""
import os
import hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig
import accumulator_width
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'volatile-check'
WORKER_RESULT = 'ZICC_VOLATILE_RESULT '


def check_accumulator_width():
    body = '''; allocation function 1 begin
.segment "CODE"
_ordinary:
    sep #$20
.a8
    lda #$12
    sta a:$2100
    rep #$20
.a16
    lda #$1234
    sta a:$4302
    lda #$0001
    sep #$20
.a8
    sta a:$420B
    lda a:.loword(_flag)
    rep #$20
.a16
    bne byte_work
    lda #$0000
    rts
byte_work = *
    sep #$20
.a8
    lda #$34
    sta a:$2121
    rep #$20
.a16
    lda #$0001
    rts
; allocation function 1 end'''
    optimized = accumulator_width.select(body)
    assert 'ldx #$1234\n    stx a:$4302' in optimized, optimized
    assert 'bne byte_work\n    rep #$20' in optimized, optimized
    assert optimized.count('sep #$20') == 1, optimized
    assert 'ldx #$1234' not in accumulator_width.select(
        body.replace('    lda #$0001', '    txa\n    lda #$0001')), body

def execute(name,rom,labels,extra,expected=0,console=False,manual=False):
    reports={}
    worker=sys.argv[2:] if len(sys.argv)>1 and sys.argv[1]=='--worker' else None
    if worker and worker[0]!=name:return reports
    for region in ('ntsc','pal'):
        if worker and worker[1]!=region:continue
        if not worker:
            result=c.run([sys.executable,Path(__file__),'--worker',name,region],timeout=40)
            rows = [line.removeprefix(WORKER_RESULT) for line in result.stdout.splitlines()
                    if line.startswith(WORKER_RESULT)]
            assert len(rows) == 1, result.stdout + result.stderr
            reports[region] = json.loads(rows[0])
            print('PASS volatile '+name+' '+region,flush=True)
            continue
        home=OUT/name/region;home.mkdir(parents=True,exist_ok=True)
        script=f"""
local reads,writes,events=0,0,{{}}
local nmis,acks,enables=0,0,0
local entered=false
local function check(ok,message) if not ok then error(message) end end
local function ram(a) return emu.read(a&0x1ffff,emu.memType.snesWorkRam,false) end
local function word(a) return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false) end
emu.addMemoryCallback(function(a,v)
 if v==0x80 then enables=enables+1;check(entered=={str(manual).lower()} and acks==1,'enable ordering')
 else check(v==0,'unexpected NMITIMEN') end
end,emu.callbackType.write,0x004200)
emu.addMemoryCallback(function() acks=acks+1 end,emu.callbackType.read,0x004210)
emu.addMemoryCallback(function() error('unexpected TIMEUP read') end,emu.callbackType.read,0x004211)
emu.addMemoryCallback(function()
 entered=true
 local s=emu.getState();check(s['cpu.dbr']==0x7e and s['cpu.d']==0,'startup bank')
 s['cpu.y']=0x5a3c;emu.setState(s)
end,emu.callbackType.exec,{labels['main']},{labels['main']})
{extra}
emu.addMemoryCallback(function()
 local s=emu.getState()
 check(s['cpu.a']=={expected}&0xffff,'main result '..s['cpu.a'])
 check(s['cpu.sp']==0x04ff and s['cpu.y']==0x5a3c and s['cpu.d']==0 and s['cpu.dbr']==0x7e,'ABI')
 check(enables=={1 if console or manual else 0} and acks=={1 if console or manual else 0},'console selection')
 verify()
 emu.log('PASS reads='..reads..' writes='..writes..' nmis='..nmis)
 emu.breakExecution()
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
"""
        core=Core(home)
        try:
            config=SnesConfig();config.Region=1 if region=='ntsc' else 2
            config.Port1.Type=1;config.DisableFrameSkipping=True;config.RamPowerOnState=1
            config.GsuClockSpeed=100;config.BsxCustomDate=-1
            for i in range(8):config.ChannelVolumes[i]=100
            core.bind('SetSnesConfig',None,SnesConfig)(config)
            core.load(rom,home/'check.lua',script);core.start()
            reports[region]=core.wait_for('PASS',20)
            print(WORKER_RESULT + json.dumps(reports[region]),flush=True)
        finally:
            core.close_with_log(home/'check.log')
    if worker:sys.exit(0)
    return reports

def main():
    OUT.mkdir(parents=True,exist_ok=True);c.OUT=OUT;report={}
    check_accumulator_width()
    extra=[ROOT/f'build/{n}.o' for n in ('arithmetic','integers','ieee_engine')]
    source=r"""
#define BYTE (*(volatile unsigned char * __far)0x7e6000UL)
#define WORD (*(volatile unsigned * __far)0x7e6002UL)
#define LONG (*(volatile unsigned long * __far)0x7e6004UL)
volatile unsigned char copied;
volatile unsigned counter;
unsigned old_counter,new_counter;
volatile signed char byte_lhs=-5,byte_rhs=3,byte_result,byte_product;
volatile unsigned char byte_unsigned=254;
volatile unsigned word_lhs=0x2345,word_rhs=0x3456,word_result;
volatile unsigned word_divisor=3;
volatile unsigned word_shift_count=8;
volatile int signed_word=-0x3456;
volatile unsigned long long_lhs=0x10002UL,long_rhs=0x3fffeUL,long_result;
volatile unsigned long zero_test=0x10001UL;
volatile float float_lhs=1.25f,float_rhs=-0.75f,float_result;
volatile float cursor_input[3]={1.25f,2.5f,5.0f},cursor_output[2];
volatile float plus_zero=0.0f,minus_zero=-0.0f;
volatile union { float value; unsigned long bits; } float_special;
volatile int float_compare;
volatile unsigned long long wide_lhs=0xfedcba9876543210ULL,wide_rhs=0x0123456789abcdf0ULL,wide_result;
volatile signed char low_byte=-128,high_byte=127;
volatile long low_long=(-2147483647L-1L),high_long=2147483647L;
volatile long long low_wide=(-9223372036854775807LL-1LL),high_wide=9223372036854775807LL;
void probe(void){
 BYTE;BYTE;BYTE=17;BYTE+=2;BYTE++;BYTE=BYTE;
 if(BYTE&4)BYTE=31;
 if(BYTE&32)BYTE=1;
 { unsigned char temp; temp=BYTE; temp=BYTE; if(temp!=31)BYTE=2; }
 WORD;WORD=0x1234U;LONG;LONG=0x12345678UL;if(LONG==0)BYTE=1;
 copied=BYTE;
 counter=0x12ff;
 counter+=2;
 old_counter=counter--;
 new_counter=++counter;
 counter++;
}
void arithmetic(void){
 byte_result=byte_lhs+byte_rhs;
 byte_product=byte_lhs*byte_rhs;
 byte_result=byte_lhs/byte_rhs;
 byte_result=byte_lhs%byte_rhs;
 byte_result=byte_rhs/byte_lhs;
 byte_result=byte_lhs/byte_lhs;
 byte_result=byte_unsigned/byte_lhs;
 byte_result=byte_unsigned%byte_lhs;
 word_result=word_lhs+word_rhs;
 word_result=word_lhs/word_divisor;
 word_result=word_lhs<<word_shift_count;
 word_result=word_lhs>>word_shift_count;
 word_result=signed_word>>word_shift_count;
 long_result=long_lhs+long_rhs;
 long_result=-long_lhs;
 long_result=~long_lhs;
 long_result=zero_test!=0;
 zero_test=0x10000UL;
 long_result=0==zero_test;
 zero_test=0;
 long_result=zero_test==0;
 float_result=-float_lhs;
 float_compare=float_lhs>float_rhs;
 float_compare=plus_zero==minus_zero;
 float_special.bits=0x7fc00001UL;
 float_compare=float_special.value!=float_lhs;
 float_compare=float_special.value<=float_lhs;
 float_result=float_lhs++;
 float_result=--float_lhs;
 float_lhs--;
 float_lhs+=float_rhs;
 wide_result=wide_lhs;
 wide_result=wide_lhs+wide_rhs;
 wide_result=~wide_result;
 wide_result=-wide_lhs;
}
__noinline int cursor_math(void){
 volatile float *p=cursor_input,*q=cursor_output;
 float a,b;
 a=*p++,b=*p,a+=*++p;
 *q++=a,*q++=b;
 return p==cursor_input+2&&q==cursor_output+2;
}
#define RELATIONS(lo,hi) ((lo)<(hi) && (lo)<=(hi) && (hi)>(lo) && (hi)>=(lo) && (lo)!=(hi) && (lo)==(lo) && (lo)<=(lo) && !((lo)>(lo)))
int main(void){
 probe();arithmetic();
 if(!cursor_math())return 3;
 if(!RELATIONS(low_byte,high_byte)||!RELATIONS(low_long,high_long)||!RELATIONS(low_wide,high_wide))return 2;
 return copied!=31||old_counter!=0x1301||new_counter!=0x1301;
}
"""
    _,rom,labels=c.compile_case('transfers',source,extra_objects=extra)
    asm=rom.with_suffix('.s').read_text()
    cursor=asm.split('_cursor_math:\n',1)[1].split('__size_cursor_math',1)[0]
    assert '_cursor_input+$0008' in cursor and '_cursor_output+$0004' in cursor,cursor
    # Byte-granular bus trace proves no widened byte reads, extra reads,
    # merged/discarded operations, or high-word-first long transfers
    expected=[('r',0,0),('r',0,0),('w',0,17),('r',0,17),('w',0,19),
              ('r',0,19),('w',0,20),('r',0,20),('w',0,20)]
    expected += [('r',0,20),('w',0,31),('r',0,31),('r',0,31),('r',0,31)]
    expected += [('r',2,0),('r',3,0),('w',2,0x34),('w',3,0x12)]
    expected += [('r',i,0) for i in range(4,8)]
    expected += [('w',i,v) for i,v in enumerate((0x78,0x56,0x34,0x12),4)]
    expected += [('r',i,v) for i,v in enumerate((0x78,0x56,0x34,0x12),4)]
    expected += [('r',0,31)]
    table='{'+','.join('{'+repr(k)+','+str(a)+','+str(v)+'}' for k,a,v in expected)+'}'
    arithmetic=[
        ('r','byte_lhs',1,0xfb),('r','byte_rhs',1,3),('w','byte_result',1,0xfe),
        ('r','byte_lhs',1,0xfb),('r','byte_rhs',1,3),('w','byte_product',1,0xf1),
        ('r','byte_lhs',1,0xfb),('r','byte_rhs',1,3),('w','byte_result',1,0xff),
        ('r','byte_lhs',1,0xfb),('r','byte_rhs',1,3),('w','byte_result',1,0xfe),
        ('r','byte_rhs',1,3),('r','byte_lhs',1,0xfb),('w','byte_result',1,0),
        ('r','byte_lhs',1,0xfb),('r','byte_lhs',1,0xfb),('w','byte_result',1,1),
        ('r','byte_unsigned',1,254),('r','byte_lhs',1,0xfb),('w','byte_result',1,206),
        ('r','byte_unsigned',1,254),('r','byte_lhs',1,0xfb),('w','byte_result',1,4),
        ('r','word_lhs',2,0x2345),('r','word_rhs',2,0x3456),('w','word_result',2,0x579b),
        ('r','word_lhs',2,0x2345),('r','word_divisor',2,3),('w','word_result',2,0x0bc1),
        ('r','word_lhs',2,0x2345),('r','word_shift_count',2,8),('w','word_result',2,0x4500),
        ('r','word_lhs',2,0x2345),('r','word_shift_count',2,8),('w','word_result',2,0x23),
        ('r','signed_word',2,0xcbaa),('r','word_shift_count',2,8),('w','word_result',2,0xffcb),
        ('r','long_lhs',4,0x10002),('r','long_rhs',4,0x3fffe),('w','long_result',4,0x50000),
        ('r','long_lhs',4,0x10002),('w','long_result',4,0xfffefffe),
        ('r','long_lhs',4,0x10002),('w','long_result',4,0xfffefffd),
        ('r','zero_test',4,0x10001),('w','long_result',4,1),
        ('w','zero_test',4,0x10000),('r','zero_test',4,0x10000),('w','long_result',4,0),
        ('w','zero_test',4,0),('r','zero_test',4,0),('w','long_result',4,1),
        ('r','float_lhs',4,0x3fa00000),('w','float_result',4,0xbfa00000),
        ('r','float_lhs',4,0x3fa00000),('r','float_rhs',4,0xbf400000),('w','float_compare',2,1),
        ('r','plus_zero',4,0),('r','minus_zero',4,0x80000000),('w','float_compare',2,1),
        ('w','float_special',4,0x7fc00001),
        ('r','float_special',4,0x7fc00001),('r','float_lhs',4,0x3fa00000),('w','float_compare',2,1),
        ('r','float_special',4,0x7fc00001),('r','float_lhs',4,0x3fa00000),('w','float_compare',2,0),
        ('r','float_lhs',4,0x3fa00000),('w','float_lhs',4,0x40100000),('w','float_result',4,0x3fa00000),
        ('r','float_lhs',4,0x40100000),('w','float_lhs',4,0x3fa00000),('w','float_result',4,0x3fa00000),
        ('r','float_lhs',4,0x3fa00000),('w','float_lhs',4,0x3e800000),
        ('r','float_lhs',4,0x3e800000),('r','float_rhs',4,0xbf400000),('w','float_lhs',4,0xbf000000),
        ('r','wide_lhs',8,0xfedcba9876543210),('w','wide_result',8,0xfedcba9876543210),
        ('r','wide_lhs',8,0xfedcba9876543210),('r','wide_rhs',8,0x0123456789abcdf0),('w','wide_result',8,0),
        ('r','wide_result',8,0),('w','wide_result',8,0xffffffffffffffff),
        ('r','wide_lhs',8,0xfedcba9876543210),('w','wide_result',8,0x0123456789abcdf0),
        ('r','cursor_input',12,0x40a00000402000003fa00000),
        ('w','cursor_output',8,0x4020000040c80000),
    ]
    accesses = [(kind,labels[name]+i,(value>>(8*i))&255)
                for kind,name,size,value in arithmetic for i in range(size)]
    arithmetic_table = '{'+','.join('{'+repr(k)+','+str(a)+','+str(v)+'}' for k,a,v in accesses)+'}'
    hooks = []
    for kind,name,size in dict.fromkeys((kind,name,size) for kind,name,size,_ in arithmetic):
        addr=labels[name]
        event='read' if kind=='r' else 'write'
        hooks.append(f"emu.addMemoryCallback(function(a,v) if entered then math_events[#math_events+1]={{'{kind}',a,v}} end end,"
                     f"emu.callbackType.{event},{addr},{addr+size-1})")
    lua=f"""
local expected={table}
local math_expected={arithmetic_table}
local math_events={{}}
{chr(10).join(hooks)}
local multiply_writes,multiply_reads,multiply_start=0,0,0
local divide_writes,divide_reads,divide_start,divide_byte=0,0,0,1
local divide_outputs={{{{0x4214}},{{0x4216}},{{0x4214}},{{0x4214}},{{0x4214}},{{0x4216}},{{0x4214,0x4215}}}}
emu.addMemoryCallback(function()
 multiply_writes=multiply_writes+1
 multiply_start=emu.getState().masterClock
end,emu.callbackType.write,0x4203,0x4203)
emu.addMemoryCallback(function()
 check(divide_writes==divide_reads,'overlapping byte divisions')
 divide_writes=divide_writes+1
 divide_start=emu.getState().masterClock
end,emu.callbackType.write,0x4206,0x4206)
emu.addMemoryCallback(function(a)
 local now=emu.getState().masterClock
 if divide_reads<divide_writes then
  local output=divide_outputs[divide_writes]
  check(output and a==output[divide_byte] and now-divide_start>=96,'divider result or latency')
  if divide_byte==#output then divide_reads=divide_reads+1;divide_byte=1 else divide_byte=divide_byte+1 end
 else
  multiply_reads=multiply_reads+1
  check(a==0x4216 and now-multiply_start>=48,'byte multiplier result or latency')
 end
end,emu.callbackType.read,0x4214,0x4217)
local counter_events={{}}
local counter_expected={{
 {{0,0xff}},{{1,0x12}},{{2,0xff}},{{3,0x12}},{{0,1}},{{1,0x13}},
 {{2,1}},{{3,0x13}},{{0,0}},{{1,0x13}},
 {{2,0}},{{3,0x13}},{{0,1}},{{1,0x13}},
 {{2,1}},{{3,0x13}},{{0,2}},{{1,0x13}}
}}
local function counter_access(kind,a,v)
 if entered then counter_events[#counter_events+1]={{kind+a-{labels['counter']},v}} end
end
local function access(k,a,v)
 if not entered then return end
 events[#events+1]={{k,a-0x7e6000,v}}
 if k=='r' then reads=reads+1 else writes=writes+1 end
end
emu.addMemoryCallback(function(a,v) access('r',a,v) end,emu.callbackType.read,0x7e6000,0x7e600f)
emu.addMemoryCallback(function(a,v) access('w',a,v) end,emu.callbackType.write,0x7e6000,0x7e600f)
emu.addMemoryCallback(function(a,v) counter_access(2,a,v) end,emu.callbackType.read,{labels['counter']},{labels['counter']+1})
emu.addMemoryCallback(function(a,v) counter_access(0,a,v) end,emu.callbackType.write,{labels['counter']},{labels['counter']+1})
function verify()
 check(#events==#expected,'bus access count '..#events)
 for i,e in ipairs(expected) do local a=events[i];check(a[1]==e[1] and a[2]==e[2] and a[3]==e[3],'bus order/value '..i) end
 check(#counter_events==#counter_expected,'volatile word update count')
 for i,e in ipairs(counter_expected) do local a=counter_events[i];check(a[1]==e[1] and a[2]==e[2],'volatile word update '..i) end
 check(#math_events==#math_expected,'arithmetic bus access count '..#math_events)
 check(multiply_writes==1 and multiply_reads==1,'one hardware low-byte product')
 check(divide_writes==#divide_outputs and divide_reads==divide_writes,'one hardware division per expression')
 for i,e in ipairs(math_expected) do
  local a=math_events[i];check(a[1]==e[1] and a[2]==e[2] and a[3]==e[3],'arithmetic bus order/value '..i)
 end
end
"""
    report['transfers']=execute('transfers',rom,labels,lua)
    source=r"""
typedef volatile unsigned char Byte;
struct S { unsigned char a;unsigned b; };
volatile struct S first,second;
struct P { volatile unsigned char first;unsigned after; };
struct P returned_src,returned_dst;
__noinline struct P give(void){return returned_src;}
__noinline unsigned char copy_result(void){return (returned_dst=give()).first;}
volatile unsigned divisor;
unsigned char * volatile pointer;
volatile unsigned char window[9][3]={{11},{22},{33},{44},{55},{66},{77},{88},{99}};
volatile unsigned char window_output;
__noinline int clipped_window(void){
 int i;
 for(i=-3;i<9;++i)if(0<=i&&i<=5){if(i==3)continue;window_output=window[i][0];}
 return i;
}
__noinline int empty_window(void){
 int i;
 for(i=0;i<9;++i)if(i>10)window_output=window[i][0];
 return i;
}
unsigned consume(volatile unsigned x){x=7;return x+x;}
int main(void){
 unsigned i,a,b;Byte *p=(Byte *)0x6100;Byte (*rows)[2]=(Byte (*)[2])0x6100;
 Byte *raw=(Byte *)&returned_src;
 *p=3;*p;*p;(*p)++;*p+=2;
 for(i=0;i<3;i++)a=*p;
 pointer=(unsigned char *)0x6100;*pointer;*pointer;
 rows[0][1]=9;rows[0][1];
 first.a=5;first.b=123;second=first;second;
 divisor=30;a=divisor/7;b=divisor%7;
 if(a!=4||b!=2||consume(1)!=14)return 1;
 if(second.a!=5||second.b!=123)return 2;
 if(clipped_window()!=9||empty_window()!=9)return 3;
 raw[0]=0x11;raw[1]=0x22;raw[2]=0x33;raw[3]=0x44;
 if(copy_result()!=0x11)return 4;
 return 0;
}
"""
    _,rom,labels=c.compile_case('qualification',source,extra_objects=extra)
    asm=rom.with_suffix('.s').read_text()
    clipped=asm.split('_clipped_window:\n',1)[1].split('__size_clipped_window',1)[0]
    assert 'cmp #$0006' in clipped and '#$FFFD' not in clipped,clipped
    for function in ('give','copy_result'):
        body=asm.split(f'_{function}:\n',1)[1].split(f'__size_{function}',1)[0]
        assert 'volatile aggregate: 4 byte accesses, fixed operands' in body,body
    lua=f"""
local near_reads,near_writes=0,0
local pointer_reads,divisor_reads=0,0
local window_reads,window_writes=0,0
local window_indices={{0,1,2,4,5}}
local returned_reads,returned_writes=0,0
emu.addMemoryCallback(function(a,v)
 if not entered then return end
 check(a=={labels['returned_src']}+returned_reads,'return source byte order')
 returned_reads=returned_reads+1
 check(v==0x11*returned_reads,'return source byte value')
end,emu.callbackType.read,{labels['returned_src']},{labels['returned_src']+3})
emu.addMemoryCallback(function(a,v)
 if not entered then return end
 check(returned_reads==4 and a=={labels['returned_dst']}+returned_writes,'return destination byte order')
 returned_writes=returned_writes+1
 check(v==0x11*returned_writes,'return destination byte value')
end,emu.callbackType.write,{labels['returned_dst']},{labels['returned_dst']+3})
emu.addMemoryCallback(function(a) near_reads=near_reads+1 end,emu.callbackType.read,0x7e6100,0x7e6101)
emu.addMemoryCallback(function(a) if entered then near_writes=near_writes+1 end end,emu.callbackType.write,0x7e6100,0x7e6101)
emu.addMemoryCallback(function() pointer_reads=pointer_reads+1 end,emu.callbackType.read,{labels['pointer']},{labels['pointer']+1})
emu.addMemoryCallback(function() divisor_reads=divisor_reads+1 end,emu.callbackType.read,{labels['divisor']},{labels['divisor']+1})
emu.addMemoryCallback(function(a,v)
 if not entered then return end
 window_reads=window_reads+1
 local i=window_indices[window_reads]
 check(i and a=={labels['window']}+3*i and v==11*(i+1),'clipped byte read')
end,emu.callbackType.read,{labels['window']},{labels['window']+26})
emu.addMemoryCallback(function(_,v)
 if not entered then return end
 window_writes=window_writes+1
 local i=window_indices[window_writes]
 check(i and window_writes==window_reads and v==11*(i+1),'clipped byte store')
end,emu.callbackType.write,{labels['window_output']},{labels['window_output']})
function verify()
 check(near_reads==12 and near_writes==4,'near byte access width/count '..near_reads..'/'..near_writes)
 check(pointer_reads==4,'volatile pointer reads '..pointer_reads)
 check(divisor_reads==4,'volatile division reuse '..divisor_reads)
 check(window_reads==5 and window_writes==5,'clipped window count')
 check(returned_reads==4 and returned_writes==4,'return aggregate byte count')
end
"""
    report['qualification']=execute('qualification',rom,labels,lua)
    source=r"""
char * __far volatile left;
char * __far volatile right;
int visit(char * __far p){return p!=(char * __far)0x7effffUL;}
int main(void){
 unsigned i;
 left=(char * __far)0x7effffUL;right=(char * __far)0x7f0000UL;
 if(left==right)return 1;
 if(visit(left))return 2;
 left++;if(left!=right)return 3;
 for(i=0;i<1;left--){i++;}
 if(left+1!=right)return 4;
 return 0;
}
"""
    _,rom,labels=c.compile_case('far-pointers',source,extra_objects=extra)
    events=[]
    def transfer(kind,name,value):
        events.extend((kind,labels[name]+i,(value>>(8*i))&255) for i in range(4))
    transfer('w','left',0x7effff);transfer('w','right',0x7f0000)
    transfer('r','left',0x7effff);transfer('r','right',0x7f0000)
    transfer('r','left',0x7effff)  # Argument evaluation
    transfer('r','left',0x7effff);transfer('w','left',0x7f0000)
    transfer('r','left',0x7f0000);transfer('r','right',0x7f0000)
    transfer('r','left',0x7f0000);transfer('w','left',0x7effff)
    transfer('r','left',0x7effff);transfer('r','right',0x7f0000)
    table='{'+','.join('{'+repr(k)+','+str(a)+','+str(v)+'}' for k,a,v in events)+'}'
    lua=f"""
local expected={table}
local function transfer(k,a,v)
 if not entered then return end
 events[#events+1]={{k,a,v}}
end
"""
    for name in ('left','right'):
        lua+=f"emu.addMemoryCallback(function(a,v) transfer('r',a,v) end,emu.callbackType.read,{labels[name]},{labels[name]+3})\n"
        lua+=f"emu.addMemoryCallback(function(a,v) transfer('w',a,v) end,emu.callbackType.write,{labels[name]},{labels[name]+3})\n"
    lua+="""
function verify()
 check(#events==#expected,'far pointer transfer count '..#events)
 for i,e in ipairs(expected)do local a=events[i];check(a[1]==e[1] and a[2]==e[2] and a[3]==e[3],'far pointer transfer order/value '..i)end
end
"""
    report['far-pointers']=execute('far-pointers',rom,labels,lua)
    source=r"""
#include <stdio.h>
#include <time.h>
volatile unsigned interrupts;
__interrupt(nmi) void vblank(void){interrupts++;}
int main(void){clock_t start;printf("ok");start=clock();while(clock()-start<3UL){}return interrupts<3;}
"""
    # console=False deliberately uses ordinary startup; the linked console hook
    # must initialize video and NMI without the old CONSOLE assembly define
    _,rom,labels=c.compile_case('console',source,extra_objects=[ROOT/'build/console.o',*extra])
    lua=f"""
emu.addMemoryCallback(function() nmis=nmis+1 end,emu.callbackType.exec,{labels['interrupt_body_vblank']},{labels['interrupt_body_vblank']})
function verify()
 check(nmis>=3,'no delivered NMI')
 check(word({labels['interrupts']})==nmis,'user NMI count')
 check(word({labels['clock_frames']})==nmis,'library tick count')
 check(word({labels['console_map']})==222 and word({labels['console_map']+2048})==214,'console text')
end
"""
    report['console']=execute('console',rom,labels,lua,console=True)
    source=source.replace('printf("ok");','(void)*(const volatile unsigned char * __far)0x4210UL;*(volatile unsigned char * __far)0x4200UL=0x80;')
    _,rom,labels=c.compile_case('mmio',source,extra_objects=extra)
    lua=f"""
emu.addMemoryCallback(function() nmis=nmis+1 end,emu.callbackType.exec,{labels['interrupt_body_vblank']},{labels['interrupt_body_vblank']})
function verify()
 check(nmis>=3,'no delivered NMI')
 check(word({labels['interrupts']})==nmis,'user NMI count')
 check(word({labels['clock_frames']})==nmis,'library tick count')
end
"""
    report['mmio']=execute('mmio',rom,labels,lua,manual=True)
    source=r"""
#define PORT_A (*(volatile unsigned char * __far)0x7e6000UL)
#define PORT_B (*(volatile unsigned char * __far)0x7e6001UL)
unsigned char low=0x12, high=0x34;
volatile unsigned char tail=0x56;
void copy_bytes(void){
    PORT_A=low; PORT_A=high;
    PORT_B=low; PORT_B=high;
    PORT_A=tail;
}
int main(void){
    copy_bytes();
    return PORT_A!=0x56 || PORT_B!=0x34;
}
"""
    path,rom,labels=c.compile_case('byte-region',source)
    body=path.with_suffix('.s').read_text().split('_copy_bytes:\n',1)[1].split('return_copy_bytes',1)[0]
    assert body.count('sep #$20')==body.count('rep #$20')==1, body
    assert 'xba' not in body, body
    stores=[line.strip() for line in body.splitlines() if line.strip().startswith('sta ')]
    assert stores==['sta f:$7E6000']*2+['sta f:$7E6001']*2+['sta f:$7E6000'], body
    report['byte-region']=c.emulate(rom,labels,0)
    source=r"""
#define PORT(n) (*(volatile unsigned char * __far)(0x7e6000UL+(n)))
unsigned char near_data;
const unsigned char far_data[1]={42};
void write_banks(void){
    PORT(0)=0x12;
    PORT(1)=(unsigned char)((unsigned long)(const void * __far)&near_data>>16);
    PORT(2)=(unsigned char)((unsigned long)(const void * __far)&far_data>>16);
    PORT(3)=0x34;
}
int main(void){
    write_banks();
    return PORT(0)!=0x12 || PORT(1)!=0x7e || PORT(3)!=0x34;
}
"""
    path,rom,labels=c.compile_case('bank-byte',source)
    body=path.with_suffix('.s').read_text().split('_write_banks:\n',1)[1].split('return_write_banks',1)[0]
    assert body.count('sep #$20')==body.count('rep #$20')==1, body
    assert 'lda #$7E\n' in body and 'lda #.bankbyte(_far_data)\n' in body, body
    assert 'txa' not in body and '.loword(_near_data)' not in body, body
    report['bank-byte']=c.emulate(rom,labels,0,extra_checks=f"""
emu.addMemoryCallback(function()
    require_value(emu.read(0x6002,emu.memType.snesWorkRam,false)=={labels['far_data']>>16},'linked bank byte')
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
""")
    source=r"""
volatile unsigned counter=0x12feU;
__noinline unsigned count_updates(unsigned count,unsigned stop){
    do {
        ++counter;
        if(counter==stop) break;
    } while(--count>0);
    return count;
}
int main(void){
    if(count_updates(3,0x1300U)!=2)return 1;
    return count_updates(1,0x1304U)!=0;
}
"""
    path,rom,labels=c.compile_case('register-countdown',source)
    body=path.with_suffix('.s').read_text().split('_count_updates:\n',1)[1].split('__size_count_updates',1)[0]
    assert '; loop lowering: register countdown' in body and '    dex\n' in body,body
    expected=[]
    for before,after in zip(range(0x12fe,0x1301),range(0x12ff,0x1302)):
        expected.extend([[2,before&255],[3,before>>8],[0,after&255],[1,after>>8],[2,after&255],[3,after>>8]])
    lua_events='{'+','.join('{'+','.join(map(str,event))+'}' for event in expected)+'}'
    lua=f"""
local expected={lua_events}
local events=0
local function access(kind,a,value)
 if not entered then return end
 events=events+1
 local want=expected[events]
 check(want and want[1]==kind+a-{labels['counter']} and want[2]==value,'countdown bus access '..events)
end
emu.addMemoryCallback(function(a,v) access(2,a,v) end,emu.callbackType.read,{labels['counter']},{labels['counter']+1})
emu.addMemoryCallback(function(a,v) access(0,a,v) end,emu.callbackType.write,{labels['counter']},{labels['counter']+1})
function verify() check(events==#expected,'countdown bus access count') end
"""
    report['register-countdown']=execute('register-countdown',rom,labels,lua)
    source=r"""
volatile unsigned byte_updates;
__noinline unsigned count_byte_updates(unsigned char count,unsigned stop){
    do {
        ++byte_updates;
        if(byte_updates==stop) break;
        continue;
    } while(--count>0);
    return count;
}
int main(void){
    if(count_byte_updates(0,1)!=0||byte_updates!=1)return 1;
    if(count_byte_updates(0,0)!=0||byte_updates!=257)return 2;
    if(count_byte_updates(255,259)!=254||byte_updates!=259)return 3;
    if(count_byte_updates(1,0)!=0||byte_updates!=260)return 4;
    return 0;
}
"""
    for mode,flags in [('register',[]),('memory',['--no-loop-index-retention'])]:
        name='byte-countdown-'+mode
        path,rom,labels=c.compile_case(name,source,flags=flags)
        body=path.with_suffix('.s').read_text().split('_count_byte_updates:\n',1)[1].split('__size_count_byte_updates',1)[0]
        assert ('; loop lowering: register countdown' in body)==(mode=='register'),body
        report[name]=c.emulate(rom,labels,0)
    source=r"""
volatile unsigned counter;
__noinline void batch(void){
    unsigned count=16;
    do ++counter; while(--count);
}
__noinline void odd_batch(void){
    unsigned char count=17;
    do ++counter; while(--count);
}
__noinline void long_batch(void){
    unsigned count=512;
    do ++counter; while(--count);
}
int main(void){
    batch();if(counter!=16)return 1;
    odd_batch();if(counter!=33)return 2;
    long_batch();return counter!=545;
}
"""
    for mode,flags in [('unrolled',[]),('scalar',['--no-loop-unroll'])]:
        name='word-countdown-'+mode
        path,rom,labels=c.compile_case(name,source,flags=flags)
        asm=path.with_suffix('.s').read_text()
        for function in ('batch','odd_batch','long_batch'):
            body=asm.split('_'+function+':\n',1)[1].split('__size_'+function,1)[0]
            assert ('; unrolled register countdown' in body)==(mode=='unrolled' and function!='odd_batch'),body
            if mode=='unrolled' and function=='long_batch':
                assert '; unrolled register countdown: 16 trips' in body,body
        report[name]=c.emulate(rom,labels,0)
    negatives=[
        'int main(void){volatile int x;int *p=&x;return 0;}',
        'void f(int *p);int main(void){volatile int x;f(&x);return 0;}',
        'int main(void){const volatile int x=1;x=2;return 0;}',
        'int main(void){volatile int a[2][2];int (*p)[2]=a;return 0;}',
    ]
    for i,source in enumerate(negatives):
        path=OUT/f'bad-{i}.c';path.write_text(source)
        c.run([ROOT/'build/zicc.exe',path,'-o',path.with_suffix('.s')],expected=1)
    report['negative_cases']=len(negatives)
    report['compiler_sha256']=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
