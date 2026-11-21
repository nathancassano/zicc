"""Bounded signed CMP/N selections, result flags and unbounded fallbacks."""
from pathlib import Path
import importlib.util,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('selection_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
BOUNDED={'min_lt':'a<b?a:b','min_le':'a<=b?a:b','min_gt':'a>b?b:a','min_ge':'a>=b?b:a',
         'max_lt':'a<b?b:a','max_le':'a<=b?b:a','max_gt':'a>b?a:b','max_ge':'a>=b?a:b'}
PREFIX='int16_t a=(int16_t)(x&1023)-512,b=(int16_t)(y&2047)-1024;'
EDGES=[0,1,32766,32767,32768,32769,65535]
VECTORS=list(dict.fromkeys([(x,y) for x in [0,511,512,513,1023] for y in [0,512,1023,1024,1025,1535,2047]]+
                          [(x,y) for x in EDGES for y in EDGES]+
                          [((n*25173+13849)&65535,(n*40503+17)&65535) for n in range(128)]))
def signed(n):return n if n<32768 else n-65536
EXPECTED=[]
for x,y in VECTORS:
 a=(x&1023)-512;b=(y&2047)-1024;lo=min(a,b);hi=max(a,b)
 EXPECTED.append([lo,hi,7 if lo else 11,13 if hi==0 else 17,19 if lo<0 else 23,29 if hi<0 else 31,lo&255,min(signed(x),signed(y)),max(signed(x),signed(y))])
SOURCE='#include <stdint.h>\nvolatile uint16_t opaque;\n'
for name,expr in BOUNDED.items():SOURCE+='__noinline int16_t '+name+'(uint16_t x,uint16_t y){'+PREFIX+'return '+expr+';}\n'
for name,expr in {'truth_min':'(a<b?a:b)?7:11','zero_max':'(a>b?a:b)==0?13:17','negative_min':'(a<b?a:b)<0?19:23','negative_max':'(a>b?a:b)<0?29:31'}.items():
 SOURCE+='__noinline int16_t '+name+'(uint16_t x,uint16_t y){'+PREFIX+'return '+expr+';}\n'
SOURCE+='__noinline uint8_t cast_min(uint16_t x,uint16_t y){'+PREFIX+'return (uint8_t)(a<b?a:b);}\n'
SOURCE+='__noinline int16_t min_full(int16_t a,int16_t b){return a<b?a:b;}\n__noinline int16_t max_full(int16_t a,int16_t b){return a>b?a:b;}\n'
SOURCE+=r'''
static uint16_t clamp_word(int16_t x) {
    return (uint16_t)x <= 31 ? (uint16_t)x : x < 0 ? 0 : 31;
}
__noinline uint16_t clamp_full(int16_t x) {
    return (uint16_t)x <= 31 ? (uint16_t)x : x < 0 ? 0 : 31;
}
__noinline uint16_t pack_fields(uint16_t x, uint16_t y) {
    int16_t delta = (int16_t)(y & 31);
    if (y & 32) delta = -delta;
    uint16_t first = clamp_word((int16_t)(x & 31) + delta);
    uint16_t second = clamp_word((int16_t)((x >> 5) & 31) - delta);
    return first | (second << 5);
}
uint16_t input_words[8], output_words[8];
__noinline void selected_mask(uint16_t i, uint16_t end, uint16_t delta, _Bool flip) {
    uint16_t mask = flip ? 0x1fff : 0;
    for (; i < end; ++i) {
        uint16_t input = input_words[i] ^ mask;
        uint16_t low = (input & 0x801f) + (delta & 0x1f);
        uint16_t high = (input & 0x0fc0) + (delta & 0x0fc0);
        if (low & 32) low = (low & 0xffc0) | 31;
        if (low & 0x8000) low = (low & 31) | 0x800;
        if (high >= 0x1000) high = 0x0fc0;
        output_words[i] = (low | high) ^ mask;
    }
}
'''
def table(name,rows,unsigned=False):return 'static const '+('uint16_t' if unsigned else 'int16_t')+' '+name+'['+str(len(rows))+']['+str(len(rows[0]))+']={\n'+',\n'.join('{'+','.join(map(str,r))+'}' for r in rows)+'};\n'
SOURCE+=table('inputs',VECTORS,True)+table('expected',EXPECTED)
SOURCE+='int main(void){uint16_t n,index,x,y;for(n=0;n<'+str(len(VECTORS))+';n++){opaque=n;index=opaque;if(index>='+str(len(VECTORS))+')return 1;x=inputs[index][0];y=inputs[index][1];\n'
for name in BOUNDED:SOURCE+='if('+name+'(x,y)!=expected[index]['+('0' if name.startswith('min') else '1')+'])return 2;\n'
for col,name in enumerate(['truth_min','zero_max','negative_min','negative_max','cast_min'],2):SOURCE+='if('+name+'(x,y)!=expected[index]['+str(col)+'])return '+str(col+1)+';\n'
SOURCE+='if(min_full((int16_t)x,(int16_t)y)!=expected[index][7]||max_full((int16_t)x,(int16_t)y)!=expected[index][8])return 9;\n}return 0;}\n'
def clamp(n):
    return max(0,min(n,31))
packed=[]
for x,y in VECTORS:
 delta=-(y&31) if y&32 else y&31
 packed.append([clamp(signed(x)),clamp((x&31)+delta)|(clamp(((x>>5)&31)-delta)<<5)])
SOURCE=SOURCE.replace('int main(void)',table('packed_expected',packed,True)+'int main(void)')
SOURCE=SOURCE.replace('return 9;\n}', '''return 9;
if(clamp_full((int16_t)x)!=packed_expected[index][0]||
   pack_fields(x,y)!=packed_expected[index][1])return 10;
{
    uint16_t i, start = y & 7, end = (x >> 6) & 7, delta = (y >> 3) & 0x0fff;
    _Bool flip = y & 8;
    for(i=0;i<8;++i){input_words[i]=x^(i*519u);output_words[i]=0xaaaa;}
    selected_mask(start,end,delta,flip);
    for(i=0;i<8;++i){
        uint16_t expected_word=0xaaaa;
        if(i>=start&&i<end){
            uint16_t mask=flip?0x1fff:0, word=(x^(i*519u))^mask;
            uint16_t lo=(word&0x801fu)+(delta&0x1fu), hi=(word&0x0fc0u)+(delta&0x0fc0u);
            if(lo&32u)lo=(lo&0xffc0u)|31u;
            if(lo&0x8000u)lo=(lo&31u)|0x800u;
            if(hi>=0x1000u)hi=0x0fc0;
            expected_word=(lo|hi)^mask;
        }
        if(output_words[i]!=expected_word)return 11;
    }
}
}''')
def body(s,name):return s.split('_'+name+':',1)[1].split('__size_'+name,1)[0]
def main():
 c.OUT.mkdir(parents=True,exist_ok=True);host=c.OUT/'signed-selection-reference.c'
 host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/Od','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[];assemblies={}
 for mode,flags in [('selected',[]),('no-known',['--no-known-values']),('no-lines',['--no-line-passes']),('no-body',['--no-body-optimizations'])]:
  _,rom,labels=c.compile_case('signed_selection_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);c.emulate(rom,labels,0);assemblies[mode]=rom.with_suffix('.s').read_text();rows.append(dict(mode=mode,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest()))
 for name in BOUNDED:
  selected=body(assemblies['selected'],name)
  assert '; bounded signed min/max: CMP/N' in selected,name
  assert '    bvc ' not in selected,name
 for name in ['truth_min','zero_max','negative_min','negative_max','cast_min']:assert '; bounded signed min/max: CMP/N' in body(assemblies['selected'],name),name
 for name in ['min_full','max_full']:
  assert '; bounded signed min/max: CMP/N' not in body(assemblies['selected'],name),name
  assert '    bvc ' in body(assemblies['selected'],name),name
 assert '; bounded signed min/max: CMP/N' not in assemblies['no-known']
 selected=body(assemblies['selected'],'pack_fields')
 assert selected.count('    bpl ')==2 and '    bit #$8000' not in selected,selected
 assert '    xba\n    lsr a\n    lsr a\n    lsr a\n    ora ' in selected,selected
 assert '    bit #$8000' in body(assemblies['selected'],'clamp_full')
 loop=body(assemblies['selected'],'selected_mask')
 assert loop.count('    eor #$1FFF')==2 and loop.count('    eor ')==2,loop
 assert '    cmp #$1000\n    bcc ' in loop and '; accumulator conditional join' in loop,loop
 assert loop.count('    bit #$8020')==2 and '    bit #$8000' not in loop,loop
 assert loop.count('    clc\n')==body(assemblies['no-known'],'selected_mask').count('    clc\n')-2,loop
 (c.OUT/'signed-minmax.json').write_text(json.dumps(dict(vectors=len(VECTORS),runs=rows),indent=2)+'\n')
 print('PASS bounded signed selections: '+str(len(VECTORS))+' opaque pairs, eight ordering/arm forms, equality, zero/sign flags, byte casts and full signed extremes; Python/host/target agreement')
if __name__=='__main__':main()
