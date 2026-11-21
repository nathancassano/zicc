"""Exercise the binary64 decimal-search seed against host conversions."""
import os
import importlib.util
from pathlib import Path
import random
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT / 'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-decimal-estimate-check'
c.OUT.mkdir(parents=True, exist_ok=True)
CASES = [(0, -343), (0, 308), (1, 0), (1, -1), (1, 308),
         (12345678901234567, -16), (18446744073709551615, 0),
         (49406564584124654, -340), (22250738585072014, -324),
         (17976931348623157, 292), (1, -323), (5, -324),
         (99999999999999999, -342), (99999999999999999, 292)]
rng = random.Random(0xd0b1e64)
CASES += [(rng.randrange(1, 10**17), rng.randrange(-330, 293)) for _ in range(12)]

def main():
    _, plain, _ = c.compile_case('plain', 'int main(void){return 0;}')
    _, archive, labels = c.compile_case('archive', 'int main(void){return 0;}', extra_objects=[ROOT/'build/libc.a'])
    assert plain.read_bytes() == archive.read_bytes()
    assert '_ieee64_decimal_estimate' not in labels
    source = c.OUT/'main.c'
    source.write_text('int estimate_probe(void);int main(void){return estimate_probe();}\n')
    expected = [int.from_bytes(struct.pack('<d', float(f'{m}e{exp}')), 'little') for m, exp in CASES]
    for stage in (1, 3, 4):
        call = 'jsr .loword(__ieee64_decimal_estimate)' if stage == 1 else 'jsl __ieee64_decimal_estimate'
        ret = 'rtl' if stage == 4 else 'rts'
        lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                 '.import __ieee64_decimal_estimate', '.export _estimate_probe, _estimate_after',
                 '.segment "CODE"', '_estimate_probe:', 'phy']
        for m, exp in CASES:
            for offset in (0, 2, 4, 6):
                lines += [f'lda #${(m >> (8*offset)) & 65535:04x}', f'sta z:__arith_lhs+{offset}']
            lines += [f'lda #${exp & 65535:04x}', 'ldx #$1234', 'ldy #$5aa5', call,
                      'jsr .loword(_estimate_after)']
        lines += ['lda #0', 'ply', ret, '_estimate_after:', 'rts']
        driver = c.OUT/f'driver-{stage}.s'
        driver.write_text('\n'.join(lines)+'\n')
        raw = c.OUT/f'estimate-{stage}.raw'
        c.run([sys.executable, ROOT/'tools/build-rom.py', source, '--assembly', driver, '--stage', str(stage), '-o', raw], timeout=120)
        sy = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        rom = raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
        checks = f'''
local expected={{{','.join(str(x) for x in expected)}}};local calls=0
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState();local e=expected[calls]
 local function word(i)return emu.read16(0x02+i,emu.memType.snesWorkRam,false)end
 local got=word(0)|(word(2)<<16)|(word(4)<<32)|(word(6)<<48)
 require_value(e~=nil and s['cpu.x']==0x1234 and s['cpu.y']==0x5aa5,'estimate X/Y '..calls)
 require_value(math.abs(got-e)<=16,'estimate bits '..calls..' got '..got..' expected '..e)
end,emu.callbackType.exec,{sy['estimate_after']},{sy['estimate_after']})
emu.addMemoryCallback(function()require_value(calls=={len(CASES)},'estimate call count')end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
        c.emulate(rom, sy, 0, extra_checks=checks)
    print(f'PASS: {len(CASES)} decimal estimate seeds, stages 1/3/4')

if __name__ == '__main__':
    main()
