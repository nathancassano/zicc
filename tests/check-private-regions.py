"""Check when private values can be reused or discarded around volatile accesses without overwriting live storage."""
from pathlib import Path
import importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('private_support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
SOURCE=r'''
#include <stdint.h>
volatile uint16_t pulse,input;uint16_t data[8],seen,calls;uint16_t *escaped;
__noinline void observe(void){calls++;if(escaped){seen=*escaped;*escaped+=7;}}
__noinline uint16_t regions(uint16_t seed){uint16_t k,sum=0,tmp=seed;pulse=seed;
 for(k=0;k<8;k++){tmp=(k&1)?seed+k:seed-k;data[k]=tmp;sum+=data[k];}
 for(k=0;k<4;k++){data[k]+=sum;if(k==2)continue;data[k]^=seed;}
 pulse=sum;return sum;}
__noinline uint16_t escaping(uint16_t seed){uint16_t a=seed+3;escaped=&a;pulse=seed;observe();escaped=0;return a;}
__noinline uint16_t local_volatile(uint16_t seed){volatile uint16_t a=seed;a=seed+1;a=seed+2;pulse=a;return a;}
__noinline uint16_t alias(uint16_t *p,uint16_t seed){uint16_t a=seed+1;pulse=seed;*p=seed+7;return a+*p;}
struct Packet{uint16_t words[7];};
__noinline uint16_t aggregate(struct Packet *dst,struct Packet *src,uint16_t seed){uint16_t a=seed+3;pulse=seed;*dst=*src;observe();return a+dst->words[4];}
__noinline uint16_t exits(uint16_t seed){uint8_t k;uint16_t sum=seed;pulse=seed;for(k=0;k<8;k++){if(k==2)continue;sum+=k;data[k]=sum;if(k==5)break;}return sum+k;}
int main(void){uint16_t n,seed,sum,k,expected[8];struct Packet src,dst;
 escaped=0;calls=0;
 for(n=0;n<128;n++){input=(uint16_t)(n*25173U+13849U);seed=input;sum=0;
  for(k=0;k<8;k++){expected[k]=(k&1)?seed+k:seed-k;sum+=expected[k];}
  for(k=0;k<4;k++){expected[k]+=sum;if(k==2)continue;expected[k]^=seed;}
  if(regions(seed)!=sum||pulse!=sum)return 1;
  for(k=0;k<8;k++)if(data[k]!=expected[k])return 2;
  if(escaping(seed)!=(uint16_t)(seed+10)||seen!=(uint16_t)(seed+3)||escaped)return 3;
  if(local_volatile(seed)!=(uint16_t)(seed+2)||pulse!=(uint16_t)(seed+2))return 4;
  if(alias(data,seed)!=(uint16_t)(seed*2+8)||data[0]!=(uint16_t)(seed+7))return 5;
  for(k=0;k<7;k++){src.words[k]=seed+k;dst.words[k]=0;}
  if(aggregate(&dst,&src,seed)!=(uint16_t)(seed*2+7))return 6;
  for(k=0;k<7;k++)if(dst.words[k]!=(uint16_t)(seed+k))return 7;
  if(exits(seed)!=(uint16_t)(seed+18))return 8;
 }if(calls!=256)return 9;return 0;}
'''
FAR_ARGUMENT_SOURCE=r'''
#include <stdint.h>
struct Point { int16_t x, y; };
struct Bounds { int16_t left, top, right, bottom; };
const struct Point points[] = {{-7, 10}, {7, 10}, {7, -5}, {2, 4}, {8, 4}, {2, 9}};
const struct Bounds box = {0, 0, 8, 9};
volatile unsigned choice;

__noinline int contains(const struct Point * __far p, const struct Bounds * __far b)
{
    return p->x >= b->left && p->x < b->right && p->y >= b->top && p->y < b->bottom;
}
int main(void)
{
    unsigned i;
    for (i = 0; i < 6; ++i) {
        choice = i;
        if (contains(&points[choice], &box) != (i == 3)) return 1;
    }
    return 0;
}
'''

DISPATCH_SOURCE=r'''
#include <stdint.h>
struct Slot { uint16_t value; uint8_t kind, pad; };
struct Slot slots[] = {{11,2,0}, {22,4,0}, {33,3,0}, {44,5,0}, {55,0,0}};
volatile unsigned input, result;
uint16_t pending;

__noinline void ground(struct Slot *p) { result = p->value + 100; }
__noinline void air(struct Slot *p) { result = p->value + 200; }
__noinline void boss(struct Slot *p) { result = p->value + 300; }
__noinline void dispatch(unsigned off)
{
    struct Slot *p = (struct Slot *)((uint8_t*)slots + off);
    switch (((struct Slot*)((uint8_t*)slots+off))->kind) {
    case 2: case 4: ground(p); break;
    case 3: air(p); break;
    case 5: boss(p); break;
    }
}
__noinline void saturate(uint16_t clocks)
{
    uint16_t sum = pending + clocks;
    pending = sum < clocks ? 65535U : sum;
}
int main(void)
{
    unsigned i;
    const unsigned expected[] = {111, 122, 233, 344, 0};
    for (i = 0; i < 5; ++i) {
        input = i;
        result = 0;
        dispatch(input * sizeof(struct Slot));
        if (result != expected[i]) return 1;
    }
    input = 32768;
    pending = 32767;
    saturate(input);
    if (pending != 65535) return 2;
    pending = 32768;
    saturate(input);
    if (pending != 65535) return 3;
    pending = 3;
    saturate(input);
    if (pending != 32771) return 4;
    return 0;
}
'''

WORD_FOLD_SOURCE=r'''
#include <stdint.h>
uint16_t ticks, requested;
volatile uint16_t pulse, seed;
__noinline unsigned update(void) { if (--ticks == 0) return 9; return 2; }
__noinline unsigned io_step(void) { if (--pulse == 0) return 7; return 3; }
__noinline uint16_t row(uint16_t x) { return (x >> 8) << 5; }
__noinline void request(uint16_t x) { requested = x; }
int main(void)
{
    unsigned i;
    for (i = 0; i < 256; ++i) {
        seed = i * 257U;
        if (row(seed) != i * 32U) return 1;
        request(seed);
        if (requested != seed) return 4;
    }
    ticks = 1;
    pulse = 1;
    if (update() != 9 || ticks != 0 || io_step() != 7 || pulse != 0) return 2;
    if (update() != 2 || ticks != 65535U || io_step() != 3 || pulse != 65535U) return 3;
    return 0;
}
'''

def main():
 c.OUT.mkdir(parents=True,exist_ok=True)
 binary=c.OUT/'private-regions-host.exe';objects=c.OUT/'private-regions-host-objects';objects.mkdir(exist_ok=True)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/D_CRT_SECURE_NO_WARNINGS','/Fo'+str(objects)+'\\','/Fe'+str(binary),ROOT/'tests/private-regions-host.c',ROOT/'src/preprocess.c',ROOT/'src/relax.c']);c.run([binary])
 host=c.OUT/'private-reference.c';host.write_text('#define __noinline __declspec(noinline)\n'+SOURCE)
 c.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/Od','/Fo'+str(host.with_suffix('.obj')),'/Fe'+str(host.with_suffix('.exe')),host]);c.run([host.with_suffix('.exe')])
 runtime=ROOT/'build/integers.o'
 rows=[]
 for mode,flags in [('selected',[]),('disabled',['--no-private-regions']),('no-lines',['--no-line-passes']),('no-retention',['--no-loop-index-retention']),('y-frame',['--no-stack-frames'])]:
  _,rom,labels=c.compile_case('private_'+mode,SOURCE,extra_objects=[runtime],flags=['-I',ROOT/'include',*flags]);c.emulate(rom,labels,0);rows.append(dict(mode=mode,bytes=rom.stat().st_size))
 for mode,flags,offset,loads in [
  ('selected',[],5,1),
  ('disabled',['--no-private-regions'],5,4),
  ('long-return',['--long-return'],6,1),
 ]:
  _,rom,labels=c.compile_case('far_arguments_'+mode,FAR_ARGUMENT_SOURCE,flags=['-I',ROOT/'include',*flags])
  body=rom.with_suffix('.s').read_text().split('_contains:\n',1)[1].split('__size_contains',1)[0]
  assert body.count(f'    lda {offset},s\n')==loads,mode
  c.emulate(rom,labels,0)
 for mode,flags in [('selected',[]),('stack',['--no-dp-homes']),
                    ('long',['--long-return']),('control',['--no-line-passes'])]:
  _,rom,labels=c.compile_case('private_dispatch_'+mode,DISPATCH_SOURCE,flags=['-I',ROOT/'include',*flags])
  asm=rom.with_suffix('.s').read_text()
  dispatch=asm.split('_dispatch:\n',1)[1].split('__size_dispatch',1)[0]
  saturate=asm.split('_saturate:\n',1)[1].split('__size_saturate',1)[0]
  assert ('    stx z:__arith_lhs' in dispatch)==(mode=='control'),mode
  assert '    phx\n' not in dispatch,mode
  assert ('    cmp ' in saturate)==(mode in ('control','stack')),mode
  c.emulate(rom,labels,0)
 for mode,flags in [('selected',[]),('control',['--no-line-passes'])]:
  _,rom,labels=c.compile_case('word_folds_'+mode,WORD_FOLD_SOURCE,flags=['-I',ROOT/'include',*flags])
  asm=rom.with_suffix('.s').read_text()
  update=asm.split('_update:\n',1)[1].split('__size_update',1)[0]
  io_step=asm.split('_io_step:\n',1)[1].split('__size_io_step',1)[0]
  row=asm.split('_row:\n',1)[1].split('__size_row',1)[0]
  request=asm.split('_request:\n',1)[1].split('__size_request',1)[0]
  assert ('dec a:.loword(_ticks)' in update)==(mode=='selected'),mode
  assert 'dec a:.loword(_pulse)' not in io_step,mode
  assert row.count('    xba\n')==(0 if mode=='selected' else 2),mode
  assert ('stx a:.loword(_requested)' in request)==(mode=='selected'),mode
  c.emulate(rom,labels,0)
 (c.OUT/'private-regions.json').write_text(json.dumps(rows,indent=2)+'\n')
 print('PASS private regions: host effect/CFG/byte proofs, 128 opaque inputs, aliases, calls, loop exits, and short/long-return far arguments')
if __name__=='__main__':main()
