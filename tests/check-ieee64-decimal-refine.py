"""Check exact midpoint correction of binary64 decimal-search estimates."""
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
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-decimal-refine-check'
c.OUT.mkdir(parents=True, exist_ok=True)

def scaled(m, power):
    if power < 0:
        return str(m * 5 ** -power), -power
    return str(m << power), 0

def bits(digits, scale):
    return int.from_bytes(struct.pack('<d', float(digits + 'e' + str(-scale))), 'little')

mid_even = scaled((1 << 53) + 1, -53)
mid_odd = scaled((1 << 53) + 3, -53)
underflow = scaled(1, -1075)
overflow = scaled((1 << 54) - 1, 970)
CASES = []
for digits, scale, seed in [
    ('1', 0, 0x3ff0000000000003), ('1', 0, 0x3feffffffffffffd),
    (*mid_even, 0x3ff0000000000002), (*mid_odd, 0x3ff0000000000000),
    (str(int(mid_even[0])-1), mid_even[1], 0x3ff0000000000001),
    (str(int(mid_even[0])+1), mid_even[1], 0x3ff0000000000000),
    (*underflow, 1), (str(int(underflow[0])+1), underflow[1], 0),
    (*overflow, 0x7fefffffffffffff),
    (str(int(overflow[0])-1), overflow[1], 0x7ff0000000000000),
    ('10000000000000001', 16, None),
    ('49406564584124654', 340, None),
    ('17976931348623157', -292, None),
]:
    CASES.append((digits, len(digits)-scale, seed, bits(digits, scale)))
rng = random.Random(0x64dec1a1)
for _ in range(8):
    digits = str(rng.randrange(10**15, 10**17))
    scale = rng.randrange(-40, 41)
    expected = bits(digits, scale)
    CASES.append((digits, len(digits)-scale, expected+rng.randrange(-4, 5), expected))

def main():
    _, plain, _ = c.compile_case('plain', 'int main(void){return 0;}')
    _, archive, labels = c.compile_case('archive', 'int main(void){return 0;}', extra_objects=[ROOT/'build/libc.a'])
    assert plain.read_bytes() == archive.read_bytes()
    assert '_ieee64_decimal_refine' not in labels and 'ieee64_dec_digits' not in labels
    source = c.OUT/'main.c'
    source.write_text('int refine_probe(void);int main(void){return refine_probe();}\n')
    for stage in (1, 3, 4):
        call = 'jsr .loword(__ieee64_decimal_refine)' if stage == 1 else 'jsl __ieee64_decimal_refine'
        estimate = 'jsr .loword(__ieee64_decimal_estimate)' if stage == 1 else 'jsl __ieee64_decimal_estimate'
        ret = 'rtl' if stage == 4 else 'rts'
        lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                 '.import __ieee64_decimal_refine, __ieee64_decimal_estimate', '.export _refine_probe, _refine_after',
                 '.segment "CODE"', '_refine_probe:', 'phy']
        for i, (digits, exp, seed, expected) in enumerate(CASES):
            initial = int(digits) if seed is None else seed
            for off in (0, 2, 4, 6):
                lines += [f'lda #${(initial>>(8*off))&65535:04x}', f'sta z:__arith_lhs+{off}']
            if seed is None:
                lines += [f'lda #${(exp-len(digits))&65535:04x}', estimate]
            lines += [f'lda #.loword(text_{i})', 'sta z:__arith_lhs+8',
                      f'lda #.bankbyte(text_{i})', 'sta z:__arith_lhs+10',
                      f'lda #.loword(text_{i}_end)', 'sta z:__arith_lhs+12',
                      f'lda #.bankbyte(text_{i}_end)', 'sta z:__arith_lhs+14',
                      f'lda #${exp&65535:04x}', 'sta z:__arith_lhs+16',
                      f'lda #${(exp>>16)&65535:04x}', 'sta z:__arith_lhs+18',
                      'ldy #$5aa5', call, 'jsr .loword(_refine_after)']
        lines += ['lda #0', 'ply', ret, '_refine_after:', 'rts', '.segment "RODATA"']
        for i, (digits, _, _, _) in enumerate(CASES):
            lines += [f'text_{i}: .byte "{digits}"', f'text_{i}_end:']
        driver = c.OUT/f'driver-{stage}.s'
        driver.write_text('\n'.join(lines)+'\n')
        raw = c.OUT/f'refine-{stage}.raw'
        c.run([sys.executable, ROOT/'tools/build-rom.py', source, '--assembly', driver, '--stage', str(stage), '-o', raw], timeout=120)
        sy = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        rom = raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
        checks = f'''
local expected={{{','.join(str(row[3]) for row in CASES)}}};local calls=0
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState()
 local function word(i)return emu.read16(0x02+i,emu.memType.snesWorkRam,false)end
 local got=word(0)|(word(2)<<16)|(word(4)<<32)|(word(6)<<48)
 require_value(s['cpu.y']==0x5aa5 and expected[calls]==got,'refine '..calls..' got '..got..' expected '..tostring(expected[calls]))
end,emu.callbackType.exec,{sy['refine_after']},{sy['refine_after']})
emu.addMemoryCallback(function()require_value(calls=={len(CASES)},'refine call count')end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
        # The two halfway-underflow cases dominate this ROM's cycle budget
        c.emulate(rom, sy, 0, extra_checks=checks, timeout_seconds=30)
    print(f'PASS: {len(CASES)} exact decimal refinements, stages 1/3/4')

if __name__ == '__main__':
    main()
