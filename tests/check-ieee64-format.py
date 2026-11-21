"""Compare the handwritten binary64 formatter with host IEEE formatting."""
import os
import importlib.util
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT / 'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-format-check'
c.OUT.mkdir(parents=True, exist_ok=True)

CASES = [
    (0, 'f', 2), (1 << 63, 'e', 2),
    (0x4004000000000000, 'f', 0), (0x400c000000000000, 'f', 0),
    (0x3ff4000000000000, 'f', 1), (0x3ffc000000000000, 'f', 1),
    (0x3fb999999999999a, 'f', 17), (0x3fd5555555555555, 'e', 16),
    (1, 'e', 6), (0x0010000000000000, 'g', 17),
    (0x7fefffffffffffff, 'E', 4), (0x7fefffffffffffff, 'f', 0),
    (0x3ff0000000000000, 'g', 0), (0x3e45798ee2308c3a, 'g', 6),
    (0x4415af1d78b58c40, 'G', 6), (0x7ff0000000000000, 'f', 2),
    (0xfff0000000000000, 'E', 2), (0x7ff8000000000000, 'G', 2),
    (0x3ff0000000000000, 'x', 2), (0x3ff0000000000000, 'f', 33),
]

def main():
    _, plain, _ = c.compile_case('plain', 'int main(void){return 0;}')
    _, archive, labels = c.compile_case('archive', 'int main(void){return 0;}', extra_objects=[ROOT / 'build/libc.a'])
    assert plain.read_bytes() == archive.read_bytes()
    assert '_ieee64_format' not in labels and 'ieee64_dec_digits' not in labels
    source = c.OUT / 'main.c'
    source.write_text('int format_probe(void);int main(void){return format_probe();}\n')
    expected = []
    for bits, kind, precision in CASES:
        value = struct.unpack('<d', struct.pack('<Q', bits))[0]
        expected.append(None if kind == 'x' or precision > 32 else format(value, f'.{precision}{kind}'))
    for stage in (1, 3, 4):
        call = 'jsr .loword(__ieee64_format)' if stage == 1 else 'jsl __ieee64_format'
        ret = 'rtl' if stage == 4 else 'rts'
        lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                 '.import __ieee64_format', '.export _format_probe, _format_after, _format_output',
                 '.segment "BSS"', 'index: .res 2', '_format_output: .res 352', '.segment "CODE"',
                 '_format_probe:', 'phy', 'stz a:index', 'loop:', 'ldx a:index']
        for offset in range(0, 8, 2):
            lines += [f'lda f:table+{offset},x', f'sta z:__arith_lhs+{offset}']
        lines += ['lda f:table+8,x', 'sta z:__arith_lhs+24', 'lda f:table+10,x',
                  'sta z:__arith_lhs+26', 'lda #.loword(_format_output)', 'sta z:__arith_lhs+28',
                  'ldy #$5aa5', call, '_format_after:', 'lda a:index', 'clc', 'adc #12',
                  'sta a:index', f'cmp #{len(CASES)*12}', 'bne loop', 'lda #0', 'ply', ret,
                  '.segment "RODATA"', 'table:']
        for bits, kind, precision in CASES:
            lines.append('.word ' + ','.join(f'${(bits >> n) & 65535:04x}' for n in (0, 16, 32, 48)) + f',${ord(kind):04x},{precision}')
        driver = c.OUT / f'driver-{stage}.s'
        driver.write_text('\n'.join(lines) + '\n')
        raw = c.OUT / f'format-{stage}.raw'
        c.run([sys.executable, ROOT / 'tools/build-rom.py', source, '--assembly', driver, '--stage', str(stage), '-o', raw], timeout=120)
        sy = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        rom = raw.with_suffix('.sfc')
        c.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
        entries = ','.join('false' if x is None else '"' + x + '"' for x in expected)
        checks = f'''
local expected={{{entries}}}
local calls=0
emu.addMemoryCallback(function()
 calls=calls+1;local e=expected[calls];local s=emu.getState()
 require_value(s['cpu.y']==0x5aa5,'format Y '..calls)
 if e==false then require_value(s['cpu.a']==0xffff,'invalid format '..calls)
 else
  require_value(e~=nil and s['cpu.a']==#e,'format length '..calls)
  for i=1,#e do require_value(emu.read({sy['format_output'] & 0x1ffff}+i-1,emu.memType.snesWorkRam,false)==e:byte(i),'format byte '..calls..':'..i) end
  require_value(emu.read({sy['format_output'] & 0x1ffff}+#e,emu.memType.snesWorkRam,false)==0,'format terminator '..calls)
 end
end,emu.callbackType.exec,{sy['format_after']},{sy['format_after']})
emu.addMemoryCallback(function() require_value(calls=={len(CASES)},'format call count') end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
        c.emulate(rom, sy, 0, extra_checks=checks)
    plain_format = c.OUT / 'integer-format.c'
    plain_format.write_text(r'''
#include <stdio.h>
#include <string.h>
char output[32];
int main(void){return sprintf(output,"%d %u",-4,9)!=4 || strcmp(output,"-4 9");}
''')
    for stage in (1, 3, 4):
        raw = c.OUT / f'integer-printf-{stage}.raw'
        c.run([sys.executable, ROOT / 'tools/build-rom.py', plain_format, '--stage', str(stage), '-o', raw], timeout=120)
        sy = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        assert '_ieee64_format' not in sy and 'ieee64_dec_digits' not in sy and '_int64_format' not in sy
        rom = raw.with_suffix('.sfc')
        c.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
        c.emulate(rom, sy, 0)
    source.write_text(r'''
#include <stdio.h>
#include <string.h>
volatile float f=1.25F;
volatile double d=1.23456789012345;
char output[96];
int main(void) {
    int n=sprintf(output,"%d %.2f %d %.14g %.1e",7,f,9,d,1000.0);
    if(n!=32 || strcmp(output,"7 1.25 9 1.2345678901235 1.0e+03")) return 1;
    if(snprintf(output,5,"%.2f",12.5)!=5 || strcmp(output,"12.5")) return 2;
    if(sprintf(output,"%E %G",1.0,1.0)!=14 || strcmp(output,"1.000000E+00 1")) return 3;
    return 0;
}
''')
    for stage in (1, 3, 4):
        raw = c.OUT / f'printf-{stage}.raw'
        c.run([sys.executable, ROOT / 'tools/build-rom.py', source, '--stage', str(stage), '-o', raw], timeout=120)
        sy = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        rom = raw.with_suffix('.sfc')
        c.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
        c.emulate(rom, sy, 0)
    source.write_text(r'''
#include <stdio.h>
#include <string.h>
typedef int (*Formatter)(char *,const char * __far,...);
Formatter volatile format_pointer=sprintf;
volatile float value=2.5F;
char output[16];
int main(void){return format_pointer(output,"%.1f",value)!=3 || strcmp(output,"2.5");}
''')
    for stage in (1, 3, 4):
        raw = c.OUT / f'indirect-printf-{stage}.raw'
        c.run([sys.executable, ROOT / 'tools/build-rom.py', source, '--stage', str(stage), '-o', raw], timeout=120)
        sy = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        assert '_ieee64_format' in sy
        rom = raw.with_suffix('.sfc')
        c.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
        c.emulate(rom, sy, 0)
    print(f'PASS: {len(CASES)} binary64 format cases, LoROM and banked stages 3/4')

if __name__ == '__main__':
    main()
