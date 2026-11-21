"""Source-derived cell ranges, relational spans and conservative barriers."""
from pathlib import Path
import importlib.util,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('range_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def clamp(v,limit):return max(0,min(limit,v))
def rectangle(values,limit,sizes):
 x=[clamp(v,limit) for v in values[:5]];y=[clamp(v,limit) for v in values[5:]]
 for i in range(5):
  for j in range(i+1,5):
   px=min(x[i]+sizes[i],x[j]+sizes[j])-max(x[i],x[j])
   if px<=0:continue
   py=min(y[i]+sizes[i],y[j]+sizes[j])-max(y[i],y[j])
   if py<=0:continue
   target,pen=(x,px) if px<py else (y,py);half=(pen+1)//2
   if target[i]<target[j]:target[i]-=half;target[j]+=half
   else:target[i]+=half;target[j]-=half
 return x+y

VALUES=[-32768,-32767,-30000,-129,-1,0,1,127,128,255,1024,30000,32766,32767]
INPUTS=[[VALUES[(n+3*k)%len(VALUES)] for k in range(5)]+[VALUES[(5*n+k+7)%len(VALUES)] for k in range(5)] for n in range(64)]
EXPECTED=[rectangle(v,(n*37)&255,[(n*17+k*31)&255 for k in range(5)]) for n,v in enumerate(INPUTS)]
def table(name,rows):return 'static const int16_t '+name+'[64][10]={'+','.join('{'+','.join(map(str,r))+'}' for r in rows)+'};\n'
SOURCE=r'''
#include <stdint.h>
volatile uint16_t input;
int16_t x[5],y[5];uint8_t sizes[5];uint16_t visits;
struct Cell{int16_t value;};struct Cell cell;
static const int16_t constants[3]={7,-9,17};
__noinline void rectangles(uint8_t limit){uint8_t i,j;int16_t a,b,px,py,half;
 for(i=0;i<5;i++){
  if(x[i]<0)x[i]=0;else if(x[i]>limit)x[i]=limit;
  if(y[i]<0)y[i]=0;else if(y[i]>limit)y[i]=limit;
 }
 for(i=0;i<5;i++)for(j=i+1;j<5;j++){
  visits++;
  a=x[i]+sizes[i];b=x[j]+sizes[j];px=(a<b?a:b)-(x[i]>x[j]?x[i]:x[j]);if(px<=0)continue;
  a=y[i]+sizes[i];b=y[j]+sizes[j];py=(a<b?a:b)-(y[i]>y[j]?y[i]:y[j]);if(py<=0)continue;
  if(px<py){half=(px+1)>>1;if(x[i]<x[j]){x[i]-=half;x[j]+=half;}else{x[i]+=half;x[j]-=half;}}
  else{half=(py+1)>>1;if(y[i]<y[j]){y[i]-=half;y[j]+=half;}else{y[i]+=half;y[j]-=half;}}
 }
}
__noinline int16_t partial(uint8_t n,uint8_t stop,uint8_t skip){uint8_t i;for(i=0;i<n;i++){
 if(i==stop)break;if(i==skip)continue;if(x[i]<0)x[i]=0;else if(x[i]>100)x[i]=100;
 }return x[0]<x[4]?x[0]:x[4];}
__noinline int16_t alias_case(int16_t *p){uint8_t i;for(i=0;i<5;i++){if(x[i]<0)x[i]=0;else if(x[i]>100)x[i]=100;}
 *p=-32768;return x[0]<x[4]?x[0]:x[4];}
__noinline int16_t byte_case(void){uint8_t i;for(i=0;i<5;i++){if(x[i]<0)x[i]=0;else if(x[i]>100)x[i]=100;}
 ((uint8_t *)x)[1]=255;return x[0]<x[4]?x[0]:x[4];}
__noinline struct Cell *getter(void){x[0]=-32768;return &cell;}
__noinline int16_t member_case(void){uint8_t i;for(i=0;i<5;i++){if(x[i]<0)x[i]=0;else if(x[i]>100)x[i]=100;}
 (x[0]=3)?getter()->value:0;return x[0]<x[4]?x[0]:x[4];}
__noinline int16_t short_case(uint8_t flag){uint8_t i;for(i=0;i<5;i++){if(x[i]<0)x[i]=0;else if(x[i]>100)x[i]=100;}
 flag&&(x[0]=-32768);return x[0]<x[4]?x[0]:x[4];}
__noinline int16_t post_case(uint8_t start){uint8_t i=start&1;int16_t v=constants[i++];return (((int16_t)i-2)>>1)+v;}
__noinline int16_t condition_case(void){uint8_t i=0;if(i++)x[0]=1;return ((int16_t)i-2)>>1;}
__noinline uint16_t unsigned_choice(uint8_t flag,int8_t a){uint16_t v=flag?a:7U;return v<<8;}
__noinline int16_t long_loop(void){uint16_t i;x[0]=0;x[4]=32767;for(i=0;i<65;i++)x[0]=(int16_t)((uint16_t)x[0]+1000U);return x[0]<x[4]?x[0]:x[4];}
__noinline int16_t moving_limit(void){uint8_t i,end=5;for(i=0;i<end;i++){if(x[i]<0)x[i]=0;else if(x[i]>100)x[i]=100;end--;}return x[0]<x[4]?x[0]:x[4];}
'''+table('inputs',INPUTS)+table('expected',EXPECTED)+r'''
int main(void){uint16_t n,k,index;int16_t want[5],result;
 for(n=0;n<64;n++){
  input=n;index=input;if(index>=64)return 1;
  for(k=0;k<5;k++){x[k]=inputs[index][k];y[k]=inputs[index][k+5];sizes[k]=(uint8_t)((index*17+k*31)&255);}
  visits=0;rectangles((uint8_t)(index*37));if(visits!=10)return 2;
  for(k=0;k<5;k++)if(x[k]!=expected[index][k]||y[k]!=expected[index][k+5])return 3;
  for(k=0;k<5;k++)want[k]=x[k]=inputs[index][k];
  for(k=0;k<index%6;k++){if(k==(index+1)%6)break;if(k==(index+2)%6)continue;if(want[k]<0)want[k]=0;else if(want[k]>100)want[k]=100;}
  result=partial((uint8_t)(index%6),(uint8_t)((index+1)%6),(uint8_t)((index+2)%6));if(result!=(want[0]<want[4]?want[0]:want[4]))return 4;
  for(k=0;k<5;k++)x[k]=inputs[index][k];if(alias_case(&x[(index&1)?4:0])!=-32768)return 5;
  for(k=0;k<5;k++)x[k]=inputs[index][k];result=byte_case();
  if(result!=(int16_t)((inputs[index][0]<0?0:inputs[index][0]>100?100:inputs[index][0])-256))return 6;
  for(k=0;k<5;k++)x[k]=inputs[index][k];if(member_case()!=-32768)return 7;
  for(k=0;k<5;k++)x[k]=inputs[index][k];result=short_case((uint8_t)(index&1));
  want[0]=inputs[index][0]<0?0:inputs[index][0]>100?100:inputs[index][0];want[4]=inputs[index][4]<0?0:inputs[index][4]>100?100:inputs[index][4];
  if(index&1)want[0]=-32768;if(result!=(want[0]<want[4]?want[0]:want[4]))return 8;
  if(post_case((uint8_t)index)!=((index&1)?-9:6)||condition_case()!=-1)return 9;
  if(unsigned_choice(1,(int8_t)(index*17))!=(uint16_t)((uint16_t)(uint8_t)(index*17)<<8)||unsigned_choice(0,-1)!=1792)return 10;
  if(long_loop()!=-536)return 11;
  for(k=0;k<5;k++)want[k]=x[k]=inputs[index][k];for(k=0;k<3;k++)want[k]=want[k]<0?0:want[k]>100?100:want[k];
  if(moving_limit()!=(want[0]<want[4]?want[0]:want[4]))return 12;
 }return 0;}
'''

def body(s,name):return s.split('_'+name+':',1)[1].split('__size_'+name,1)[0]
def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'range-reference.c';host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/Od','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[];assemblies={}
 for mode,flags in [('selected',[]),('no-ranges',['--no-known-values']),('no-lines',['--no-line-passes']),('no-reuse',['--no-value-reuse'])]:
  _,rom,labels=c.compile_case('range_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);c.emulate(rom,labels,0);assemblies[mode]=rom.with_suffix('.s').read_text();rows.append(dict(mode=mode,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest()))
 assert '    bvc ' not in body(assemblies['selected'],'rectangles')
 assert '    ror a' not in body(assemblies['selected'],'rectangles')
 assert '    bvc ' in body(assemblies['no-ranges'],'rectangles')
 for name in ['partial','alias_case','byte_case','member_case','short_case','long_loop','moving_limit']:
  assert '    bvc ' in body(assemblies['selected'],name),name+' must retain its signed-overflow guard'
 (c.OUT/'range-values.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS range values: 64 opaque rectangle workloads, source/Python/host agreement, complete pair counts, partial clamps, break/continue, aliases, bytes, calls, short circuit and side-effecting indices')
if __name__=='__main__':main()
