"""Call the added library routines through their C headers, including calls across banks."""
import os
import hashlib
import importlib.util
import json
import re
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'libc-new-check'
c.OUT.mkdir(parents=True, exist_ok=True)
FLAGS = ['-I', ROOT/'include']
OBJS = [*[ROOT/'build'/(n+'.o') for n in
        ('arithmetic', 'integers', 'ieee_engine', 'tables', 'io')], ROOT/'build/libc-new/libc.a', ROOT/'build/decimal.o']
report = {}
parser=argparse.ArgumentParser(description=__doc__)
selection=parser.add_mutually_exclusive_group()
selection.add_argument('--case')
selection.add_argument('--from',dest='resume')
args=parser.parse_args()
selected=args.case
started=not args.resume

def check(name, source, expected=0, extra=(), *, expected_abort=False):
    global started
    if name==args.resume:
        started=True
    if not started:
        return
    if selected and selected!=name:
        return
    _, rom, labels = c.compile_case(name, source, extra_objects=[*extra,*OBJS], flags=FLAGS)
    report[name] = c.emulate(rom, labels, expected, expected_abort=expected_abort, extra_checks=f"emu.addMemoryCallback(function() if not done then print('RESULT '..emu.getState()['cpu.a']) end end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})\n")
    report[name] += c.run(['python', ROOT/'tests/check-libc.py', '--pal-rom', rom], timeout=30).stdout
    print('PASS '+name+' NTSC/PAL', flush=True)
    return rom

HEADERS = r'''
#include <stddef.h>
#include <stdint.h>
#include <inttypes.h>
#include <limits.h>
#include <float.h>
#include <math.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>
'''

check('library_builtins', r'''
char buffer[16];
volatile unsigned size = 5;
extern int __builtin_memcmp(const void * __far a,const void * __far b,unsigned n);
static int strcat(void){return 7;}
int main(void){
    int strcmp=17;
    if(__builtin_memset(buffer, 'x', sizeof buffer)!=buffer)return 1;
    if(__builtin_memcpy(buffer,"abcd",size)!=buffer)return 2;
    if(__builtin_memmove(buffer+1,buffer,size)!=buffer+1)return 3;
    if(__builtin_memcmp(buffer+1,"abcd",size)||__builtin_strcmp(buffer+1,"abcd"))return 4;
    if(__builtin_memchr("abcd",'c',size)!="abcd"+2)return 5;
    void *near_match=__builtin_memchr(buffer+1,'c',size);
    if(near_match!=buffer+3)return 11;
    near_match=__builtin_memchr(buffer+1,'z',size);
    if(near_match)return 12;
    void * __far far_match=__builtin_memchr((void * __far)(buffer+1),'c',size);
    if(far_match!=(void * __far)(buffer+3))return 13;
    if(__builtin_strcpy(buffer,"ab")!=buffer||__builtin_strcat(buffer,"cd")!=buffer)return 6;
    if(__builtin_strncpy(buffer+4,"xyz",2)!=buffer+4)return 7;
    buffer[6]=0;
    if(__builtin_strncat(buffer,"123",2)!=buffer||__builtin_strlen(buffer)!=8)return 8;
    if(__builtin_strncmp(buffer,"abcdxy12",8)||__builtin_strspn(buffer,"abcd")!=4)return 9;
    if(__builtin_strcspn(buffer,"2")!=7||strcmp!=17||strcat()!=7)return 10;
    return 0;
}
''')

check('library_builtin_later_static', r'''
int compare(void){return __builtin_strcmp("a","a");}
static int strcmp(void){return 11;}
int main(void){return compare()||strcmp()!=11;}
''')

check('headers', HEADERS+r'''
#if CHAR_BIT != 8 || INT_MAX != 32767 || UINT32_MAX != 4294967295UL || UINT16_C(65535) != 65535U
#error incorrect limits
#endif
#ifndef INT64_MAX
#error missing 64-bit integer limits
#endif
#ifndef LDBL_MAX
#error missing long double limits
#endif
struct inner {char a;long b;};
struct outer {char a;struct inner b[3];};
unsigned offsets[offsetof(struct outer,b[2].b)==16?1:2];
bool global=256;
bool global_zero=-0.0;
struct adjacent {bool a;char b;};
struct adjacent pair;
bool identity(bool a){return a;}
volatile unsigned input;
volatile unsigned long wide;
volatile float f;
int main(void){
 bool b;bool *p=&b;float v;unsigned long *bits;
 if(sizeof(size_t)!=2||sizeof(ptrdiff_t)!=2||sizeof(int8_t)!=1||sizeof(int16_t)!=2||sizeof(int32_t)!=4)return 1;
 if(sizeof(intmax_t)!=8||sizeof(intptr_t)!=2||sizeof(max_align_t)!=4||sizeof(offsets)!=2)return 2;
 if(CHAR_MIN!=0||CHAR_MAX!=255||LONG_MIN!=-2147483647L-1L||sizeof(UINT16_C(65535))!=2||sizeof(INT32_C(123))!=4)return 3;
 if(!global||global_zero||sizeof(bool)!=1||true!=1||false!=0)return 4;
 pair.a=0;pair.b=127;if(pair.a)return 20;
 input=256;b=input;if(b!=1||identity(input)!=1)return 5;
 *p=0;if(b)return 6;++b;if(b!=1)return 7;b++;if(b!=1)return 8;
 wide=65536UL;b=wide;if(b!=1)return 9;
 f=-0.0F;b=f;if(b)return 10;f=0.25F;b=f;if(b!=1)return 11;
 b=p;if(b!=1)return 12;
 v=INFINITY;bits=(unsigned long *)&v;if(*bits!=0x7f800000UL)return 13;
 v=NAN;if(*bits!=0x7fc00000UL)return 14;
 v=FLT_MAX;if(*bits!=0x7f7fffffUL)return 15;
 v=FLT_MIN;if(*bits!=0x00800000UL)return 16;
 v=FLT_TRUE_MIN;if(*bits!=1UL)return 17;
 v=FLT_EPSILON;if(*bits!=0x34000000UL)return 18;
 if(DBL_MANT_DIG!=53||LDBL_MANT_DIG!=53||FLT_ROUNDS!=1||FLT_HAS_SUBNORM!=1)return 19;
 return 0;
}
''')

check('ctype', HEADERS+r'''
int main(void){
 int i,alpha,digit,space,print,graph,lower,upper;
 for(i=-1;i<256;++i){
  lower=i>=97&&i<=122;upper=i>=65&&i<=90;alpha=lower||upper;
  digit=i>=48&&i<=57;space=i==32||(i>=9&&i<=13);
  print=i>=32&&i<=126;graph=i>=33&&i<=126;
  if(!!isalpha(i)!=alpha||!!isalnum(i)!=(alpha||digit))return 1;
  if(!!islower(i)!=lower||!!isupper(i)!=upper||!!isdigit(i)!=digit)return 2;
  if(!!isspace(i)!=space||!!isblank(i)!=(i==9||i==32))return 3;
  if(!!iscntrl(i)!=((i>=0&&i<32)||i==127))return 4;
  if(!!isprint(i)!=print||!!isgraph(i)!=graph||!!ispunct(i)!=(graph&&!alpha&&!digit))return 5;
  if(!!isxdigit(i)!=(digit||(i>=65&&i<=70)||(i>=97&&i<=102)))return 6;
  if(tolower(i)!=(upper?i+32:i)||toupper(i)!=(lower?i-32:i))return 7;
 }
 return 0;
}
''')

STRINGS = HEADERS+r'''
char a[700],b[700];
int main(void){
 unsigned i,n,k;char *t;char * __far p;char * __far edge=(char * __far)0x7efffdUL;
 {char * __far l=(char * __far)0x7e3000UL,* __far r=(char * __far)0x7f3000UL;
  union {unsigned long bits;char * __far address;} alias;
  l[0]=r[0]='a';l[1]=r[1]='b';l[2]='c';r[2]='d';l[3]=r[3]=0;
  if(strcmp(l,r)>=0||strcmp(r,l)<=0)return 38;
  alias.bits=0x997e3000UL;if(strcmp(alias.address,l))return 39;
 }
 if(strlen("")||strlen("abc")!=3)return 1;
 for(n=0;n<12;++n){
  memset(a,85,20);if(strncpy(a+1,"abc",n)!=a+1||a[0]!=85||a[n+1]!=85)return 2;
  for(i=0;i<n;++i)if(a[i+1]!=(i<3?'a'+i:0))return 3;
  strcpy(a,"xy");if(strncat(a,"abcd",n)!=a||strlen(a)!=2+(n<4?n:4))return 4;
  if(strncmp("abc","abd",n)!=(n<3?0:-1))return 5;
  memset(a,85,20);k=strxfrm(a+1,"abc",n);if(k!=3||a[0]!=85)return 6;
  for(i=0;i<n&&i<4;++i)if(a[i+1]!=(i<3?'a'+i:0))return 7;
  if(a[(n<4?n:4)+1]!=85)return 8;
 }
 strcpy(a,"xy");if(strcat(a,"z")!=a||strcmp(a,"xyz"))return 9;
 if(strcoll("abc","abd")>=0||strcoll("abc","abc"))return 10;
 strcpy(a,"abca");p=a;
 if(strchr(a,'a')!=p||strrchr(a,'a')!=p+3||strchr(a,0)!=p+4||strrchr(a,0)!=p+4)return 11;
 if(strchr(a,0x0161)!=p||strchr(a,0x0100)!=p+4)return 11;
 if(strchr(a,'z')||strrchr("",'x')||strpbrk("abc","xyz"))return 12;
 if(strspn("aabcc","ab")!=3||strcspn("aabcc","bc")!=2||strspn("abc","")||strcspn("abc","")!=3)return 13;
 if(strpbrk(a,"cz")!=p+2||strstr(a,"bc")!=p+1||strstr(a,"")!=p||strstr(a,"abcd"))return 14;
 a[0]=128;a[1]=0;b[0]=127;b[1]=0;
 if(memcmp(a,b,1)<=0||memcmp(b,a,1)>=0||memcmp(a,b,0)||strncmp(a,b,1)<=0)return 15;
 a[1]=0;a[2]='z';if(memchr(a,0,3)!=(void * __far)(a+1)||memchr(a,'z',2))return 16;
 if(memchr((void * __far)0,0,0)||memcmp((void * __far)0,(void * __far)0,0))return 17;
 if(strncmp((char * __far)0,(char * __far)0,0)||strxfrm((char *)0,"abc",0)!=3)return 18;
 strcpy(a,",,one;two,,three;");t=strtok(a,",;");if(!t||strcmp(t,"one"))return 19;
 t=strtok(0,",");if(!t||strcmp(t,"two"))return 20;
 t=strtok(0,";");if(!t||strcmp(t,",three"))return 21;
 if(strtok(0,",")||strtok(0,","))return 22;
 strcpy(a,"one");if(strtok(a,"")!=a||strtok(0,""))return 23;
 for(i=0;i<600;++i)a[i]=(char)(i%255+1);a[600]=0;
 if(strlen(a)!=600||strncpy(b,a,601)!=b||memcmp(a,b,601))return 24;
 for(n=0;n<8;++n){
  for(i=0;i<8;++i)edge[i]=i==n?0:(char)255;
  if(strlen(edge)!=n)return 36;
 }
 edge[0]='a';edge[1]='b';edge[2]='c';edge[3]='a';edge[4]='d';edge[5]=0;
 if(strlen(edge)!=5||strchr(edge,'d')!=edge+4||strrchr(edge,'a')!=edge+3)return 25;
 if(strstr(edge,"cad")!=edge+2||strstr("abcad",edge)==0)return 26;
 if(strspn(edge,"abc")!=4||strcspn(edge,"d")!=4||strpbrk(edge,"d")!=edge+4)return 27;
 strcpy(a,"");strcat(a,edge);if(strcmp(a,"abcad")||strncmp(edge,"abcad",6)||memcmp(edge,"abcad",6))return 28;
 if(memchr(edge,'d',5)!=(void * __far)(edge+4))return 29;
 if(strspn("abcad",edge)!=5||strcspn("xxd",edge)!=2)return 30;
 if(strncpy((char *)0,(char * __far)0,0)!=0)return 31;
 {char *big=(char *)0x3000;char * __far other=(char * __far)0x7f0000UL;
  for(i=0;i<50000U;++i){big[i]='a';other[i]='a';}
  other[50000U]=0;if(strlen(other)!=50000U)return 37;
  if(memcmp(big,other,50000U)||strncmp(big,other,50000U))return 32;
  other[49999]='z';if(memcmp(big,other,50000U)>=0||strncmp(big,other,50000U)>=0)return 33;
  if(memchr(other,'z',50000U)!=(void * __far)(other+49999U))return 34;
  if(strncpy(big,other,50000U)!=big||big[49999]!='z')return 35;
  /* Adjacent far strings differ only after the 16-bit search index wraps */
  {char * __far text=(char * __far)0x7e3000UL;
   for(i=0;i<65535U;i++)text[i]='a';
   text[65535UL]='a';text[65536UL]='a';text[65537UL]=0;
   if(strlen(text)!=1)return 41;
   if(strcmp(text,text+1)<=0||strcmp(text+1,text)>=0)return 40;
  }
 }
 return 0;
}
'''
check('strings', STRINGS)

NEAR_COPY = r'''
#include <stddef.h>
void *memcpy(void *, const void *, __SIZE_TYPE__);
#ifdef CHECK_INDIRECT_COPY
void *(*volatile copy_bytes)(void *, const void *, size_t) = memcpy;
#else
#define copy_bytes memcpy
#endif
static unsigned char copy_src[12],copy_dst[12];
int near_copy_test(void){
 unsigned i;
 for(i=0;i<12;++i){copy_src[i]=(unsigned char)(9+17*i);copy_dst[i]=85;}
 if(memcpy(copy_dst+1,copy_src,10)!=copy_dst+1 || copy_dst[0]!=85 || copy_dst[11]!=85)return 40;
 for(i=0;i<10;++i)if(copy_dst[i+1]!=copy_src[i])return 41;
 if(copy_bytes(copy_dst,copy_src+3,4)!=copy_dst)return 42;
 for(i=0;i<4;++i)if(copy_dst[i]!=copy_src[i+3])return 43;
 if(copy_bytes(copy_dst,copy_src,0)!=copy_dst||copy_dst[0]!=copy_src[3])return 44;
 return 0;
}
'''
check('near_memcpy', NEAR_COPY+'int main(void){return near_copy_test();}')

FORMAT = HEADERS+r'''
char out[160],text[8];
int main(void){
 unsigned n,i;int result;char * __far edge=(char * __far)0x7efffcUL;
 strcpy(text,"near");
 result=sprintf(out,"%d|%u|%ld|%lu",(-32767-1),65535U,-2147483647L-1L,4294967295UL);
 if(result!=35)return 1000+result;
 if(strcmp(out,"-32768|65535|-2147483648|4294967295"))return 2;
 if(sprintf(out,"[%05d][%-5.2s][%S]%%",-12,text,"far")!=20||strcmp(out,"[-0012][ne   ][far]%"))return 3;
 for(n=0;n<10;++n){
  memset(out,85,20);result=snprintf(out+1,n,"%s:%d",text,123);
  if(result!=8||out[0]!=85||out[(n?n:0)+1]!=85)return 4;
  if(n){for(i=0;i<n-1&&i<8;++i)if(out[i+1]!="near:123"[i])return 5;
   if(out[1+(n-1<8?n-1:8)]!=0)return 6;}
 }
 if(snprintf(0,0,"abc%d",123)!=6||snprintf(0,0,"")!=0)return 7;
 if(sprintf(out,"")!=0||out[0])return 8;
 out[0]='!';out[5]='?';
 if(sprintf(out+1,"foo\0bar")!=3||strcmp(out+1,"foo")||out[0]!='!'||out[5]!='?')return 15;
 if(sprintf(out+1,"xy")!=2||strcmp(out+1,"xy")||out[0]!='!'||out[5]!='?')return 16;
 n=0;
 if(sprintf(out,"ok",++n)!=2||n!=1||strcmp(out,"ok"))return 17;
 if(snprintf(out,4,"%c%c%c",0,'x',255)!=3||out[0]!=0||out[1]!='x'||(unsigned char)out[2]!=255||out[3])return 9;
 if(sprintf(out,"%.2f|%.3g",1.25,123.0)!=8||strcmp(out,"1.25|123"))return 10;
 edge[0]='A';edge[1]='%';edge[2]='d';edge[3]='Z';edge[4]=0;
 if(snprintf(out,160,edge,42)!=4||strcmp(out,"A42Z"))return 11;
 if(snprintf(out,2,"%q")!=-1||out[0]!='?'||out[1])return 12;
 {char *big=(char *)0x3000;for(i=0;i<32768U;++i)big[i]='x';big[32768U]=0;
  if(snprintf(out,2,"%s",big)!=-1||out[0]!='x'||out[1])return 13;
  big[32767U]=0;if(snprintf(0,0,"%s",big)!=32767)return 14;
 }
 return 0;
}
'''
check('format', FORMAT)

if not selected or selected=='preservation':
    probe=c.OUT/'preservation-probe.o'
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',probe,ROOT/'tests/libc_new_preserve.s'])
    check('preservation','int libc_new_preserve(void);int main(void){return libc_new_preserve();}',extra=[probe])

for function, expected in [('abort', 0), ('__builtin_abort', 0), ('exit', 37), ('quick_exit', 39), ('_Exit', 41)]:
    expected_abort = function in ('abort', '__builtin_abort')
    call_args = '' if expected_abort else str(expected)
    check('terminate_'+function, HEADERS+f'int main(void){{{function}({call_args});return 99;}}', expected, expected_abort=expected_abort)

# Exercise the same assembly through every automatic ROM allocation ABI
for stage in (1, 2, 3, 4):
    if args.resume=='stage'+str(stage):
        started=True
    if not started:
        continue
    if selected and selected!='stage'+str(stage):
        continue
    source = c.OUT/f'stage{stage}.c'
    source.write_text(STRINGS.replace('int main(void)', 'int string_test(void)')+
                      FORMAT.replace('int main(void)', 'int format_test(void)')+
                      'int near_copy_test(void);int main(void){int r=string_test();if(r)return r;'
                      'r=format_test();return r?r:near_copy_test();}')
    copy_source = c.OUT/f'stage{stage}-near-copy.c'
    copy_source.write_text('#define CHECK_INDIRECT_COPY\n'+NEAR_COPY)
    raw = c.OUT/f'stage{stage}.raw'
    c.run(['python', ROOT/'tools/build-rom.py', source, copy_source, '-o', raw, '--stage', str(stage)], timeout=120)
    rom = raw.with_suffix('.sfc')
    c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
    labels = {n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
    report['stage'+str(stage)] = c.emulate(rom, labels, 0)
    print('PASS strings allocation stage '+str(stage), flush=True)

report['hashes'] = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in [ROOT/'build/zicc.exe', ROOT/'build/libc-new/libc.a',
                              *sorted((ROOT/'include').glob('*.h')),
                              *sorted((ROOT/'runtime/strings').glob('*.s')),
                              *sorted((ROOT/'runtime/ctype').glob('*.s')),
                              *[ROOT/'runtime'/n for n in ('terminate.s','console.s','sprintf.s')]]}
(c.OUT/'results.json').write_text(json.dumps(report, indent=2)+'\n')
