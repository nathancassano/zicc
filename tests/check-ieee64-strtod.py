"""Exercise the public binary64 strtod ABI, including indirect calls."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-strtod-check'
c.OUT.mkdir(parents=True,exist_ok=True)

SOURCE=r'''
#include <stdlib.h>
#include <errno.h>
union Bits { double d; unsigned long long u; } value;
typedef double (*Parser)(const char * __far, char * __far *);
Parser volatile indirect=strtod;
typedef long double (*LongParser)(const char * __far, char * __far *);
LongParser volatile long_indirect=strtold;
char * __far end;
int main(void){
 errno=0;value.d=strtod("1.00000000000000011102230246251565404236316680908203125x",&end);
 if(value.u!=0x3ff0000000000000ULL||*end!='x'||errno)return 1;
 value.d=strtod("0x1.000000000000080000000001p0!",&end);
 if(value.u!=0x3ff0000000000001ULL||*end!='!')return 2;
 value.d=indirect("-0x1.8p2?",&end);
 if(value.u!=0xc018000000000000ULL||*end!='?')return 3;
 errno=0;value.d=strtod("4.9406564584124654e-324;",&end);
 if(value.u!=1ULL||*end!=';'||errno!=ERANGE)return 4;
 errno=0;value.d=strtod("1e99999!",&end);
 if(value.u!=0x7ff0000000000000ULL||*end!='!'||errno!=ERANGE)return 5;
 errno=0;value.d=strtod("-0x1p-1075!",&end);
 if(value.u!=0x8000000000000000ULL||*end!='!'||errno!=ERANGE)return 6;
 value.d=strtod("nan(foo)!",&end);
 if(value.u!=0x7ff8000000000000ULL||*end!='!')return 7;
 errno=0;value.d=long_indirect("0x1.0000000000001p0!",&end);
 if(value.u!=0x3ff0000000000001ULL||*end!='!'||errno)return 8;
 value.d=strtold("-0!",&end);
 if(value.u!=0x8000000000000000ULL||*end!='!'||errno)return 9;
 return 0;
}
'''

def main():
    source=c.OUT/'main.c';source.write_text(SOURCE)
    unused=c.OUT/'no-wide.c';unused.write_text('#include <errno.h>\nint main(void){return errno;}\n')
    for stage in (1,2,3,4):
        for name,path in (('used',source),('unused',unused)):
            raw=c.OUT/f'{name}-{stage}.raw'
            c.run([sys.executable,ROOT/'tools/build-rom.py',path,'--stage',str(stage),'-o',raw],timeout=120)
            sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
            if name=='used':
                assert 'strtod' in sy and '_ieee64_hexparse' in sy and '_ieee64_parse_decimal' in sy
                assert sy['strtold'] == sy['strtod']
            else:
                assert 'strtod' not in sy and '_ieee64_hexparse' not in sy and '_ieee64_parse_decimal' not in sy
                assert 'strtold' not in sy
            rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
            c.emulate(rom,sy,0)
    print('PASS: public binary64 strtod, direct/indirect calls and unused I/O, stages 1/2/3/4')

if __name__=='__main__':main()
