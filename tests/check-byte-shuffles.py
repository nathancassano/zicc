"""Check word shifts, including which bits survive and which flags are set after the CPU swaps the bytes."""
from pathlib import Path
import importlib.util,json,re
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('shuffle_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
VALUES=[0,1,2,3,31,32,63,64,127,128,255,256,257,512,1023,32767,32768,32769,65280,65535]
seed=0x1234
for _ in range(28):seed=(seed*25173+13849)&65535;VALUES.append(seed)
SOURCE='#include <stdint.h>\nvolatile uint16_t input;\n'
for n in range(16):
 SOURCE+=f'__noinline uint16_t left_{n}(uint16_t x){{return x<<{n};}}\n'
 SOURCE+=f'__noinline uint16_t right_{n}(uint16_t x){{return x>>{n};}}\n'
 SOURCE+=f'__noinline int16_t signed_{n}(int16_t x){{return x>>{n};}}\n'
SOURCE+=r'''
__noinline uint16_t narrow_left(uint16_t x){uint16_t p=x&31U;return p<<10;}
__noinline uint16_t byte_left(uint16_t x){uint16_t p=x&255U;return p<<5;}
__noinline uint16_t low_zero(uint16_t x){uint16_t p=x&65280U;return p>>5;}
__noinline int16_t positive_right(uint16_t x){int16_t p=x&32767U;return p>>8;}
__noinline int left_zero(uint16_t x){return (uint16_t)(x<<8)==0;}
__noinline int left_negative(uint16_t x){int16_t p=(uint16_t)(x<<8);return p<0;}
__noinline int right_negative(uint16_t x){int16_t p=x>>8;return p<0;}
uint16_t words[4], peers[4];
__noinline int high_index(unsigned i,uint16_t value){if((words[i]>>8)==(value>>8))return 9;return 15;}
__noinline int high_pair(unsigned i){if((words[i]>>8)!=(peers[i]>>8))return 9;return 15;}
__noinline int high_distinct(unsigned i,unsigned j){if((words[i]>>8)==(peers[j]>>8))return 9;return 15;}
__noinline int high_promoted(unsigned i,uint8_t value){if((words[i]>>8)==value)return 9;return 15;}
__noinline int high_literal(unsigned i){if((words[i]>>8)==255U)return 9;return 15;}
__noinline int high_signed(unsigned i){if(((int16_t)words[i]>>8)==255)return 9;return 15;}
__noinline int high_volatile(void){if((input>>8)==255U)return 9;return 15;}
__noinline int high_bool(unsigned i,uint16_t value){if((words[i]>>8)==(_Bool)value)return 9;return 15;}
__noinline int high_effect(unsigned i){if((words[i]++>>8)==255U)return 9;return 15;}
__noinline int decrement_test(unsigned i){if(--words[i])return 9;return 15;}
__noinline uint16_t decrement_value(unsigned i){return --words[i];}
'''
def array(name,values):return 'const uint16_t '+name+'[]={\n'+',\n'.join(','.join(str(v&65535)+'U' for v in values[i:i+16]) for i in range(0,len(values),16))+'};\n'
SOURCE+=array('values',VALUES)
for name,operation in [('expected_left',lambda x,n:x<<n),('expected_right',lambda x,n:x>>n),('expected_signed',lambda x,n:(x if x<32768 else x-65536)>>n)]:
 SOURCE+=array(name,[operation(x,n) for x in VALUES for n in range(16)])
for name,operation in [('narrow',lambda x:(x&31)<<10),('byte',lambda x:(x&255)<<5),('low',lambda x:(x&65280)>>5),('positive',lambda x:(x&32767)>>8)]:
 SOURCE+=array('expected_'+name,[operation(x) for x in VALUES])
SOURCE+='int main(void){unsigned i;uint16_t x;for(i=0;i<'+str(len(VALUES))+';i++){input=values[i];x=input;\n'
for n in range(16):
 SOURCE+=f'if(left_{n}(x)!=expected_left[i*16+{n}])return 1;\n'
 SOURCE+=f'if(right_{n}(x)!=expected_right[i*16+{n}])return 2;\n'
 SOURCE+=f'if((uint16_t)signed_{n}((int16_t)x)!=expected_signed[i*16+{n}])return 3;\n'
SOURCE+='''if(narrow_left(x)!=expected_narrow[i]||byte_left(x)!=expected_byte[i]||low_zero(x)!=expected_low[i]||positive_right(x)!=expected_positive[i])return 4;
if(left_zero(x)!=((x&255U)==0)||left_negative(x)!=((x&128U)!=0)||right_negative(x)!=0)return 5;
words[1]=x; peers[1]=x^255U; peers[2]=x^256U;
if(high_index(1,x^255U)!=9||high_index(1,x^256U)!=15||
   high_pair(1)!=15||high_distinct(1,2)!=15||high_promoted(1,x>>8)!=9)return 6;
peers[1]=x^256U;peers[2]=x^255U;
if(high_pair(1)!=9||high_distinct(1,2)!=9||high_promoted(1,(x>>8)^128U)!=15)return 7;
if(high_literal(1)!=(x>=65280U?9:15)||high_volatile()!=(x>=65280U?9:15)||
   high_signed(1)!=(x>=65280U && (int16_t)x>=0?9:15)||high_bool(1,256U)!=((x>>8)==1?9:15))return 8;
if(high_effect(1)!=(x>=65280U?9:15)||words[1]!=(uint16_t)(x+1U))return 9;
if(decrement_test(1)!=(x?9:15)||words[1]!=x)return 10;
if(decrement_value(1)!=(uint16_t)(x-1U)||words[1]!=(uint16_t)(x-1U))return 11;
}return 0;}'''
def body(s,n):return s.split('_'+n+':',1)[1].split('__size_'+n,1)[0]
def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 host=c.OUT/'shuffle-host.c';host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 # Use /Od for the host check. This version of MSVC gives the wrong answer
 # for the signed-short left-shift test with /O2
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/Od','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[]
 for mode,flags in [('selected',[]),('disabled',['--no-byte-shuffles']),('no-lines',['--no-line-passes']),('no-known',['--no-known-values'])]:
  _,rom,labels=c.compile_case('shuffle_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);s=rom.with_suffix('.s').read_text();c.emulate(rom,labels,0)
  if mode=='selected':
   for name in ('left_8','right_8','left_15','right_15','narrow_left','byte_left','low_zero','positive_right'):assert '    xba\n' in body(s,name),name
   assert 'and #$FF00' in body(s,'left_8') and 'and #$00FF' in body(s,'right_8')
   assert 'and #$FF00' not in body(s,'narrow_left')
   for name in ('high_index','high_pair','high_promoted','high_literal'):
    assert 'lda a:.loword(_words+$0001),x' in body(s,name),name
   assert 'cmp a:.loword(_peers+$0001),x' in body(s,'high_pair')
   for name in ('high_distinct','high_signed','high_volatile','high_bool','high_effect'):
    assert 'lda a:.loword(_words+$0001),x' not in body(s,name),name
   assert 'lda a:.loword(_input)' in body(s,'high_volatile')
   assert 'dec a:.loword(_words+$0000),x\n    lda' not in body(s,'decrement_test')
   assert 'dec a:.loword(_words+$0000),x' in body(s,'decrement_test')
   for n in range(16):
    signed=body(s,'signed_'+str(n))
    assert ('    xba\n' in signed)==(n>=8),n
    if n>=3:
     sign=1<<(15-n)
     mask=f'    eor #${sign:04X}\n'
     subtract=mask+f'    sec\n    sbc #${sign:04X}\n'
     branch=rf'    cmp #\${sign:04X}\n    bcc (cg_\w+)\n    ora #\${0x10000-2*sign:04X}\n\1 = \*'
     assert subtract in signed or (sign<=2 and mask+'    dec a\n'*sign in signed) or re.search(branch,signed),n
  if mode=='disabled':assert '    xba\n' not in s
  rows.append(dict(mode=mode,vectors=len(VALUES),shift_results=len(VALUES)*48,bytes=rom.stat().st_size))
 (c.OUT/'byte-shuffles.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS byte shuffles: all 16 counts, arbitrary words, signed extension, known bits and full-word N/Z, selected/disabled/no-lines/no-known')
if __name__=='__main__':main()
