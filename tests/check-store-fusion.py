"""Adjacent RAM byte stores: exact bytes, stable inputs and boundary guards."""
from pathlib import Path
import importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fusion_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
SOURCE=r'''
#include <stdint.h>
uint8_t out[64];volatile uint8_t io[2];volatile uint16_t salt;uint16_t global_word,seen;
__noinline void pair_constant(uint16_t v){v^=salt;out[3]=(uint8_t)(v&255U);out[4]=(uint8_t)(v>>8);}
__noinline void pair_end(uint16_t v){v^=salt;out[62]=(uint8_t)v;out[63]=(uint8_t)(v>>8);}
__noinline void pair_index(uint16_t i,uint16_t v){i&=7;v^=salt;out[i+3]=(uint8_t)v;out[i+4]=(uint8_t)(v>>8);}
__noinline void pair_loop(uint16_t v){uint8_t k;v^=salt;for(k=0;k<8;k++){out[k*5+3]=(uint8_t)v;out[k*5+4]=(uint8_t)(v>>8);}}
__noinline void pair_pointer(uint8_t *p,uint16_t v){v^=salt;p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
__noinline void pair_global(uint16_t v){global_word=v^salt;out[0]=(uint8_t)global_word;out[1]=(uint8_t)(global_word>>8);}
__noinline void pair_observed(uint16_t v){v^=salt;out[0]=(uint8_t)v;seen=out[0];out[1]=(uint8_t)(v>>8);}
__noinline void pair_volatile(uint16_t v){v^=salt;io[0]=(uint8_t)v;io[1]=(uint8_t)(v>>8);}
__noinline void pair_mmio(uint16_t v){*(volatile uint8_t*)0x2100=(uint8_t)v;*(volatile uint8_t*)0x2101=(uint8_t)(v>>8);}
__noinline void pair_reverse(uint16_t v){v^=salt;out[1]=(uint8_t)(v>>8);out[0]=(uint8_t)v;}
__noinline void pair_gap(uint16_t v){v^=salt;out[0]=(uint8_t)v;out[2]=(uint8_t)(v>>8);}
__noinline void pair_different(uint16_t v,uint16_t w){v^=salt;out[0]=(uint8_t)v;out[1]=(uint8_t)(w>>8);}
__noinline void pair_narrow(uint16_t v){v^=salt;out[0]=(uint8_t)v;out[1]=(uint8_t)(((uint8_t)v)>>8);}
__noinline void pair_wrap(uint16_t i,uint16_t v){i&=63;v^=salt;out[i]=(uint8_t)v;out[(i+1)&63]=(uint8_t)(v>>8);}
__noinline void touch(uint16_t *v){seen=*v;}
__noinline void pair_escaped(uint16_t v){v^=salt;touch(&v);out[0]=(uint8_t)v;out[1]=(uint8_t)(v>>8);}
struct Fields { signed int part:4; };
volatile struct Fields device_field;
int first_field;
unsigned second_field;
__noinline void repeat_field(struct Fields v){first_field=v.part;second_field=v.part;}
__noinline void repeat_device_field(void){first_field=device_field.part;second_field=device_field.part;}
int main(void){unsigned i,j;uint16_t v;uint8_t lo,hi;salt=0;
 struct Fields fields={-3};
 repeat_field(fields);if(first_field!=-3||second_field!=(unsigned)-3)return 15;
 fields.part=6;repeat_field(fields);if(first_field!=6||second_field!=6)return 16;
 device_field.part=-4;repeat_device_field();if(first_field!=-4||second_field!=(unsigned)-4)return 17;
 for(i=0;i<256;i++){
  salt=(uint16_t)(i*25173U+13849U);v=salt;salt=0;lo=(uint8_t)v;hi=(uint8_t)(v>>8);
  for(j=0;j<64;j++)out[j]=90;
  pair_constant(v);if(out[3]!=lo||out[4]!=hi||out[2]!=90||out[5]!=90)return 1;
  pair_end(v);if(out[62]!=lo||out[63]!=hi||out[61]!=90)return 2;
  pair_index(i,v);if(out[(i&7)+3]!=lo||out[(i&7)+4]!=hi)return 3;
  pair_loop(v);for(j=0;j<8;j++)if(out[j*5+3]!=lo||out[j*5+4]!=hi)return 4;
  pair_pointer(out,v);if(out[0]!=lo||out[1]!=hi)return 5;
  pair_global(v);if(out[0]!=lo||out[1]!=hi)return 6;
  pair_observed(v);if(out[0]!=lo||out[1]!=hi||seen!=lo)return 7;
  pair_volatile(v);if(io[0]!=lo||io[1]!=hi)return 8;
  pair_reverse(v);if(out[0]!=lo||out[1]!=hi)return 9;
  pair_gap(v);if(out[0]!=lo||out[2]!=hi)return 10;
  pair_different(v,v^65535U);if(out[0]!=lo||out[1]!=(uint8_t)(hi^255))return 11;
  pair_narrow(v);if(out[0]!=lo||out[1]!=0)return 12;
  pair_wrap(63,v);if(out[63]!=lo||out[0]!=hi)return 13;
  pair_escaped(v);if(out[0]!=lo||out[1]!=hi||seen!=v)return 14;
 }return 0;}
'''
def body(s,n):return s.split('_'+n+':',1)[1].split('__size_'+n,1)[0]
def field_extensions(assembly):
 subtract='    eor #$0008\n    sec\n    sbc #$0008\n'
 branch=r'    cmp #\$0008\n    bcc (cg_\w+)\n    ora #\$FFF0\n\1 = \*'
 return assembly.count(subtract)+len(re.findall(branch,assembly))

def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'fusion-host.c';host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[]
 for mode,flags in [('selected',[]),('disabled',['--no-store-fusion']),('no-lines',['--no-line-passes']),('no-retention',['--no-loop-index-retention']),('no-shuffles',['--no-byte-shuffles'])]:
  _,rom,labels=c.compile_case('fusion_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);s=rom.with_suffix('.s').read_text();c.emulate(rom,labels,0)
  if mode=='selected':
   for name in ('pair_constant','pair_end','pair_index','pair_loop'):assert '; fused adjacent RAM byte stores' in body(s,name),name
   for name in ('pair_pointer','pair_global','pair_observed','pair_volatile','pair_mmio','pair_reverse','pair_gap','pair_different','pair_narrow','pair_wrap','pair_escaped'):assert '; fused adjacent RAM byte stores' not in body(s,name),name
  if mode=='disabled':assert '; fused adjacent RAM byte stores' not in s
  assert field_extensions(body(s,'repeat_field'))==(2 if mode=='disabled' else 1)
  device=body(s,'repeat_device_field')
  assert field_extensions(device)==2
  assert device.count('lda a:.loword(_device_field+$0000)')==2
  rows.append(dict(mode=mode,bytes=rom.stat().st_size))
 (c.OUT/'store-fusion.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS store fusion: fixed/indexed/retained/end-of-object stores, guards for aliasing, observations, narrowing, wrap, volatile and MMIO')
if __name__=='__main__':main()
