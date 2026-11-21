"""Target execution checks for the Priority 4 library and ABI work."""
import os
import importlib.util
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'priority4-check'
spec = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def build(name, source, stage=1, extra_source=None, lto=False):
    path = OUT / f'{name}.c'
    path.write_text(source)
    raw = path.with_suffix('.raw')
    sources = [path]
    if extra_source is not None:
        kernel = OUT / f'{name}-kernel.c'
        kernel.write_text(extra_source)
        sources.append(kernel)
    support.run([sys.executable, ROOT / 'tools/build-rom.py', *sources,
                 '--stage', str(stage), '-o', raw, *(['--lto'] if lto else [])], timeout=120)
    labels = {name.removeprefix('_'): int(address, 16)
              for address, name in re.findall(r'^al (\w+) \.(\S+)$',
                                               raw.with_suffix('.labels').read_text(), re.M)}
    rom = raw.with_suffix('.sfc')
    support.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
    return rom, labels


def assertions():
    rom, labels = build('assert-disabled', '''
#include <assert.h>
#define NDEBUG
#include <assert.h>
int main(void){int n=0;assert(++n);return n;}
''')
    assert '__zicc_assert_fail' not in labels
    support.emulate(rom, labels, 0)
    for stage in (1, 3):
        rom, labels = build(f'assert-failure-{stage}', '''
#define NDEBUG
#include <assert.h>
#undef NDEBUG
#include <assert.h>
volatile int evaluations;
int main(void){
    assert(++evaluations == 1);
#line 75 "assert-fixture.c"
    assert(++evaluations == 3);
    return 7;
}
''', stage)
        checks = f'''
local function word(a) return emu.read16(a,emu.memType.snesMemory,false) end
local function text(a)
    local p=word(a)|(word(a+2)<<16)
    local t=""
    for i=0,63 do
        local b=emu.read(p+i,emu.memType.snesMemory,false)
        if b==0 then return t end
        t=t..string.char(b)
    end
    return t
end
emu.addMemoryCallback(function()
    require_value(word({labels['evaluations']})==2,'assert operand evaluated once')
    require_value(word({labels['_assert_line']})==75,'assert line')
    require_value(text({labels['_assert_file']})=='assert-fixture.c','assert filename')
    require_value(text({labels['_assert_expression']})=='++evaluations == 3','assert spelling')
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
        support.emulate(rom, labels, 0, extra_checks=checks, expected_abort=True)


def integer_conversions():
    source = r'''
#include <stdlib.h>
#include <errno.h>
#include <limits.h>
const char no_digits[]="  -xyz";
const char incomplete_hex[]="0x!";
int main(void){
    char * __far end;
    errno=7;
    if(strtol(" \t-0x7f!", &end, 0)!=-127L||*end!='!'||errno!=7)return 1;
    if(strtol("0758",&end,0)!=61L||*end!='8')return 2;
    if(strtoul("Zz?", &end,36)!=1295UL||*end!='?')return 3;
    if(strtol(no_digits,&end,10)||end!=no_digits)return 4;
    if(strtol(incomplete_hex,&end,16)||end!=incomplete_hex+1)return 5;
    if(strtol("-2147483648",&end,10)!=LONG_MIN||*end||errno!=7)return 6;
    if(strtoul("-4294967295",&end,10)!=1UL||*end||errno!=7)return 7;
    if(strtol("2147483648x",&end,10)!=LONG_MAX||*end!='x'||errno!=ERANGE)return 8;
    errno=0;
    if(strtol("-2147483649",&end,10)!=LONG_MIN||*end||errno!=ERANGE)return 9;
    errno=0;
    if(strtoul("4294967296000!",&end,10)!=ULONG_MAX||*end!='!'||errno!=ERANGE)return 10;
    if(atoi(" -32768tail")!=-32767-1||atol("+123456")!=123456L)return 11;
    return 0;
}
'''
    for stage in (1, 3):
        rom, labels = build(f'integer-conversions-{stage}', source, stage)
        support.emulate(rom, labels, 0)


def absolute_values():
    source = '''
#include <stdlib.h>
volatile int word=-32767;
volatile long wide=-2147483647L;
int main(void){
    if(abs(word)!=32767||labs(wide)!=2147483647L)return 1;
    word=0;wide=-65536L;
    if(abs(word)!=0||labs(wide)!=65536L)return 2;
    word=19;wide=65537L;
    if(abs(word)!=19||labs(wide)!=65537L||labs(0L)!=0)return 3;
    return 0;
}
'''
    for stage in (1, 3):
        rom, labels = build(f'absolute-values-{stage}', source, stage)
        support.emulate(rom, labels, 0)


def variadic_formatting():
    source = r'''
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
typedef int (*callback)(int);
typedef int (*formatter)(char *, const char * __far, ...);

static int render(char *out,const char * __far format,va_list ap){
    int n=0;
    while(*format){
        if(*format!='%'){
            out[n++]=*format++;
            continue;
        }
        ++format;
        switch(*format++){
        case 'd':n+=sprintf(out+n,"%d",va_arg(ap,int));break;
        case 'l':n+=sprintf(out+n,"%ld",va_arg(ap,long));break;
        case 's':n+=sprintf(out+n,"%s",va_arg(ap,char *));break;
        case 'S':n+=sprintf(out+n,"%S",va_arg(ap,const char * __far));break;
        case 'f':n+=sprintf(out+n,"%.1f",va_arg(ap,double));break;
        default:return -1;
        }
    }
    out[n]=0;
    return n;
}
static int format_output(char *out,const char * __far format,...){
    va_list ap,copy;
    char reference[48];
    int n;
    va_start(ap,format);
    va_copy(copy,ap);
    n=render(out,format,ap);
    va_end(ap);
    if(render(reference,format,copy)!=n||strcmp(out,reference))n=-1;
    va_end(copy);
    return n;
}
static int increment(int n){return n+1;}
static int register_prefix(int first,int last,...){
    va_list ap;
    int n;
    va_start(ap,last);
    n=va_arg(ap,int (*)(int))(first);
    n+=va_arg(ap,int *)[0]+last;
    va_end(ap);
    return n;
}
static int stack_prefix(int first,long second,int last,...){
    va_list ap;
    va_start(ap,last);
    return first+(int)second+last+va_arg(ap,int);
}
static long skip_arguments(int tag,...){
    va_list ap,copy;
    int i;
    va_start(ap,tag);
    va_copy(copy,ap);
    for(i=0;i<3;++i)(void)va_arg(ap,int);
    if(va_arg(copy,int)!=tag)return -1;
    return va_arg(ap,long);
}
__noinline int scan_arguments(int tag,...){
    va_list ap;
    for(int i=0;i<2;++i){
        va_start(ap,tag);
        char *value;
        int length=0;
        while((value=va_arg(ap,char *))!=0)length+=*value;
        if(length!=tag||va_arg(ap,int)!=1234)return 0;
        va_end(ap);
    }
    return 1;
}
int main(void){
    formatter format=format_output;
    char out[48],near_text[]="near";
    signed char small=-7;
    int pointed=30;
    if(format(out,"%d|%l|%s|%S|%f",small,70000L,near_text,"far",1.5)!=21)return 1;
    if(strcmp(out,"-7|70000|near|far|1.5"))return 2;
    if(register_prefix(4,6,increment,&pointed)!=41)return 3;
    if(stack_prefix(2,5L,7,11)!=25)return 4;
    if(skip_arguments(4,4,-8,19,0x12345678L)!=0x12345678L)return 5;
    if(!scan_arguments('n'+'e',near_text,near_text+1,(char *)0,1234))return 6;
    return 0;
}
'''
    for stage in (1, 3, 4):
        rom, labels = build(f'variadic-formatting-{stage}', source, stage)
        support.emulate(rom, labels, 0)
    invalid = {
        'nonvariadic': ('int f(int n){va_list ap;va_start(ap,n);return 0;}',
                        'requires a variadic function'),
        'wrong-last': ('int f(int a,int b,...){va_list ap;va_start(ap,a);return 0;}',
                       'requires the last named parameter'),
        'unpromoted': ('int f(va_list ap){return va_arg(ap,char);}',
                       'requires a promoted scalar or pointer'),
    }
    for name, (code, message) in invalid.items():
        path = OUT / f'{name}.c'
        path.write_text('#include <stdarg.h>\n'+code)
        result = subprocess.run([str(ROOT / 'build/zicc.exe'), str(path), '-o',
                                 str(path.with_suffix('.s'))], capture_output=True, text=True)
        assert result.returncode and message in result.stderr, (name, result.stderr)


def allocation():
    source = '''
#include <stdlib.h>
int main(void){
    unsigned char *p=malloc(12),*guard,*grown;
    unsigned i;
    if(!p)return 1;
    for(i=0;i<12;++i)p[i]=165;
    free(p);
    p=calloc(3,4);
    if(!p||calloc(256,256)||calloc(0,8)||calloc(8,0))return 2;
    for(i=0;i<12;++i){if(p[i])return 3;p[i]=i+1;}
    guard=realloc(0,12);
    if(!guard)return 4;
    guard[0]=199;
    if(realloc(p,65535U)||p[11]!=12||guard[0]!=199)return 5;
    grown=realloc(p,33);
    if(!grown||guard[0]!=199)return 6;
    for(i=0;i<12;++i)if(grown[i]!=i+1)return 7;
    p=realloc(grown,5);
    if(!p||p[4]!=5||realloc(p,0))return 8;
    free(guard);
    return 0;
}
'''
    for stage in (1, 3):
        rom, labels = build(f'allocation-{stage}', source, stage)
        support.emulate(rom, labels, 0)


def aggregate_calls():
    types = '''
struct Pair { int x; long y; char text[4]; };
union Choice { long x; char bytes[4]; };
typedef struct Pair (*Callback)(struct Pair, int, long);
struct Pair adjust(struct Pair p,int n,long k);
union Choice echo(union Choice v);
int variadic_pair(int tag,...);
'''
    driver = types + '''
const struct Pair rom={5,70000L,"abc"};
volatile struct Pair observed={7,11L,"abc"};
int main(void){
    struct Pair x=rom, y;
    Callback fn=adjust;
    union Choice v={131075L},w;
    y=fn(adjust(x,1,2L),3,4L);
    if(x.x!=5||x.y!=70000L||x.text[0]!='a')return 1;
    if(y.x!=9||y.y!=70006L||y.text[0]!='z')return 2;
    if(adjust(rom,2,3L).x!=7||adjust(rom,2,3L).text[2]!='c')return 3;
    w=echo(v);
    if(w.x!=131076L||v.x!=131075L)return 4;
    if(adjust(observed,1,2L).y!=13L||variadic_pair(3,y,4)!=16)return 5;
    return 0;
}
'''
    kernel = types + '''
#include <stdarg.h>
struct Pair adjust(struct Pair p,int n,long k){
    p.x+=n;p.y+=k;p.text[0]='z';
    return p;
}
union Choice echo(union Choice v){v.x++;return v;}
int variadic_pair(int tag,...){
    va_list ap;
    struct Pair p;
    int tail;
    va_start(ap,tag);
    p=va_arg(ap,struct Pair);
    tail=va_arg(ap,int);
    va_end(ap);
    return tag+p.x+tail;
}
'''
    for stage, lto in ((1, False), (3, False), (4, True)):
        rom, labels = build(f'aggregate-calls-{stage}', driver, stage, kernel, lto)
        support.emulate(rom, labels, 0)


def bitfields():
    source = '''
#include <stddef.h>
struct Bits {
    unsigned low:3;
    signed middle:5;
    unsigned :3;
    unsigned high:5;
    unsigned :0;
    unsigned next:4;
    unsigned char tail;
};
union View { struct Bits fields; unsigned word; };
union Plain { unsigned part:4; unsigned word; };
const union View packed={{5,-3,17,9,170}};
const union Plain overlay={11};
volatile struct Bits live={3,-4,7,8,170};
struct Bits indexed[2];
struct Factor {unsigned scale:2;signed signed_scale:2;};
unsigned visits;
volatile struct Bits * __far target(void){++visits;return &live;}
unsigned pack_named(int a,int b,unsigned c){
    union View item;
    item.word=0x00e0;
    item.fields.low=a;
    item.fields.middle=b;
    item.fields.high=c;
    return item.word;
}
struct Widths { unsigned x:1,y:2,z:3; };
union Pack { struct Widths fields; unsigned word; };
unsigned pack_pair(int x,int y,int z){
    union Pack first,second;
    first.word=0xc000U;
    second.word=0x8000U;
    first.fields.x=x;
    first.fields.y=y;
    first.fields.z=z;
    second.fields.x=x;
    second.fields.y=y;
    second.fields.z=z;
    second.fields.z+=2;
    return (first.word!=0xc02dU)|(second.word!=0x803dU);
}
unsigned pack_pair_initializers(int x,int y,int z){
    struct Widths first={x,y,z};
    struct Widths second={x,y,z};
    second.z+=2;
    return first.z+second.z;
}
int read_low(union View *item){return item->fields.low;}
union Upper {struct {unsigned low:12;signed high:4;} fields;unsigned word;};
volatile union Upper upper={ {0xabc,0} };
int update_upper(int n){upper.fields.high=n;return upper.fields.high;}
union Upper packed_upper;
__noinline int add_upper(int n){
    packed_upper.fields.high+=n;
    return -8==packed_upper.fields.high;
}
__noinline int add_inner(int n){
    union View item;
    item.word=0x889dU;
    item.fields.middle+=n;
    return item.fields.middle!=-16||item.word!=0x8885U;
}
unsigned pack_observed(int a){
    union View item;
    item.word=0;
    item.fields.low=a;
    item.fields.middle=read_low(&item);
    return item.word;
}
unsigned update_alias(unsigned n){
    union View item,other;
    union View *p=&item;
    item.word=0x88edU;
    other.word=0;
    p->fields.low+=n;
    p=&other;
    p->fields.high=n;
    return item.word^other.word;
}
int multiply_bits(int x,struct Factor *p){return x*p->scale;}
int multiply_bits_reverse(int x,struct Factor *p){return p->scale*x;}
int multiply_signed_bits(int x,struct Factor *p){return x*p->signed_scale;}
int update_named(int value){
    struct Bits local={0,-5};
    int old;
    local.low=value;
    old=local.low--;
    ++indexed[1].high;
    indexed[1].middle+=local.middle;
    return old+local.low;
}
int main(void){
    struct Bits local={2,-5};
    struct Factor factor={0,-2};
    int old;
    if(sizeof(struct Bits)!=6||offsetof(struct Bits,tail)!=4)return 1;
    if(packed.word!=0x88edU||packed.fields.middle!=-3||
       packed.fields.next!=9||packed.fields.tail!=170||overlay.word!=11)return 2;
    if(local.low!=2||local.middle!=-5||local.high||local.next||local.tail)return 3;
    if(local.low-8>=0||((unsigned)local.low)-8<0)return 4;
    if((local.low=9)!=1||local.low!=1||local.middle!=-5)return 5;
    old=local.middle++;
    if(old!=-5||local.middle!=-4||--local.middle!=-5)return 6;
    target()->low+=(live.high=19,4);
    if(visits!=1||live.low!=7||live.high!=19||live.middle!=-4||live.next!=8||live.tail!=170)return 7;
    live.middle*=2L;
    live.high>>=1;
    if(live.middle!=-8||live.high!=9||live.low!=7)return 8;
    if(update_named(8)!=7||indexed[1].high!=1||indexed[1].middle!=-5)return 9;
    for(old=0;old<4;++old){
        factor.scale=old;
        if(multiply_bits(-1234,&factor)!=-1234*old||multiply_bits_reverse(-1234,&factor)!=-1234*old)return 10;
    }
    if(multiply_signed_bits(-1234,&factor)!=2468)return 11;
    if(pack_named(10,-3,33)!=0x08eaU||pack_observed(10)!=18)return 12;
    if(update_upper(-9)!=7||upper.word!=0x7abcU||update_upper(-8)!=-8||upper.word!=0x8abcU)return 13;
    if(update_alias(10)!=0xd8efU)return 14;
    if(pack_pair(3,6,13)||pack_pair_initializers(3,6,13)!=12)return 15;
    packed_upper.word=0x7abcU;
    if(add_upper(1)!=1||packed_upper.word!=0x8abcU)return 16;
    if(add_upper(-1)!=0||packed_upper.word!=0x7abcU)return 17;
    if(add_inner(-3))return 18;
    return 0;
}
'''
    for stage in (1, 4):
        rom, labels = build(f'bitfields-{stage}', source, stage)
        support.emulate(rom, labels, 0)
    path = OUT / 'bitfields-direct.c'
    path.write_text(source)
    asm = path.with_suffix('.s')
    support.run([ROOT / 'build/zicc.exe', path, '-o', asm, '-I', ROOT / 'include'])
    text = asm.read_text()
    named = text.split('_update_named:\n', 1)[1].split('__size_update_named', 1)[0]
    assert '[__arith_lhs]' not in named and 'sta a:.loword(_indexed+$0006)' in named, named
    packed_body = text.split('_pack_named:\n', 1)[1].split('__size_pack_named', 1)[0]
    assert 'fused adjacent bit-field stores' in packed_body, packed_body
    for name in ('pack_pair','pack_pair_initializers'):
        body = text.split(f'_{name}:\n', 1)[1].split(f'__size_{name}', 1)[0]
        assert body.count('shared packed bit-field payload') == 1, body
    upper_body = text.split('_update_upper:\n', 1)[1].split('__size_update_upper', 1)[0]
    assert upper_body.count('    xba\n')==2 and '    pha\n' not in upper_body, upper_body
    add = text.split('_add_upper:\n', 1)[1].split('__size_add_upper', 1)[0]
    assert 'adc a:.loword(_packed_upper+$0000)' in add and 'cmp #$8000' in add, add
    assert 'lsr a' not in add, add
    alias_body = text.split('_update_alias:\n', 1)[1].split('__size_update_alias', 1)[0]
    assert '[__arith_lhs]' not in alias_body, alias_body
    for name in ('multiply_bits','multiply_bits_reverse'):
        body = text.split(f'_{name}:\n', 1)[1].split(f'__size_{name}', 1)[0]
        assert 'two-bit word multiply' in body and '__mul16' not in body, body
    signed = text.split('_multiply_signed_bits:\n', 1)[1].split('__size_multiply_signed_bits', 1)[0]
    assert '__mul16' in signed and 'two-bit word multiply' not in signed, signed
    invalid = {
        'bitfield-address': ('struct S{int a:1;} s;void f(void){&s.a;}', 'address of a bit-field'),
        'bitfield-sizeof': ('struct S{int a:1;} s;int f(void){return sizeof(s.a);}', 'sizeof cannot'),
        'bitfield-zero': ('struct S{int a:0;};', 'invalid bit-field width'),
        'bitfield-type': ('struct S{float a:1;};', 'bit-field requires'),
    }
    for name, (code, message) in invalid.items():
        path = OUT / f'{name}.c'
        path.write_text(code)
        result = subprocess.run([str(ROOT / 'build/zicc.exe'), str(path), '-o',
                                 str(path.with_suffix('.s'))], capture_output=True, text=True)
        assert result.returncode and message in result.stderr, (name, result.stderr)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    support.OUT = OUT
    assertions()
    integer_conversions()
    absolute_values()
    variadic_formatting()
    allocation()
    aggregate_calls()
    bitfields()
    print('PASS: assertions, conversions, abs/labs, variadic formatting, allocation, aggregate calls and bit-fields')
