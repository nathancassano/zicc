"""Call the public C library from separately compiled C programs and run them on the SNES."""
import os
import importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'libc-check';c.OUT.mkdir(parents=True,exist_ok=True)
# Core instances are isolated by process; run each PAL ROM in its own worker
if len(sys.argv)>1 and sys.argv[1]=='--pal-rom':
 sys.path.insert(0,str(ROOT/'tools'))
 from mesen_core import Core,SnesConfig
 rom=Path(sys.argv[2]);home=rom.parent/(rom.stem+'-pal')
 script=rom.with_suffix('.lua').read_text().replace("print('PASS')","emu.log('PASS')").replace("emu.stop(bad and 1 or 0)","emu.breakExecution()")
 core=Core(home)
 try:
  config=SnesConfig();config.Region=2;config.Port1.Type=1;config.DisableFrameSkipping=True;config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
  for i in range(8):config.ChannelVolumes[i]=100
  core.bind('SetSnesConfig',None,SnesConfig)(config)
  core.load(rom,home/'test.lua',script);core.start();core.wait_for('PASS',20)
  log=core.log();assert 'FAIL' not in log,log
  print('PASS PAL '+rom.stem)
 finally:core.close_with_log(home/'result.log')
 sys.exit(0)
original_emulate=c.emulate
def both_regions(rom,labels,expected):
 result=original_emulate(rom,labels,expected)
 result+=c.run([sys.executable,__file__,'--pal-rom',rom],timeout=30).stdout
 return result
c.emulate=both_regions
NEAR_CAPACITY=0x10000-0x0500
SOURCE=r"""
void *malloc(unsigned size);
int main(void){
 unsigned char *a,*b,*p;unsigned i,count;
 if(malloc(0)!=0 || malloc(65535u)!=0 || malloc(65533u)!=0)return 1;
 a=malloc(1);b=malloc(3);
 if(!a||!b||a==b||((unsigned)a&1)||((unsigned)b&1))return 2;
 a[0]=91;b[0]=17;b[1]=29;b[2]=43;
 if(a[0]!=91||b[0]!=17||b[1]!=29||b[2]!=43)return 3;
 p=malloc(40000u);if(!p)return 4;
 for(i=0;i<40000u;++i)p[i]=(unsigned char)i;
 for(i=0;i<40000u;++i)if(p[i]!=(unsigned char)i)return 5;
 count=0;while(malloc(1000u))++count;
 if(count!=EXPECTED_COUNT||malloc(60000u)!=0)return 6;
 while(malloc(1)){}
 if(malloc(1)!=0||malloc(2)!=0||a[0]!=91||b[2]!=43)return 7;
 return 0;
}
""".replace('EXPECTED_COUNT',str((NEAR_CAPACITY-2-4-6-40002)//1002))
_,rom,labels=c.compile_case('malloc',SOURCE,extra_objects=[ROOT/'build/libc.a',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
print(c.emulate(rom,labels,0))

for size in (NEAR_CAPACITY-6,NEAR_CAPACITY-4):
 body='return malloc(1)==0 || malloc(1)!=0;' if size==NEAR_CAPACITY-6 else 'return malloc(1)!=0;'
 source='void *malloc(unsigned n);unsigned char reserved[14000],b[14000],d[14000],tail[%d];int main(void){%s}'%(size-42000,body)
 _,rom,labels=c.compile_case('full_'+str(size),source,extra_objects=[ROOT/'build/libc.a'])
 print(c.emulate(rom,labels,0))

FREE=r"""
void *malloc(unsigned n);void free(void *p);
int main(void){
 char *a,*b,*d,*tail,*joined;unsigned i;
 free((void *)0);
 a=malloc(100);b=malloc(200);d=malloc(300);tail=malloc(400);
 if(!a||!b||!d||!tail)return 1;
 for(i=0;i<400;++i)tail[i]=(char)i;
 free(b);joined=malloc(200);if(joined!=b)return 2;
 free(a);free(d);free(joined);
 joined=malloc(604);if(joined!=a)return 3;
 for(i=0;i<400;++i)if(tail[i]!=(char)i)return 4;
 free(tail);free(joined);
 a=malloc(57000u);if(!a)return 5;free(a);
 for(i=0;i<1000;++i){a=malloc((i&31)+1);if(!a)return 6;free(a);}
 a=malloc(57000u);if(!a)return 7;free(a);
 return 0;
}
"""
_,rom,labels=c.compile_case('free',FREE,extra_objects=[ROOT/'build/libc.a',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
print(c.emulate(rom,labels,0))

COPY=r"""
char *strcpy(char *d,const char * __far s);
char destination[600],source[520];
int main(void){
 unsigned i;char *p;char * __far edge=(char * __far)0x7efffeUL;
 for(i=0;i<600;++i)destination[i]=85;
 if(strcpy(destination+1,"")!=destination+1||destination[1]!=0||destination[0]!=85||destination[2]!=85)return 1;
 if(strcpy(destination,"Copy nine")!=destination||destination[8]!='e'||destination[9]!=0||destination[10]!=85)return 2;
 for(i=0;i<519;++i)source[i]=(char)((i%255)+1);source[519]=0;
 p=strcpy(destination,source);if(p!=destination||destination[520]!=85)return 3;
 for(i=0;i<520;++i)if(destination[i]!=source[i])return 4;
 edge[0]='X';edge[1]=(char)128;edge[2]='Y';edge[3]=0;
 strcpy(destination,edge);
 if(destination[0]!='X'||(unsigned char)destination[1]!=128||destination[2]!='Y'||destination[3]!=0)return 5;
 return 0;
}
"""
_,rom,labels=c.compile_case('strcpy',COPY,extra_objects=[ROOT/'build/libc.a',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
print(c.emulate(rom,labels,0))

COMPARE=r"""
int strcmp(const char * __far a,const char * __far b);
char a[600],b[600];
int main(void){
 unsigned i;char * __far edge=(char * __far)0x7effffUL;
 if(strcmp("","")||strcmp("abc","abc"))return 1;
 if(strcmp("","a")>=0||strcmp("a","")<=0)return 2;
 if(strcmp("abc","abcd")>=0||strcmp("abcd","abc")<=0)return 3;
 if(strcmp("abc","abd")>=0||strcmp("abd","abc")<=0)return 4;
 for(i=0;i<599;++i)a[i]=b[i]=(char)((i%255)+1);a[599]=b[599]=0;
 if(strcmp(a,b))return 5;b[598]=1;if(strcmp(a,b)<=0||strcmp(b,a)>=0)return 6;
 a[0]=(char)128;a[1]=0;b[0]=127;b[1]=0;
 if(strcmp(a,b)<=0||strcmp(b,a)>=0)return 7;
 edge[0]=(char)128;edge[1]=0;if(strcmp(edge,a)||strcmp(a,edge))return 8;
 return 0;
}
"""
_,rom,labels=c.compile_case('strcmp',COMPARE,extra_objects=[ROOT/'build/libc.a',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
print(c.emulate(rom,labels,0))

MEMORY=r"""
#include <stdlib.h>
#include <string.h>
unsigned char a[1100],b[1100];
static union { unsigned char buf[16]; long long align; } member;
int main(void){
 unsigned i,n,k,shift;void *p;
 unsigned char * __far edge=(unsigned char * __far)0x7efff0UL;
 for(k=0;k<9;++k){
  n=k==0?0:k==1?1:k==2?2:k==3?3:k==4?255:k==5?256:k==6?257:k==7?1023:1024;
  for(i=0;i<1100;++i){a[i]=85;b[i]=(unsigned char)(i*13+7);}
  p=memset(a+1,0x1a3,n);if(p!=a+1||a[0]!=85||a[n+1]!=85)return 10;
  for(i=0;i<n;++i)if(a[i+1]!=163)return 11;
  p=memcpy(a+1,b,n);if(p!=a+1||a[0]!=85||a[n+1]!=85)return 12;
  for(i=0;i<n;++i)if(a[i+1]!=b[i])return 13;
  for(shift=0;shift<5;++shift){
   for(i=0;i<1100;++i)a[i]=b[i];
   if(memmove(a+shift,a,n)!=a+shift)return 14;
   for(i=0;i<1100;++i)if(a[i]!=(i>=shift&&i-shift<n?b[i-shift]:b[i]))return 15;
   for(i=0;i<1100;++i)a[i]=b[i];
   if(memmove(a,a+shift,n)!=a)return 16;
   for(i=0;i<1100;++i)if(a[i]!=(i<n?b[i+shift]:b[i]))return 17;
  }
 }
 if(memcpy(a,"ROM source",11)!=a||a[0]!='R'||a[9]!='e'||a[10]!=0)return 18;
 if(memmove(a,"ROM source",11)!=a||a[0]!='R'||a[10]!=0)return 19;
 for(i=0;i<64;++i)edge[i]=(unsigned char)(i+128);
 for(n=15;n<=33;++n){
  memset(a,85,65);if(memcpy(a+1,edge,n)!=a+1||a[0]!=85||a[n+1]!=85)return 20;
  for(i=0;i<n;++i)if(a[i+1]!=(unsigned char)(i+128))return 21;
  if(memmove(a+1,edge,n)!=a+1)return 22;
 }
 if(memset(a,-1,2)!=a||a[0]!=255||a[1]!=255)return 23;
 if(memcpy(a,(void * __far)0,0)!=a||memmove(a,(void * __far)0,0)!=a)return 24;
 a[4]=41;i=324;
 if(memset(a+1,++i,3)!=a+1||i!=325||a[0]!=255||a[4]!=41)return 25;
 if(a[1]!=69||a[2]!=69||a[3]!=69)return 26;
 for(i=1;i<4;++i){
  n=0x1c3u+i;
  p=memset(member.buf+i,++n,8);
  if(p!=member.buf+i||n!=0x1c4u+i)return 27;
  for(k=0;k<8;++k)if(member.buf[i+k]!=(unsigned char)n)return 28;
  p=memset(member.buf+i,n,0);
  if(p!=member.buf+i)return 29;
 }
 i=2;p=memset(member.buf+i++,0x5a,1);
 if(p!=member.buf+2||p==member.buf+i||member.buf[2]!=0x5a)return 30;
 return 0;
}
"""
_,rom,labels=c.compile_case('memory',MEMORY,extra_objects=[ROOT/'build/libc.a',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
assert '; inline short memset: 3 bytes' in rom.with_suffix('.s').read_text()
assert '; inline short memset: 8 bytes' in rom.with_suffix('.s').read_text()
print(c.emulate(rom,labels,0))

LARGE=r"""
#include <string.h>
int main(void){
 unsigned i;unsigned char *d=(unsigned char *)0x3000;
 unsigned char * __far s=(unsigned char * __far)0x7f0000UL;
 for(i=0;i<50000u;++i)s[i]=(unsigned char)(i+17);
 if(memcpy(d,s,50000u)!=d)return 30;
 for(i=0;i<50000u;++i)if(d[i]!=(unsigned char)(i+17))return 31;
 if(memset(d,0x1234,50000u)!=d)return 32;
 for(i=0;i<50000u;++i)if(d[i]!=52)return 33;
 for(i=0;i<50000u;++i)d[i]=(unsigned char)(i+17);
 if(memmove(d+1,d,49999u)!=d+1)return 34;
 if(d[0]!=17)return 35;
 for(i=1;i<50000u;++i)if(d[i]!=(unsigned char)(i+16))return 36;
 d=(unsigned char *)0xfff0;
 if(memset(d,0x5a,16)!=d)return 37;
 for(i=0;i<16;++i)if(d[i]!=0x5a)return 38;
 if(memcpy(d,s,16)!=d)return 39;
 for(i=0;i<16;++i)if(d[i]!=(unsigned char)(i+17))return 40;
 if(memmove(d+1,d,15)!=d+1)return 41;
 for(i=1;i<16;++i)if(d[i]!=(unsigned char)(i+16))return 42;
 return 0;
}
"""
_,rom,labels=c.compile_case('memory_large',LARGE,extra_objects=[ROOT/'build/libc.a',ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
print(c.emulate(rom,labels,0))

probe=c.OUT/'libc_preserve.o'
c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',probe,ROOT/'tests/libc_preserve.s'])
_,rom,labels=c.compile_case('preserve','int libc_preserve(void);int main(void){return libc_preserve();}',extra_objects=[probe,ROOT/'build/libc.a'])
print(c.emulate(rom,labels,0))
probe=c.OUT/'memory-preserve-probe.o'
c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',probe,ROOT/'tests/memory_preserve.s'])
_,rom,labels=c.compile_case('memory_preserve','int memory_preserve(void);int main(void){return memory_preserve();}',extra_objects=[probe,ROOT/'build/libc.a'])
print(c.emulate(rom,labels,0))
(c.OUT/'results.json').write_text(json.dumps({'regions':['ntsc','pal'],'malloc':'PASS','free':'PASS','strcpy':'PASS','strcmp':'PASS','memcpy':'PASS','memset':'PASS','memmove':'PASS','scratch_and_y':'PASS','nested_memory_nmi':'PASS'})+'\n')
