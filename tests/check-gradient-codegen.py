"""Check when gradient calculations can drop unused counters, use fixed offsets or reuse storage."""
from pathlib import Path
import importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gradient_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

SOURCE=r'''
#include <stdint.h>
volatile uint16_t opaque;
uint8_t table[400];uint16_t observed,completed;
static uint8_t tri(uint8_t x){x&=63;return x<32?x:63-x;}
__noinline void packed(uint8_t seed){uint8_t i,p;uint16_t color;
 for(i=0;i<17;i++){
  p=(uint8_t)(i+seed);
  color=((uint16_t)tri(p+11)<<10)|((uint16_t)tri(p+23)<<5)|(uint16_t)tri(p);
  table[i*5+3]=(uint8_t)color;table[i*5+4]=(uint8_t)(color>>8);
 }
}
__noinline void nonzero(uint8_t seed){uint8_t i,p;uint16_t color;
 for(i=3;i<13;i++){
  p=(uint8_t)(i+seed);
  color=((uint16_t)tri(p+11)<<10)|((uint16_t)tri(p+23)<<5)|(uint16_t)tri(p);
  table[i*7+2]=(uint8_t)color;table[i*7+3]=(uint8_t)(color>>8);
 }
}
__noinline void dynamic(uint8_t seed,uint8_t start){uint8_t i,p;uint16_t color;
 for(i=start;i<17;i++){
  p=(uint8_t)(i+seed);
  color=((uint16_t)tri(p+11)<<10)|((uint16_t)tri(p+23)<<5)|(uint16_t)tri(p);
  table[i*5+3]=(uint8_t)color;table[i*5+4]=(uint8_t)(color>>8);
 }
}
__noinline void live_counter(uint8_t seed){uint8_t i;
 for(i=0;i<9;i++){table[i*5+3]=seed;table[i*5+4]=seed+1;}completed=i;
}
__noinline uint16_t live_color(uint8_t seed){uint16_t a=(uint16_t)tri(seed+11)<<10;
 uint16_t b=a|((uint16_t)tri(seed+23)<<5)|tri(seed);observed=a;return b;
}
__noinline uint16_t repeated(uint8_t seed){uint16_t a=(uint16_t)tri(seed+11)<<10;
 return (a|((uint16_t)tri(seed+23)<<5)|tri(seed))^a;
}
__noinline uint16_t tick(uint8_t seed){observed=123;return seed^90;}
__noinline uint16_t call_barrier(uint8_t seed){uint16_t a=(uint16_t)tri(seed+11)<<10;
 return a|tick(seed);
}
EXPECTED_TABLES
int main(void){unsigned n,k;uint8_t seed;
 for(n=0;n<256;n++){
  opaque=n;seed=(uint8_t)opaque;
  for(k=0;k<400;k++)table[k]=99;
  packed(seed);
  for(k=0;k<17;k++){
   if(table[k*5+3]!=(uint8_t)expected[n][k]||table[k*5+4]!=(uint8_t)(expected[n][k]>>8))return 1;
   if(table[k*5]!=99||table[k*5+1]!=99||table[k*5+2]!=99)return 2;
  }
  for(k=0;k<400;k++)table[k]=99;
  nonzero(seed);
  for(k=3;k<13;k++){
   if(table[k*7+2]!=(uint8_t)expected[n][k]||table[k*7+3]!=(uint8_t)(expected[n][k]>>8))return 3;
   if(table[k*7]!=99||table[k*7+1]!=99||table[k*7+4]!=99)return 4;
  }
  if(table[2*7+2]!=99||table[13*7+2]!=99)return 5;
  for(k=0;k<400;k++)table[k]=99;
  dynamic(seed,(uint8_t)(n%20));
  for(k=0;k<17;k++){
   if(k<n%20){if(table[k*5+3]!=99||table[k*5+4]!=99)return 11;}
   else if(table[k*5+3]!=(uint8_t)expected[n][k]||table[k*5+4]!=(uint8_t)(expected[n][k]>>8))return 12;
  }
  live_counter(seed);if(completed!=9)return 6;
  for(k=0;k<9;k++)if(table[k*5+3]!=seed||table[k*5+4]!=(uint8_t)(seed+1))return 7;
  if(live_color(seed)!=expected[n][0]||observed!=red[n])return 8;
  if(repeated(seed)!=(uint16_t)(expected[n][0]^red[n]))return 9;
  if(call_barrier(seed)!=(red[n]|(seed^90))||observed!=123)return 10;
 }
 return 0;
}
'''
def tri(x):
 x&=63
 return x if x<32 else 63-x
colors=[[tri(n+i+11)<<10|tri(n+i+23)<<5|tri(n+i) for i in range(17)] for n in range(256)]
expected_tables='static const uint16_t expected[256][17]={\n'+',\n'.join('{'+','.join(map(str,row))+'}' for row in colors)+'\n};\n'
expected_tables+='static const uint16_t red[256]={'+','.join(str(tri(n+11)<<10) for n in range(256))+'};\n'
SOURCE=SOURCE.replace('EXPECTED_TABLES',expected_tables)
def body(s,n):return s.split('_'+n+':',1)[1].split('__size_'+n,1)[0]
def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'gradient-reference.c';host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/Od','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[]
 for mode,flags in [('selected',[]),('no-lines',['--no-line-passes']),('no-retention',['--no-loop-index-retention']),('no-private',['--no-private-regions']),('no-body',['--no-body-optimizations'])]:
  _,rom,labels=c.compile_case('gradient_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);c.emulate(rom,labels,0)
  assembly=rom.with_suffix('.s').read_text()
  if mode=='selected':
   for name,entry,limit in [('packed',0,85),('nonzero',21,91)]:
    b=body(assembly,name)
    assert 'counter eliminated' in b and f'ldx #${entry:04X}' in b and f'cpx #${limit:04X}' in b,name
    assert '    cpy ' not in b and not re.search(r'^    (?:pha|pla)$',b,re.M),name
    assert 'last-use home accumulation' in b,name
    homes=re.findall(r'^    (?:sta|ora) z:__arith_lhs\+(\d+)$',b,re.M)
    assert len(set(homes))==1,(name,homes)
   assert 'counter eliminated' not in body(assembly,'live_counter')
   assert 'counter eliminated' in body(assembly,'dynamic')
  rows.append(dict(mode=mode,rom_bytes=rom.stat().st_size))
 (c.OUT/'gradient-codegen.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS gradient codegen: 256 opaque phases, Python/host/target agreement, strides 5/7, literal starts 0/3, dynamic starts/zero trips, live counters/colors, repeated reads and call barriers')
if __name__=='__main__':main()
