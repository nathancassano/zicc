"""Exercise default-promoted K&R floating parameters in separate units."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'legacy-float-abi-check'
c.OUT.mkdir(parents=True,exist_ok=True)

KERNEL=r'''
volatile unsigned count;
float old_add(a,b,c) float a,c; int b;
{ count++; return a+c+(float)b; }
double old_double(a,b) double a; float b;
{ count++; return a+(double)b; }
'''
DRIVER=r'''
float old_add();double old_double();
typedef float (*OldFloat)();typedef double (*OldDouble)();
OldFloat volatile fp=old_add;OldDouble volatile dp=old_double;
volatile float a=1.25F,c=2.5F;
volatile double d=4.5;
extern volatile unsigned count;
int main(void){
 if(old_add(a,3,c)!=6.75F)return 1;
 if(fp(a,3,c)!=6.75F)return 2;
 if(old_double(d,a)!=5.75)return 3;
 if(dp(d,a)!=5.75)return 4;
 return count!=4;
}
'''

def main():
    driver=c.OUT/'driver.c';driver.write_text(DRIVER)
    kernel=c.OUT/'kernel.c';kernel.write_text(KERNEL)
    for stage in (1,2,3,4):
        raw=c.OUT/f'legacy-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',driver,kernel,'--stage',str(stage),'-o',raw],timeout=120)
        sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        assert '_fext32_64' in sy and '_ftrunc64_32' in sy
        rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        c.emulate(rom,sy,0)
    print('PASS: K&R float/double argument promotion and indirect calls, stages 1/2/3/4')

if __name__=='__main__':main()
