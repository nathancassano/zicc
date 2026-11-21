"""Check exact binary64 midpoint decimal expansion and comparison on target."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT / 'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-decimal-compare-check'
c.OUT.mkdir(parents=True, exist_ok=True)

# Half-minimum subnormal, halfway values near one, an overflow midpoint,
# a full 64-bit input, a cancelable significand, and zero
CASES = [(1, -1075), ((1 << 53) + 1, -53), ((1 << 54) - 1, 970),
         ((1 << 64) - 1, -10), (1000, -10), (0, 0)]

def expansion(m, power):
    if not m:
        return 0, '0'
    while power < 0 and not m & 1:
        m >>= 1
        power += 1
    return (-power, str(m * 5 ** -power)) if power < 0 else (0, str(m << power))

def main():
    _, plain, _ = c.compile_case('plain', 'int main(void){return 0;}')
    _, archive, labels = c.compile_case('archive', 'int main(void){return 0;}', extra_objects=[ROOT/'build/libc.a'])
    assert plain.read_bytes() == archive.read_bytes()
    assert '_ieee64_decimal_compare' not in labels and 'ieee64_dec_digits' not in labels
    source = c.OUT / 'main.c'
    source.write_text('int compare_probe(void);int main(void){return compare_probe();}\n')
    expanded = [expansion(*case) for case in CASES]
    comparisons = []
    for index, (scale, digits) in enumerate(expanded):
        if CASES[index][0] == 0:
            continue
        number = int(digits)
        for delta in (-1, 0, 1):
            if number + delta <= 0:
                continue
            text = str(number + delta)
            point = len(text) - scale
            if len(text) > 2:
                text = text[0] + '.' + text[1:]
            comparisons.append((index, text, point, delta))
    scale, digits = expanded[1]
    point = len(digits) - scale
    comparisons += [(1, digits + '000', point, 0),
                    (1, digits, point - 1, -1), (1, digits, point + 1, 1),
                    (1, digits, -100000, -1), (1, digits, 100000, 1)]
    comparisons.sort(key=lambda row: row[0])
    for stage in (1, 3, 4):
        scaled = 'jsr .loword(__ieee64_decimal_scaled)' if stage == 1 else 'jsl __ieee64_decimal_scaled'
        compare = 'jsr .loword(__ieee64_decimal_compare)' if stage == 1 else 'jsl __ieee64_decimal_compare'
        ret = 'rtl' if stage == 4 else 'rts'
        lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                 '.import __ieee64_decimal_scaled, __ieee64_decimal_compare',
                 '.export _compare_probe, _scaled_after, _compare_after', '.segment "CODE"',
                 '_compare_probe:', 'phy']
        for index, (m, power) in enumerate(CASES):
            for offset in (0, 2, 4, 6):
                lines += [f'lda #${(m >> (offset*8)) & 65535:04x}', f'sta z:__arith_lhs+{offset}']
            lines += ['ldy #$5aa5', f'lda #${power & 65535:04x}', scaled,
                      'jsr .loword(_scaled_after)']
            for j, (case, text, point, delta) in enumerate(comparisons):
                if case != index:
                    continue
                lines += [f'pea ${(point >> 16) & 65535:04x}', f'pea ${point & 65535:04x}',
                          f'pea .bankbyte(text_{j}_end)', f'pea .loword(text_{j}_end)',
                          f'pea .bankbyte(text_{j})', f'pea .loword(text_{j})', compare,
                          'jsr .loword(_compare_after)', 'tsc', 'clc', 'adc #12', 'tcs']
        lines += ['lda #0', 'ply', ret, '_scaled_after:', 'rts', '_compare_after:', 'rts', '.segment "RODATA"']
        # The callback stubs are local JSRs even when runtime calls are long
        for j, (_, value, _, _) in enumerate(comparisons):
            lines += [f'text_{j}: .byte "{value}"', f'text_{j}_end:']
        driver = c.OUT / f'driver-{stage}.s'
        driver.write_text('\n'.join(lines) + '\n')
        raw = c.OUT / f'compare-{stage}.raw'
        c.run([sys.executable, ROOT/'tools/build-rom.py', source, '--assembly', driver, '--stage', str(stage), '-o', raw], timeout=120)
        sy = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        rom = raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
        expected = ','.join('{%d,"%s"}' % (scale, digits[::-1]) for scale, digits in expanded)
        outcomes = ','.join(str(delta & 65535) for _, _, _, delta in comparisons)
        checks = f'''
local expected={{{expected}}};local outcomes={{{outcomes}}};local n=0;local k=0
emu.addMemoryCallback(function()
 n=n+1;local e=expected[n];local s=emu.getState()
 require_value(e~=nil and s['cpu.a']==0 and s['cpu.y']==0x5aa5,'scaled status/Y '..n)
 local count=emu.read16({sy['ieee64_dec_n'] & 0x1ffff},emu.memType.snesWorkRam,false)
 local scale=emu.read16({sy['ieee64_dec_scale'] & 0x1ffff},emu.memType.snesWorkRam,false)
 require_value(count==#e[2] and scale==e[1],'scaled count/scale '..n)
 for i=1,#e[2] do require_value(emu.read({sy['ieee64_dec_digits'] & 0x1ffff}+i-1,emu.memType.snesWorkRam,false)==tonumber(e[2]:sub(i,i)),'scaled digit '..n..':'..i) end
end,emu.callbackType.exec,{sy['scaled_after']},{sy['scaled_after']})
emu.addMemoryCallback(function()
 k=k+1;local s=emu.getState();require_value(s['cpu.a']==outcomes[k] and s['cpu.y']==0x5aa5,'compare '..k)
end,emu.callbackType.exec,{sy['compare_after']},{sy['compare_after']})
emu.addMemoryCallback(function() require_value(n=={len(CASES)} and k=={len(comparisons)},'call counts') end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
        c.emulate(rom, sy, 0, extra_checks=checks)
    print(f'PASS: {len(CASES)} exact scaled values and {len(comparisons)} decimal comparisons, stages 1/3/4')

if __name__ == '__main__':
    main()
