"""Check loops that select and copy bytes, including when copies can use wider words or two loops can safely become one."""
import os
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'structured-byte-loop-check'
spec = importlib.util.spec_from_file_location('body_checks', ROOT / 'tests/check-body-codegen.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

KERNELS = r'''
#include <stdint.h>
uint8_t tags[256], image[1056], slots[256], backup[256], small[32], other[256], phase;
volatile uint8_t observed[16];
uint16_t used, bound;
static void collect(unsigned first,unsigned end) {
    for(unsigned i=first;i<end;i++) {
        if(tags[i]==phase) {
            unsigned at=used++;
            slots[at]=i;
            backup[at]=image[i*4+1];
            image[i*4+1]=241;
        }
    }
}
void filtered(unsigned first,unsigned end) {
    collect(first,end);
    for(unsigned j=first;j<end;j++) {
        if(tags[j]==phase) image[1024+j/8]&=~(1<<(j%8));
    }
}
void scatter(void) {
    for(unsigned i=0;i<used;i++) image[slots[i]*4+1]=backup[i];
}
unsigned fixed_odd(void) {
    unsigned i;
    for(i=2;i<15;i++) small[i]=image[500+i];
    return i;
}
void overlap(void) {
    for(unsigned i=0;i<15;i++) small[i+1]=small[i];
}
unsigned changing_bound(void) {
    unsigned i;bound=20;
    for(i=0;i<bound;i++) {other[i]=i;if(i==2)bound=3;}
    return i;
}
unsigned alias_bound(uint8_t *where) {
    unsigned i;bound=7;
    for(i=0;i<bound;i++) {other[i]=i;*where=3;}
    return i;
}
void volatile_loop(void) {
    for(unsigned i=0;i<16;i++) observed[i]=i;
}
void dependent_loops(void) {
    for(unsigned i=0;i<16;i++) other[i]=small[i];
    for(unsigned j=0;j<16;j++) small[j]=other[(j+1)&15];
}
void changing_predicate(void) {
    for(unsigned i=0;i<16;i++) {if(tags[i]==phase) phase^=1;}
    for(unsigned j=0;j<16;j++) {if(tags[j]==phase) other[j]=99;}
}
void independent_loops(unsigned first,unsigned end) {
    for(unsigned i=first;i<end;i++) small[i]=image[i];
    for(unsigned j=first;j<end;j++) other[j]=tags[j];
}
unsigned self_start(unsigned start,unsigned end) {
    unsigned i=start;
    for(i=i+1;i<end;i++) other[i]=i+11;
    for(i=i+1;i<end;i++) small[i]=i+37;
    return i;
}
unsigned post_result(unsigned start) {
    unsigned value=start,old=0;
    for(unsigned i=0;i<7;i++) {old=value++;if(value!=old+1)return 1;}
    return value!=start+7;
}
unsigned global_steps(unsigned first,unsigned end) {
    for(used=first;used<end;used++) other[used]=used^73;
    return used;
}
unsigned comma_steps(unsigned end) {
    phase=0;
    for(used=0;used<end;used++,phase^=1) other[used]=used;
    return used+phase;
}
unsigned mixed_steps(unsigned end) {
    unsigned i;
    uint8_t value=65;
    for(i=0;i<end;i++,value++,backup[i]=value) {
        if(value>=68)value=65;
        other[i]=value;
    }
    for(i=0;i<end;value--,i++) {
        if(value<=65)value=68;
        image[2*i]=value;
    }
    return i+value;
}
unsigned repeated_index_step(unsigned end) {
    unsigned i;
    for(i=0;i<end;i++,i++) {
        if(phase)small[i]=i;
    }
    return i;
}
unsigned while_copy(unsigned first,unsigned end) {
    unsigned i=first;
    while(end>i) {if(tags[i]==phase)other[i]=image[i*2+1];i++;}
    return i;
}
unsigned while_copy_plus(unsigned first,unsigned end) {
    unsigned i=first;
    while(end>i) {if(tags[i]==phase)other[i]=image[i*2+1];i+=1;}
    return i;
}
void sentinel(unsigned first,unsigned end) {
    for(unsigned i=first;i!=end;i+=1) {if(tags[i]==phase)other[i]=i^131;}
}
int signed_window(int first,int end) {
    int i;
    for(i=first;i<end;i++) {if(phase==2)other[i+12]=i;}
    return i;
}
void signed_predicates(unsigned n) {
    for(unsigned i=0;i<n;i++) {if((int8_t)tags[i]<1)other[i]=17;else other[i]=33;}
}
void cast_predicates(unsigned n) {
    for(unsigned i=0;i<n;i++) {if((unsigned)(int8_t)tags[i]<1U)other[i]=17;else other[i]=33;}
}
void compare_bytes(unsigned n) {
    for(unsigned i=0;i<n;i++) {
        if((int8_t)tags[i]<(int8_t)backup[i])other[i]|=1;
        if((int8_t)tags[i]<=(int8_t)backup[i])other[i]|=2;
        if((int8_t)tags[i]>(int8_t)backup[i])other[i]|=4;
        if((int8_t)tags[i]>=(int8_t)backup[i])other[i]|=8;
        if((int8_t)tags[i]==(int8_t)backup[i])other[i]|=16;
        if((int8_t)tags[i]!=(int8_t)backup[i])other[i]|=32;
    }
}
void mixed_predicate(unsigned n) {
    for(unsigned i=0;i<n;i++) {if((int8_t)tags[i]==backup[i])other[i]=17;else other[i]=33;}
}
void cmp_lt(unsigned n) {for(unsigned i=0;i<n;i++)if((int8_t)tags[i]<(int8_t)backup[i])other[i]|=1;}
void cmp_le(unsigned n) {for(unsigned i=0;i<n;i++)if((int8_t)tags[i]<=(int8_t)backup[i])other[i]|=2;}
void cmp_gt(unsigned n) {for(unsigned i=0;i<n;i++)if((int8_t)tags[i]>(int8_t)backup[i])other[i]|=4;}
void cmp_ge(unsigned n) {for(unsigned i=0;i<n;i++)if((int8_t)tags[i]>=(int8_t)backup[i])other[i]|=8;}
void cmp_eq(unsigned n) {for(unsigned i=0;i<n;i++)if((int8_t)tags[i]==(int8_t)backup[i])other[i]|=16;}
void cmp_ne(unsigned n) {for(unsigned i=0;i<n;i++)if((int8_t)tags[i]!=(int8_t)backup[i])other[i]|=32;}
void expr_bound_char(unsigned n, unsigned trim) {unsigned char i;if(n<10||n>200||trim>10)return;for(i=0;i<n-trim;i++)other[i]=tags[i]^0x55;}
'''
DRIVER = r'''
#include <stdint.h>
extern uint8_t tags[256],image[1056],slots[256],backup[256],small[32],other[256],phase;
extern volatile uint8_t observed[16];
extern uint16_t used,bound;
void filtered(unsigned,unsigned);void scatter(void);unsigned fixed_odd(void);void overlap(void);
unsigned changing_bound(void);unsigned alias_bound(uint8_t *);void volatile_loop(void);
void dependent_loops(void);void changing_predicate(void);void independent_loops(unsigned,unsigned);
unsigned post_result(unsigned);
unsigned global_steps(unsigned,unsigned);unsigned comma_steps(unsigned);
unsigned mixed_steps(unsigned);unsigned repeated_index_step(unsigned);
unsigned self_start(unsigned,unsigned);unsigned while_copy_plus(unsigned,unsigned);
unsigned while_copy(unsigned,unsigned);void sentinel(unsigned,unsigned);int signed_window(int,int);
void signed_predicates(unsigned);void cast_predicates(unsigned);
void compare_bytes(unsigned);void mixed_predicate(unsigned);
void cmp_lt(unsigned);void cmp_le(unsigned);void cmp_gt(unsigned);void cmp_ge(unsigned);void cmp_eq(unsigned);void cmp_ne(unsigned);
void expr_bound_char(unsigned,unsigned);
uint8_t expected_masks[256];
int main(void) {
    unsigned t,i,j,first,end,expected,next;uint8_t want;
    for(t=0;t<32;t++) {
        phase=t&1;used=0;first=(t*7)%257;end=(t*13)%257;
        if(t<2){first=0;end=256;}
        for(i=0;i<256;i++) tags[i]=t==1?phase:(i+t)%3;
        for(i=0;i<1056;i++) image[i]=(i*37+t*11)&255;
        filtered(first,end);expected=0;
        for(i=0;i<256;i++) {
            int hidden=i>=first&&i<end&&tags[i]==phase;
            if(hidden) {
                if(slots[expected]!=i||backup[expected]!=(uint8_t)((i*4+1)*37+t*11))return 1;
                expected++;
            }
            for(j=0;j<4;j++) {
                want=(i*4+j)*37+t*11;
                if(j==1&&hidden)want=241;
                if(image[i*4+j]!=want)return 2;
            }
        }
        if(used!=expected)return 3;
        for(i=0;i<32;i++) {
            want=(1024+i)*37+t*11;
            for(j=0;j<8;j++) {
                next=i*8+j;
                if(next>=first&&next<end&&tags[next]==phase)want&=~(1<<j);
            }
            if(image[1024+i]!=want)return 4;
        }
        scatter();
        for(i=0;i<1024;i++) if(image[i]!=(uint8_t)(i*37+t*11))return 5;
    }
    for(i=0;i<32;i++)small[i]=77;
    if(fixed_odd()!=15)return 6;
    for(i=0;i<32;i++)if(small[i]!=(i>=2&&i<15?image[500+i]:77))return 7;
    overlap();for(i=0;i<16;i++)if(small[i]!=77)return 8;
    for(i=0;i<256;i++)other[i]=77;
    if(changing_bound()!=3||bound!=3||other[2]!=2||other[3]!=77)return 9;
    for(i=0;i<256;i++)other[i]=77;
    if(alias_bound((uint8_t *)&bound)!=3||bound!=3||other[2]!=2||other[3]!=77)return 10;
    volatile_loop();for(i=0;i<16;i++)if(observed[i]!=i)return 11;
    for(i=0;i<16;i++){small[i]=i+17;other[i]=77;tags[i]=i&1;}
    dependent_loops();for(i=0;i<16;i++)if(small[i]!=(i+1)%16+17)return 12;
    phase=0;for(i=0;i<16;i++)other[i]=77;
    changing_predicate();for(i=0;i<16;i++)if(other[i]!=(i&1?77:99))return 13;
    independent_loops(1,16);
    for(i=1;i<16;i++)if(small[i]!=image[i]||other[i]!=tags[i])return 14;
    if(post_result(65300))return 15;
    for(i=0;i<32;i++)other[i]=77;
    if(global_steps(3,19)!=19||global_steps(20,12)!=20)return 36;
    for(i=0;i<32;i++)if(other[i]!=(i>=3&&i<19?(i^73):77))return 37;
    if(comma_steps(9)!=10||used!=9||phase!=1)return 38;
    for(i=0;i<9;i++)if(other[i]!=i)return 39;
    backup[0]=99;
    if(mixed_steps(8)!=73||backup[0]!=99)return 40;
    for(i=0;i<8;i++) {
        want=65+i%3;
        if(other[i]!=want||backup[i+1]!=want+1)return 41;
        want=i<2?67-i:68-(i-2)%3;
        if(image[2*i]!=want)return 42;
    }
    if(repeated_index_step(7)!=8||small[6]!=6)return 43;
    for(i=0;i<32;i++)small[i]=77;
    if(self_start(1,8)!=9)return 33;
    for(i=0;i<32;i++)if(small[i]!=77)return 34;
    phase=1;for(i=0;i<32;i++)other[i]=77;
    if(while_copy(1,17)!=17||while_copy(19,2)!=19)return 16;
    if(while_copy_plus(1,17)!=17||while_copy_plus(19,2)!=19)return 35;
    for(i=1;i<17;i++)if(other[i]!=(tags[i]==phase?image[i*2+1]:77))return 17;
    sentinel(2,19);for(i=2;i<19;i++)if(tags[i]==phase&&other[i]!=(i^131))return 18;
    phase=2;for(i=0;i<32;i++)other[i]=77;
    if(signed_window(-6,-1)!=-1||signed_window(-1,-2)!=-1)return 19;
    for(i=0;i<32;i++)if(other[i]!=(i>=6&&i<=10?(uint8_t)(i-12):77))return 20;
    for(i=0;i<256;i++)tags[i]=i;
    signed_predicates(256);for(i=0;i<256;i++)if(other[i]!=(i==0||i>=128?17:33))return 21;
    cast_predicates(256);for(i=0;i<256;i++)if(other[i]!=(i==0?17:33))return 22;
    for(t=0;t<256;t++) {
        for(i=0;i<256;i++){tags[i]=i;backup[i]=t;other[i]=0;}
        compare_bytes(256);
        for(i=0;i<256;i++) {
            int a=(int8_t)i,b=(int8_t)t;
            expected=(a<b?1:0)|(a<=b?2:0)|(a>b?4:0)|(a>=b?8:0)|(a==b?16:0)|(a!=b?32:0);
            if(other[i]!=expected)return 23;expected_masks[i]=expected;
        }
        for(i=0;i<256;i++)other[i]=0;
        cmp_lt(256);cmp_le(256);cmp_gt(256);cmp_ge(256);cmp_eq(256);cmp_ne(256);
        for(i=0;i<256;i++)if(other[i]!=expected_masks[i])return 25;
    }
    for(i=0;i<256;i++){tags[i]=i;backup[i]=i;}
    mixed_predicate(256);for(i=0;i<256;i++)if(other[i]!=(i<128?17:33))return 24;
    for(i=0;i<32;i++)other[i]=77;
    expr_bound_char(10,10);if(other[0]!=77)return 26;
    expr_bound_char(19,5);for(i=0;i<32;i++)if(other[i]!=(i<14?(tags[i]^0x55):77))return 27;
    return 0;
}
'''


def body(assembly, name):
    return assembly.split('_' + name + ':', 1)[1].split('__size_' + name, 1)[0]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks.OUT = OUT
    host = OUT / 'reference.c'
    host.write_text(KERNELS + '\n' + DRIVER, encoding='ascii')
    exe = host.with_suffix('.exe')
    checks.c.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/O2',
                  '/Fo' + str(host.with_suffix('.obj')), '/Fe' + str(exe), host])
    assert subprocess.run([str(exe)], timeout=5).returncode == 0
    reports = {}
    for mode in ('optimized', 'fallback'):
        directory, rom, sy, assembly = checks.build(mode, KERNELS, DRIVER)
        if mode == 'optimized':
            assert assembly.count('; fused independent counted loops') == 2, assembly
            filtered = body(assembly, 'filtered')
            assert '; structured byte loop:' in filtered and filtered.count('lda a:.loword(_tags') == 1
            assert '; bounded byte shift lookup' in filtered
            assert '; structured byte loop:' in body(assembly, 'scatter')
            for name in ('while_copy', 'while_copy_plus', 'sentinel', 'signed_window', 'signed_predicates', 'cast_predicates', 'compare_bytes',
                         'cmp_lt', 'cmp_le', 'cmp_gt', 'cmp_ge', 'cmp_eq', 'cmp_ne', 'expr_bound_char'):
                assert '; structured byte loop:' in body(assembly, name), name
            assert '; widened fixed byte copy: 13 bytes' in body(assembly, 'fixed_odd')
            for name in ('overlap', 'changing_bound', 'alias_bound', 'volatile_loop'):
                part = body(assembly, name)
                assert '; widened fixed byte copy:' not in part, name
                if name != 'overlap':
                    assert '; structured byte loop:' not in part, name
            assert '; structured byte loop:' not in body(assembly, 'mixed_predicate')
            mixed = body(assembly, 'mixed_steps')
            assert mixed.count('; structured byte loop:') == 2, mixed
            assert '; structured byte loop:' not in body(assembly, 'repeated_index_step')
        sha = checks.run(directory, rom, sy, expect_calls={
            'filtered': 32, 'scatter': 32, 'fixed_odd': 1, 'overlap': 1,
            'changing_bound': 1, 'alias_bound': 1, 'volatile_loop': 1,
            'dependent_loops': 1, 'changing_predicate': 1, 'independent_loops': 1, 'self_start': 1, 'post_result': 1,
            'while_copy_plus': 2,
            'global_steps': 2, 'comma_steps': 1, 'mixed_steps': 1, 'repeated_index_step': 1,
            'while_copy': 2, 'sentinel': 1, 'signed_window': 2, 'signed_predicates': 1, 'cast_predicates': 1,
            'compare_bytes': 256, 'mixed_predicate': 1, 'expr_bound_char': 2,
            **{name: 256 for name in ('cmp_lt', 'cmp_le', 'cmp_gt', 'cmp_ge', 'cmp_eq', 'cmp_ne')}})
        reports[mode] = dict(rom_sha256=sha, filter_cases=32, max_backups=256, signed_byte_pairs=65536)
        print('PASS structured byte loops', mode, flush=True)
    (OUT / 'results.json').write_text(json.dumps(reports, indent=2) + '\n')


if __name__ == '__main__':
    main()
