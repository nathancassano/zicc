"""C loop scope, basic asm and ca65 input through the staged allocator."""
import os
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'port-abi-check'
spec = importlib.util.spec_from_file_location('support', ROOT/'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

SOURCE = r'''
unsigned plus_one(unsigned);
volatile unsigned seed=5;
void sleep_until_interrupt(void){__asm__ volatile("wai");}
int main(void){
    unsigned i=91,total=0;
    for(unsigned i=0;i<3;i++){total+=plus_one(i);}
    for(unsigned i=0;i<2;i++){total+=plus_one(seed);}
    __asm__ __volatile__("nop\nnop");
    __asm("nop");
    return total!=18||i!=91;
}
'''
ASSEMBLY = '''
.setcpu "65816"
.segment "CODE"
.export _plus_one
.a16
.i16
_plus_one:
    txa
    jsr .loword(add_one)
.if ZICC_LONG_CALLS
    rtl
.else
    rts
.endif
add_one:
    inc a
    rts
'''


def main():
    OUT.mkdir(parents=True,exist_ok=True);support.OUT=OUT
    source=OUT/'driver.c';source.write_text(SOURCE)
    assembly=OUT/'helper.s';assembly.write_text(ASSEMBLY)
    report={}
    for stage in (1,4):
        raw=OUT/f'stage{stage}.raw'
        support.run([sys.executable,ROOT/'tools/build-rom.py',source,'--assembly',assembly,'--stage',str(stage),'-o',raw],timeout=120)
        labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        rom=raw.with_suffix('.sfc');support.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        extra=f'''
local calls=0
emu.addMemoryCallback(function() calls=calls+1 end,emu.callbackType.exec,{labels['plus_one']},{labels['plus_one']})
emu.addMemoryCallback(function() require_value(calls==5,'ca65 call count') end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
        report[str(stage)]=support.emulate(rom,labels,0,extra_checks=extra)
        manifest=json.loads(raw.with_suffix('.allocation.json').read_text())
        output=Path(manifest['evidence'])/f'stage{stage}'/'0_driver.s'
        text=output.read_text()
        assert len(re.findall(r'^    nop$',text,re.M))>=3 and '    wai\n' in text and 'basic_asm' not in text
    rejected={
        'loop_scope':('int f(void){for(int i=0;i<1;i++){}return i;}','undeclared identifier'),
        'assembly_operand':('void f(void){__asm("nop" : : : "memory");}','after basic __asm string'),
        'assembly_clobber':('void f(void){__asm("lda #1");}','only wai and nop'),
        'assembly_nul':(r'void f(void){__asm("nop\0wai");}','embedded NULs'),
    }
    for name,(text,message) in rejected.items():
        path=OUT/(name+'.c');path.write_text(text)
        result=subprocess.run([str(ROOT/'build/zicc.exe'),str(path),'-o',str(path.with_suffix('.s'))],capture_output=True,text=True)
        assert result.returncode and message in result.stderr,(name,result.stderr)
    report['rejected']=list(rejected)
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: loop scope, basic asm, and measured short/long calls to ca65 code')


if __name__=='__main__':main()
