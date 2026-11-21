"""Check how the compiler lays out 64-bit integer types and stores integer constants."""
import os
import importlib.util
from pathlib import Path
import random
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'int64-frontend-check'
c.OUT.mkdir(parents=True,exist_ok=True)

SOURCE = r'''
unsigned long long a=0xfedcba9876543210ULL;
long long b=-123456789012345LL;
unsigned long long c=4294967296;
unsigned long long d=18446744073709551615ull;
long long sign_extended=-1;
unsigned long long numbers[2]={1LL,0x8000000000000000ull};
struct W { char c; unsigned long long n; } record={0x33,0x0123456789abcdefULL};
unsigned long long expr=(0x12345678ULL<<32)|0x9abcdef0UL;
unsigned long long divexpr=0xffffffffffffffffULL/3ULL;
long long negexpr=(-9223372036854775807LL-1LL)/2LL;
unsigned long long wrap=0xffffffffffffffffULL+2ULL;
unsigned long long lazy=0 ? (1ULL/0ULL) : (7ULL<<40);
int comparison=(0x100000000ULL>0xffffffffUL) && (-5LL<3UL);
unsigned int narrow=(1ULL<<40)+0x1234U;
enum wide_enum { WIDE_TRUE=(1ULL<<40)>0, WIDE_NEG=(-5LL<3UL) };
int main(void){
    unsigned char *p=(unsigned char *)&a;
    unsigned char *q=(unsigned char *)&b;
    unsigned char *r=(unsigned char *)&record;
    unsigned char *s=(unsigned char *)&numbers;
    unsigned char *t=(unsigned char *)&sign_extended;
    unsigned char *u=(unsigned char *)&expr;
    unsigned char *v=(unsigned char *)&divexpr;
    unsigned char *w=(unsigned char *)&negexpr;
    unsigned char *x=(unsigned char *)&wrap;
    unsigned char *y=(unsigned char *)&lazy;
    if(sizeof(long long)!=8 || sizeof(unsigned long long int)!=8 || sizeof(a)!=8) return 1;
    if(sizeof(4294967295)!=8 || sizeof(0xffffffff)!=4 || sizeof(1UL)!=4) return 2;
    if(sizeof(0xffffffffffffffff)!=8 || sizeof(123LL)!=8 || sizeof(record)!=10) return 3;
    if(p[0]!=0x10 || p[1]!=0x32 || p[6]!=0xdc || p[7]!=0xfe) return 4;
    if(q[0]!=0x87 || q[1]!=0x20 || q[6]!=0xff || q[7]!=0xff) return 5;
    if(r[0]!=0x33 || r[2]!=0xef || r[9]!=0x01) return 6;
    if(s[0]!=1 || s[7]!=0 || s[8]!=0 || s[15]!=0x80) return 7;
    if(t[0]!=0xff || t[3]!=0xff || t[4]!=0xff || t[7]!=0xff) return 8;
    if(u[0]!=0xf0 || u[3]!=0x9a || u[4]!=0x78 || u[7]!=0x12) return 9;
    if(v[0]!=0x55 || v[3]!=0x55 || v[7]!=0x55) return 10;
    if(w[0]!=0 || w[6]!=0 || w[7]!=0xc0) return 11;
    if(x[0]!=1 || x[7]!=0 || y[5]!=7 || y[7]!=0) return 12;
    if(comparison!=1 || narrow!=0x1234U || WIDE_TRUE!=1 || WIDE_NEG!=1) return 13;
    return 0;
}
'''

HEADERS = r'''
#include <stdint.h>
#include <limits.h>
#include <inttypes.h>
const char scan_formats[] = "%" SCNd64 " %" SCNi64 " %" SCNo64 " %" SCNu64 " %" SCNx64;
int64_t minimum=INT64_MIN;
int64_t maximum=LLONG_MAX;
uint64_t maximum_unsigned=UINT64_MAX;
int_least64_t least=INT64_C(0x123456789abcdef);
uint_fast64_t fast=UINT64_C(0xfedcba9876543210);
int main(void){
    unsigned char *a=(unsigned char *)&minimum,*b=(unsigned char *)&maximum;
    unsigned char *c=(unsigned char *)&maximum_unsigned,*d=(unsigned char *)&least,*e=(unsigned char *)&fast;
    if(sizeof(int64_t)!=8||sizeof(uint64_t)!=8||sizeof(int_least64_t)!=8||sizeof(uint_least64_t)!=8||sizeof(int_fast64_t)!=8||sizeof(uint_fast64_t)!=8)return 1;
    if(INT64_WIDTH!=64||UINT64_WIDTH!=64||LLONG_WIDTH!=64||ULLONG_WIDTH!=64||INT_FAST64_WIDTH!=64||UINT_LEAST64_WIDTH!=64)return 2;
    if(a[0]!=0||a[7]!=0x80||b[0]!=0xff||b[7]!=0x7f||c[0]!=0xff||c[7]!=0xff)return 3;
    if(d[0]!=0xef||d[7]!=1||e[0]!=0x10||e[7]!=0xfe)return 4;
    if(scan_formats[0]!='%'||scan_formats[1]!='l'||scan_formats[2]!='l'||scan_formats[3]!='d'||
       scan_formats[8]!='i'||scan_formats[13]!='o'||scan_formats[18]!='u'||scan_formats[23]!='x')return 5;
    return 0;
}
'''

BINARY64_STATIC = r'''
long double values[]={1.0L,-0.0L,1.0000000000000002L,0x1.0000000000001p0L,
                      4.9406564584124654e-324L,1.7976931348623157e308L,-42,
                      9007199254740993ULL,1.0L+2.0L,(1.0L/3.0L)*3.0L,
                      1.5L+3,1 ? 6.25L : 1.0L/0.0L};
struct Entry {char tag; double long value;} entry={7,3.5L};
long long signed_cast=(long long)-123456789.75L;
unsigned long long unsigned_cast=(unsigned long long)18446744073709549568.0L;
long long minimum_cast=(long long)-9223372036854775808.0L;
unsigned short negative_fraction=(unsigned short)-0.5L;
int below_min_fraction=(int)-32768.75L;
int compare_cast=1.5L<2.0L;
float float_cast=(float)1.25L;
unsigned long long exact_choice=(1.0L<2.0L)?0xffffffffffffffffULL:0ULL;
unsigned long long exact_arithmetic=0xffffffffffffffffULL-(1.0L<2.0L);
unsigned long long exact_shift=1ULL<<((1.0L<2.0L)+1);
long double exact_to_double=(1.0L<2.0L)?0xfffffffffffff000ULL:0ULL;
float mixed_float=(float)0.1L+0.2F;
int main(void){
    if(sizeof(long double)!=8||sizeof(double long)!=8||sizeof(values)!=96||sizeof(entry)!=10)return 1;
    if(signed_cast!=-123456789LL||unsigned_cast!=18446744073709549568ULL||compare_cast!=1||
       minimum_cast!=(-9223372036854775807LL-1LL)||negative_fraction!=0||below_min_fraction!=-32768||
       exact_choice!=0xffffffffffffffffULL||exact_arithmetic!=0xfffffffffffffffeULL||exact_shift!=4ULL)return 2;
    return 0;
}
'''


def main():
    _,rom,labels=c.compile_case('layout',SOURCE)
    c.emulate(rom,labels,0)
    _,rom,labels=c.compile_case('headers',HEADERS,flags=['-I',ROOT/'include'])
    c.emulate(rom,labels,0)
    _,rom,labels=c.compile_case('binary64-static',BINARY64_STATIC,extra_objects=[ROOT/'build/libc.a'])
    values=[1.0,-0.0,1.0000000000000002,float.fromhex('0x1.0000000000001p0'),
            float.fromhex('0x0.0000000000001p-1022'),float.fromhex('0x1.fffffffffffffp1023'),-42.0,float(9007199254740993),
            3.0,(1.0/3.0)*3.0,4.5,6.25]
    expected=b''.join(struct.pack('<d',x) for x in values)
    entry=bytes([7,0])+struct.pack('<d',3.5)
    checks=['local once=false','emu.addMemoryCallback(function()',' if once then return end',' once=true']
    f32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
    for name,image in (('values',expected),('entry',entry),('float_cast',struct.pack('<f',1.25)),
                       ('mixed_float',struct.pack('<f',f32(0.1)+f32(0.2))),
                       ('exact_to_double',struct.pack('<d',float(0xfffffffffffff000)))):
        address=labels[name]&0x1ffff
        for i,byte in enumerate(image):
            checks.append(f" require_value(emu.read({address+i},emu.memType.snesWorkRam,false)=={byte},'{name} byte {i}')")
    checks.append(f"end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})")
    c.emulate(rom,labels,0,extra_checks='\n'.join(checks))
    rng=random.Random(0x64656e)
    mask=(1<<64)-1
    cases=[]
    for _ in range(36):
        a,b=rng.getrandbits(64),rng.getrandbits(64) or 1
        for op,result in [('+',(a+b)&mask),('-',(a-b)&mask),('*',(a*b)&mask),
                          ('/',a//b),('%',a%b),('&',a&b),('|',a|b),('^',a^b)]:
            cases.append((f'(0x{a:016x}ULL {op} 0x{b:016x}ULL)',result))
    for shift in range(64):
        a=rng.getrandbits(64)
        cases.append((f'(0x{a:016x}ULL<<{shift})',(a<<shift)&mask))
        cases.append((f'(0x{a:016x}ULL>>{shift})',a>>shift))
    for _ in range(48):
        a=rng.randrange(-(1<<61),1<<61);b=rng.randrange(-65535,65536) or 1
        q=abs(a)//abs(b)*(-1 if (a<0)!=(b<0) else 1)
        for op,result in [('/',q),('%',a-q*b)]:
            cases.append((f'({a}LL {op} {b}LL)',result&mask))
    for _ in range(36):
        a=rng.randrange(-1000000000,1000000000);b=rng.randrange(-1000000000,1000000000)
        shift=rng.randrange(64)
        for op,result in [('+',a+b),('-',a-b),('*',a*b),('>>',a>>shift),
                          ('<',int(a<b)),('>=',int(a>=b))]:
            right=shift if op=='>>' else b
            cases.append((f'({a}LL {op} {right}LL)',result&mask))
    source='unsigned long long values[]={\n'+',\n'.join(e for e,_ in cases)+'\n}; int main(void){return 0;}'
    _,rom,labels=c.compile_case('vectors',source)
    expected=','.join(str((value>>(8*i))&255) for _,value in cases for i in range(8))
    start=labels['values']&0x1ffff
    checks=f'''
local expected={{{expected}}}
emu.addMemoryCallback(function()
 for i=1,#expected do
  if emu.read({start}+i-1,emu.memType.snesWorkRam,false)~=expected[i] then
   require_value(false,'wide initializer byte '..i); break
  end
 end
end,emu.callbackType.exec,{labels['main']},{labels['main']})
'''
    c.emulate(rom,labels,0,extra_checks=checks)
    invalid={
        'overflow_add':'long long x=9223372036854775807LL+1LL; int main(void){return 0;}',
        'overflow_mul':'long long x=0x4000000000000000LL*2LL; int main(void){return 0;}',
        'overflow_div':'long long x=(-9223372036854775807LL-1LL)/-1LL; int main(void){return 0;}',
        'bad_shift':'unsigned long long x=1ULL<<64; int main(void){return 0;}',
        'negative_shift':'long long x=-1LL<<1; int main(void){return 0;}',
        'zero_div':'long long x=1LL/0LL; int main(void){return 0;}',
        'array_overflow':'int x[1ULL<<40]; int main(void){return 0;}',
        'suffix':'int main(void){return sizeof(1lL);}',
        'decimal_overflow':'int main(void){return sizeof(18446744073709551615LL);}',
        'pointer_truncation':'int *p=(int *)0x100000000ULL; int main(void){return 0;}',
        'wide_index':'long long a[2]; int main(void){a[0x100000000ULL]=1LL;return 0;}',
        'duplicate_wide_case':'int main(void){unsigned long long x=0;switch(x){case -1LL:break;case 0xffffffffffffffffULL:break;}return 0;}',
        'duplicate_narrow_case':'int main(void){unsigned x=0;switch(x){case 0:break;case 0x10000ULL:break;}return 0;}',
        'binary64_divzero':'long double x=1.0L/0.0L;int main(void){return 0;}',
        'binary64_narrow_overflow':'int x=(int)32768.0L;int main(void){return 0;}',
        'binary64_float_index':'int a[2];int main(void){return a[1.0L];}',
        'binary64_bad_specifier':'unsigned long double x;int main(void){return 0;}',
    }
    for name,source in invalid.items():
        path=c.OUT/(name+'.c');path.write_text(source)
        result=c.run([ROOT/'build/zicc.exe',path,'-o',path.with_suffix('.s')],expected=1)
        assert 'error:' in result.stderr,(name,result.stderr)
    print(f'PASS: 64-bit syntax, layout, {len(cases)} arithmetic initializers and guarded unsupported uses')


if __name__=='__main__':
    main()
