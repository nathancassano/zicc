"""Use the assembly routines to format 64-bit integers and check that the linker pulls in the routines on demand."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT / 'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'int64-format-check'
c.OUT.mkdir(parents=True, exist_ok=True)

SOURCE = r'''
#include <stdio.h>
#include <string.h>
#include <inttypes.h>
volatile long long lo=(-9223372036854775807LL-1LL), hi=9223372036854775807LL;
volatile unsigned long long all=18446744073709551615ULL, zero=0ULL, value=0x1234abcdef987654ULL;
volatile unsigned long long digit=7ULL, prefix=65538ULL;
char buffer[96];
typedef int (*Formatter)(char *,const char * __far,...);
Formatter volatile callback=sprintf;
int main(void){
 if(sprintf(buffer,"%" PRId64,lo)!=20||strcmp(buffer,"-9223372036854775808"))return 1;
 if(sprintf(buffer,"%" PRIiMAX,hi)!=19||strcmp(buffer,"9223372036854775807"))return 2;
 if(sprintf(buffer,"%" PRIu64,all)!=20||strcmp(buffer,"18446744073709551615"))return 3;
 if(sprintf(buffer,"%" PRIx64,value)!=16||strcmp(buffer,"1234abcdef987654"))return 4;
 if(sprintf(buffer,"%" PRIX64,value)!=16||strcmp(buffer,"1234ABCDEF987654"))return 5;
 if(sprintf(buffer,"[%024llu]",all)!=26||strcmp(buffer,"[000018446744073709551615]"))return 6;
 if(sprintf(buffer,"[%25lld]",lo)!=27||strcmp(buffer,"[     -9223372036854775808]"))return 7;
 if(sprintf(buffer,"[%-.0llu]",zero)!=2||strcmp(buffer,"[]"))return 8;
 if(sprintf(buffer,"%ju %d",all,7)!=22||strcmp(buffer,"18446744073709551615 7"))return 9;
 if(snprintf(buffer,5,"%llx",value)!=16||strcmp(buffer,"1234"))return 10;
 if(callback(buffer,"%llX",value)!=16||strcmp(buffer,"1234ABCDEF987654"))return 11;
 if(sprintf(buffer,"%llu %llu %llu",zero,digit,prefix)!=9||strcmp(buffer,"0 7 65538"))return 12;
 if(sprintf(buffer,"%04x %X",0xau,0xabcdu)!=9||strcmp(buffer,"000a ABCD"))return 13;
 if(sprintf(buffer,"%lx%08.lx",0xaabbccddUL,0x12345678UL)!=16||strcmp(buffer,"aabbccdd12345678"))return 14;
 if(sprintf(buffer,"[%.0x][%5.3lX]",0u,0xaUL)!=9||strcmp(buffer,"[][  00A]"))return 15;
 return 0;
}
'''

def main():
    source = c.OUT / 'format.c'
    source.write_text(SOURCE)
    for stage in (1, 2, 3, 4):
        raw = c.OUT / f'format-{stage}.raw'
        c.run([sys.executable, ROOT / 'tools/build-rom.py', source, '--stage', str(stage), '-o', raw], timeout=120)
        sy = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        assert '_int64_format' in sy and '_udiv64' in sy
        rom = raw.with_suffix('.sfc')
        c.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
        c.emulate(rom, sy, 0)
    print('PASS: signed/unsigned 64-bit decimal and hexadecimal formatting, stages 1–4')

if __name__ == '__main__':
    main()
