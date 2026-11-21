"""Check when expressions can share a condition and when the compiler can drop unused storage or call setup."""
from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('cleanup_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
SOURCE=r'''
#include <stdint.h>
#ifndef __ZICC__
#define __far
#endif
volatile uint16_t opaque,io;
uint16_t flags[8],data[16],calls,guard_word;
__noinline void shared(void){uint8_t i;uint16_t x,y;
 for(i=0;i<8;i++){
  x=flags[i]?91:199;y=flags[i]?17:37;
  if(data[i]>x)data[i]=x;if(data[i+8]>y)data[i+8]=y;
 }
}
__noinline uint16_t mutation(uint16_t x){uint16_t y;x=x?0:1;y=x?17:37;return x+y;}
__noinline uint16_t predicate(void){uint16_t x=calls;calls++;return x&1;}
__noinline uint16_t call_choices(void){uint16_t x,y;x=predicate()?91:199;y=predicate()?17:37;return x^y;}
__noinline uint16_t volatile_choices(void){uint16_t x,y;x=io?91:199;y=io?17:37;return x^y;}
__noinline uint16_t combine(uint16_t a,uint16_t b,uint16_t c){return a^(uint16_t)(b+c);}
__noinline uint16_t lifetimes(uint16_t seed){uint16_t result,live=seed^23130;
 {uint16_t a=seed+3,b=seed^52;result=combine(a,b,seed+7);}
 {uint16_t a=seed+11,b=seed^25;result+=combine(a,b,seed+13);}
 return result^live;
}
__noinline void alter(uint16_t *p,uint16_t v){*p+=v;}
__noinline uint16_t single_written_value(void){uint16_t value,i;
 for(i=0;i<2;i++){
  if(guard_word){if(value!=19)return 7;}
  else{value=19;guard_word++;}
 }
 return 0;
}
__noinline uint16_t other_written_values(uint16_t seed){uint16_t value=19,escaped_value=19;
 if(seed&1)value=23;
 alter(&escaped_value,3);
 if(seed&2)value++;
 return value+escaped_value;
}
__noinline uint16_t byte_pair(uint16_t high,uint16_t low){return (high<<8)|low;}
__noinline uint16_t xor_tail(uint16_t seed){uint8_t a=seed,b=seed+1;
 a^=b;b^=a;a^=b;return byte_pair(a,b);
}
__noinline uint16_t xor_spelled(uint16_t seed){uint8_t a=seed,b=seed+1;
 a=(uint8_t)(b^a);b=b^a;a=a^b;return byte_pair(a,b);
}
__noinline uint16_t xor_nonterminal(uint16_t seed){uint8_t a=seed,b=seed+1;
 if(seed&1){a^=b;b^=a;a^=b;}
 return byte_pair(a,b);
}
__noinline uint16_t xor_escaped(uint16_t seed){uint8_t a=seed,b=seed+1,*p=&a;
 a^=b;b^=a;a^=b;return byte_pair(*p,b);
}
__noinline uint16_t escaped(uint16_t seed){uint16_t pinned=seed,result;
 {uint16_t a=seed+17;alter(&pinned,a);result=combine(a,pinned,seed);}
 {uint16_t a=seed+29;alter(&pinned,a);result+=combine(a,pinned,seed);}
 return result^pinned;
}
__noinline uint16_t loop_lifetimes(uint16_t seed){uint16_t k,total=seed;
 for(k=0;k<6;k++){
  uint16_t a=seed+k,b=combine(a,k,total);
  if(k==2)continue;
  {uint16_t c=combine(b,a,k);total+=c;}
  if(k==4&&seed&1)break;
 }
 return total;
}
__noinline uint32_t wide_call(uint16_t a,uint16_t b,uint16_t c,uint16_t d){calls++;return ((uint32_t)(a^b)<<16)|(uint16_t)(c+d);}
__noinline uint16_t projections(uint32_t v){return (uint16_t)v^(uint16_t)(v>>16)^(uint8_t)(v>>16);}
volatile uint32_t wide_io;
__noinline uint16_t volatile_projection(void){return (uint16_t)wide_io;}
uint32_t wide_source;
uint16_t narrowed;
__noinline void narrow_copy(void){int32_t saved=(int32_t)wide_source;narrowed=(uint16_t)saved;}
__noinline uint16_t snapshot_before_write(void){uint32_t saved=wide_source;return (wide_source=17,(uint16_t)saved);}
struct Payload {uint16_t head;uint8_t bytes[8];};struct Payload packet;
uint16_t received,bank;
__noinline void accept(const uint8_t * __far p,uint16_t x,uint16_t y){
 received=(p?*p:0)+x+y;
#ifdef __ZICC__
 bank=(uint16_t)((uint32_t)p>>16);
#endif
}
__noinline void local_address(uint16_t v){struct Payload local;local.bytes[0]=(uint8_t)v;accept(local.bytes,7,9);}
__noinline uint16_t post_scan(const uint8_t * __far p,const uint8_t * __far end,uint16_t limit){
 uint16_t q=limit+opaque,i,a,b;if(q==0)return 55;
 for(i=0;p<end&&i<limit;){a=*p++;b=i<4?i:0;if(a!=b)return a+100;i++;}
 return i;
}
EXPECTED_VALUES
int main(void){uint16_t n,k,v;
 guard_word=opaque;if(single_written_value()||guard_word!=1)return 19;
 for(n=0;n<256;n++){
  opaque=n;v=opaque;
  for(k=0;k<8;k++)flags[k]=(v>>k)&1;
  for(k=0;k<16;k++)data[k]=(uint16_t)((uint32_t)v*25173U+(uint32_t)k*13849U);
  shared();for(k=0;k<16;k++)if(data[k]!=expected[n][k])return 1;
  if(mutation(v)!=(v?37:18))return 2;
  calls=0;if(call_choices()!=(199^17)||calls!=2)return 3;
  io=v;if(volatile_choices()!=(v?(91^17):(199^37)))return 4;
  if(lifetimes(v)!=extra[n][0]||escaped(v)!=extra[n][1]||loop_lifetimes(v)!=extra[n][2])return 5;
  if(other_written_values(v)!=((v&1)?45:41)+((v&2)!=0))return 20;
  {uint16_t next=(uint8_t)(v+1),swapped=(next<<8)|v;
   if(xor_tail(v)!=swapped||xor_spelled(v)!=swapped||xor_escaped(v)!=swapped)return 21;
   if(xor_nonterminal(v)!=((v&1)?swapped:((v<<8)|next)))return 22;
  }
  calls=0;wide_call(v,(uint16_t)~v,65530,v);if(calls!=1)return 6;
  if(wide_call(v,(uint16_t)~v,65530,v)!=(((uint32_t)65535<<16)|(uint16_t)(v+65530U))||calls!=2)return 7;
  {uint32_t w=((uint32_t)(v+65280U)<<16)|(uint16_t)(v*257U);
   if(projections(w)!=((uint16_t)(v*257U)^(uint16_t)(v+65280U)^(uint8_t)v))return 8;
   wide_io=w;if(volatile_projection()!=(uint16_t)(v*257U))return 9;
   wide_source=w;narrow_copy();if(narrowed!=(uint16_t)w)return 17;
   if(snapshot_before_write()!=(uint16_t)w||wide_source!=17)return 18;
  }
  packet.bytes[0]=(uint8_t)v;accept(packet.bytes,7,9);if(received!=v+16)return 10;
#ifdef __ZICC__
  if(bank!=126)return 11;
#endif
  {const uint8_t *p=v?packet.bytes:0;accept(p,7,9);if(received!=(v?v+16:16))return 12;
#ifdef __ZICC__
   if(bank!=(v?126:0))return 13;
#endif
  }
  local_address(v);if(received!=v+16)return 14;
  for(k=0;k<8;k++)packet.bytes[k]=(uint8_t)k;
  opaque=1;
  if(post_scan(packet.bytes,packet.bytes+8,v%9)!=(v%9<=4?v%9:104))return 15;
  if(post_scan(packet.bytes,packet.bytes+8,65535)!=55)return 16;
 }
 return 0;
}
'''
expected_rows=[]
for n in range(256):
 expected_rows.append([min((n*25173+k*13849)&65535,(91 if n&(1<<k) else 199) if k<8 else (17 if n&(1<<(k-8)) else 37)) for k in range(16)])
SOURCE=SOURCE.replace('EXPECTED_VALUES','static const uint16_t expected[256][16]={\n'+',\n'.join('{'+','.join(map(str,row))+'}' for row in expected_rows)+'\n};')
def combine(a,b,c):return (a^((b+c)&65535))&65535
extra=[]
for n in range(256):
 result=(combine(n+3,n^52,n+7)+combine(n+11,n^25,n+13))&65535
 first=result^(n^23130)
 pinned=(2*n+17)&65535;result=combine(n+17,pinned,n)
 pinned=(pinned+n+29)&65535;result=(result+combine(n+29,pinned,n))&65535
 total=n
 for k in range(6):
  b=combine(n+k,k,total)
  if k==2:continue
  total=(total+combine(b,n+k,k))&65535
  if k==4 and n&1:break
 extra.append([first,result^pinned,total])
SOURCE=SOURCE.replace('int main(void){','static const uint16_t extra[256][3]={\n'+',\n'.join('{'+','.join(map(str,row))+'}' for row in extra)+'\n};\nint main(void){')
def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'cleanup-host.c';host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/Od','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[]
 for mode,flags in [('selected',[]),('no-lines',['--no-line-passes']),('no-body',['--no-body-optimizations']),('no-private',['--no-private-regions']),('no-strength',['--no-strength-reduction'])]:
  _,rom,labels=c.compile_case('cleanup_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);c.emulate(rom,labels,0)
  asm=rom.with_suffix('.s').read_text()
  if mode=='selected':assert '; fused private selections' in asm
  if mode=='selected':assert '; packed private frame:' in asm
  single_value=asm.split('_single_written_value:',1)[1].split('__size_single_written_value',1)[0]
  if mode in ('selected','no-lines'):assert '$0013' not in single_value,single_value
  if mode=='no-body':assert '$0013' in single_value,single_value
  if mode in ('selected','no-lines'):
   for function in ('xor_tail','xor_spelled'):
    swap=asm.split('_'+function+':',1)[1].split('__size_'+function,1)[0]
    assert '    eor ' not in swap,swap
  if mode=='selected':
   assert '; fixed near object argument' in asm and '; discarded-result argument cleanup' in asm
   assert '; demanded word projection' in asm
   volatile=asm.split('_volatile_projection:',1)[1].split('__size_volatile_projection',1)[0]
   assert '; demanded word projection' not in volatile
   narrow=asm.split('_narrow_copy:',1)[1].split('__size_narrow_copy',1)[0]
   assert 'demanded word projection' in narrow and '_wide_source+2' not in narrow,narrow
  if mode=='no-private':assert '; packed private frame:' not in asm
  rows.append(dict(mode=mode,rom_bytes=rom.stat().st_size))
 (c.OUT/'private-cleanups.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS private cleanups: 256 opaque vectors, Python/host/target agreement, shared predicates, frame lifetimes/loops/escapes, live/discarded wide results, projections and NULL/member/local far arguments')
if __name__=='__main__':main()
