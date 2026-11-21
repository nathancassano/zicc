"""Check binary32 by default and the opt-in binary64 ABI."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'float-abi-mode-check'
c.OUT.mkdir(parents=True, exist_ok=True)

SOURCE = r'''
#include <float.h>
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
volatile float single = 1.25f;
volatile double operand = 2.25;
double (*volatile square_root)(double) = sqrt;
char text[24];
char * __far end;
double first(int count, ...) {
    va_list ap;
    double value;
    va_start(ap, count);
    value = va_arg(ap, double);
    va_end(ap);
    return value;
}
float literal_arithmetic(void) { return ((0.1f+0.2f)*20)/3; }
int main(void) {
#if __ZICC_BINARY64__
    if (sizeof(double)!=8 || sizeof(long double)!=8 ||
        sizeof(1.0)!=8 || sizeof(1.0L)!=8 || DBL_MANT_DIG!=53) return 1;
#else
    if (sizeof(double)!=4 || sizeof(long double)!=4 ||
        sizeof(1.0)!=4 || sizeof(1.0L)!=4 || DBL_MANT_DIG!=24) return 2;
#endif
    if (sizeof(float)!=4 || sizeof(1.0f)!=4) return 3;
    if (square_root(operand)!=1.5) return 4;
    if (first(1,single)!=1.25) return 5;
    if (strtod("0x1.4p0!", &end)!=1.25 || *end!='!') return 6;
    if (strtold("1.25", 0)!=1.25L) return 7;
    if (sprintf(text,"%.2f",single)!=4 ||
        text[0]!='1' || text[1]!='.' || text[2]!='2' || text[3]!='5' || text[4]) return 8;
    if (literal_arithmetic()!=2.0f) return 9;
    return 0;
}
'''


def main():
    source = c.OUT/'main.c'
    source.write_text(SOURCE)
    for binary64 in (False, True):
        for stage in (1, 2, 3, 4):
            raw = c.OUT/f'mode-{int(binary64)}-{stage}.raw'
            c.run([sys.executable, ROOT/'tools/build-rom.py', source, '--stage', str(stage),
                   '-o', raw], timeout=120, binary64=binary64)
            labels = {name.removeprefix('_'): int(address, 16) for address, name in re.findall(
                r'^al (\w+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
            assert ('_ieee64_format' in labels) == binary64
            assert ('decimal__dec_format_raw_spec' in labels) != binary64
            rom = raw.with_suffix('.sfc')
            c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
            c.emulate(rom, labels, 0)
    print('PASS: default binary32 and opt-in binary64, stages 1/2/3/4')


if __name__ == '__main__':
    main()
