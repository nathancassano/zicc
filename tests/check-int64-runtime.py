"""Compare the 64-bit assembly routines with results computed using Python integers."""
import os
import importlib.util
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'int64-runtime-check'
c.OUT.mkdir(parents=True, exist_ok=True)
MASK = (1 << 64) - 1
rng = random.Random(0x64a11)


def signed(n):
    return n - (1 << 64) if n & (1 << 63) else n


def words(value):
    return ','.join('$%04x' % ((value >> n) & 0xffff) for n in (0, 16, 32, 48))


def quotient(a, b):
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def vectors():
    edge = [0, 1, 2, 0xffff, 0x10000, 0xffffffff, 1 << 32,
            (1 << 63)-1, 1 << 63, MASK-1, MASK]
    pairs = [(a, b) for a in edge for b in edge]
    pairs += [(rng.getrandbits(64), rng.getrandbits(64)) for _ in range(150)]
    result = {}
    for name in ('shl', 'ushr', 'sshr'):
        result[name] = []
        operands = edge + [rng.getrandbits(64) for _ in range(12)]
        for index, a in enumerate(operands):
            shifts = range(64) if index in (0, 1, 7, 8, 10, 11) else (0, 1, 15, 16, 17, 31, 32, 33, 47, 48, 49, 63)
            for shift in shifts:
                v = (a << shift) if name == 'shl' else (a >> shift) if name == 'ushr' else (signed(a) >> shift)
                result[name].append((a, shift, v & MASK))
    result['mul'] = [(a, b, (a*b) & MASK) for a,b in pairs]
    result['mul'] += [(a,b,(a*b)&MASK) for a in (0xfedcba9876543210,MASK)
                      for b in (255,256,65535,65536,1 << 32,1 << 48,(1 << 32) | (1 << 16))]
    result['ucmp'] = [(a,b, (a > b) - (a < b)) for a,b in pairs]
    result['scmp'] = [(a,b, (signed(a) > signed(b)) - (signed(a) < signed(b))) for a,b in pairs]
    valid = [(a,b) for a,b in pairs if b]
    # Exercise the hardware divisor boundary and carry a remainder across
    # every byte of dividends containing leading and interior zero words
    valid += [(a,b) for a in (0x1234,0x1234000000,0xfedc000076540010,MASK)
             for b in (3,127,255,256,257,32768,65533,65535)]
    valid += [(a,b) for a in (0x1234000000,0xfedc000076540010,MASK)
             for b in (0x10001,0x100000001,0x1000000000001)]
    valid += [(a,b) for a in (0,0xfffe,0x10000,0x765432100000fedc,0x876543210000fedc,MASK)
             for b in (0x80000001,0xffffffff,0x800000000001,0xffffffffffff,0x7fffffffffffffff)]
    result['udiv'] = [(a,b,a//b) for a,b in valid]
    result['umod'] = [(a,b,a%b) for a,b in valid]
    valid = [(a,b) for a,b in valid if not (a == 1 << 63 and b == MASK)]
    result['sdiv'] = [(a,b,quotient(signed(a),signed(b)) & MASK) for a,b in valid]
    result['smod'] = [(a,b,(signed(a)-quotient(signed(a),signed(b))*signed(b)) & MASK) for a,b in valid]
    return result


def main():
    all_vectors = vectors()
    # Individual ROMs keep each table within a bank and make helper execution
    # observable independently. Each loop must complete every vector
    workspace = c.OUT/'workspace.s'
    workspace.write_text('.exportzp __arith_lhs,__arith_rhs\n.segment "DP_SCRATCH": zeropage\n'
                         '__arith_lhs: .res 4\n__arith_rhs: .res 28\n')
    c.run([c.CC65/'ca65.exe', '-o', c.OUT/'workspace.o', workspace])
    objects = []
    for name in ('shift', 'mul', 'div', 'cmp'):
        obj = c.OUT/(name+'.o')
        c.run([c.CC65/'ca65.exe', '--cpu', '65816', '-g', '-o', obj, ROOT/'runtime/int64'/(name+'.s')])
        objects.append(obj)
    archive = c.OUT/'int64.a'
    archive.unlink(missing_ok=True)
    c.run([c.CC65/'ar65.exe', 'a', archive, *objects])
    plain = 'int main(void){return 0;}'
    _, baseline, _ = c.compile_case('baseline', plain)
    _, with_archive, baseline_labels = c.compile_case('baseline-archive', plain, extra_objects=[archive])
    assert baseline.read_bytes() == with_archive.read_bytes(), 'unused archive changed baseline ROM'
    assert not any(name in baseline_labels for name in
                   ('_shl64', '_mul64', '_udiv64', '_scmp64'))
    groups = {
        'shift': {'shl', 'ushr', 'sshr'}, 'mul': {'mul'},
        'div': {'udiv', 'umod', 'sdiv', 'smod'}, 'cmp': {'ucmp', 'scmp'},
    }
    for name, rows in all_vectors.items():
        compare = name.endswith('cmp')
        # A 24-byte record keeps a uniform format; shifts use R's low word
        assert len(rows) * 24 < 65536
        lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                 '.import __'+name+'64', '.export _int64_probe', '.segment "CODE"',
                 '_int64_probe:', '    ldx #0', '@loop:']
        for offset in range(0, 16, 2):
            lines += [f'    lda f:table+{offset},x', f'    sta z:__arith_lhs+{offset}']
        lines += ['    phx', '    jsr .loword(__'+name+'64)', '    plx']
        if compare:
            lines += ['    cmp f:table+16,x', '    bne @bad']
        else:
            for offset in range(0, 8, 2):
                lines += [f'    lda z:__arith_lhs+{offset}', f'    cmp f:table+{16+offset},x', '    bne @bad']
        lines += ['    txa', '    clc', '    adc #24', '    tax', f'    cpx #{len(rows)*24}',
                  '    bne @loop', '    lda #0', '    rts', '@bad:', '    lda #1', '    rts',
                  '.segment "RODATA"', 'table:']
        for a,b,v in rows:
            lines.append('    .word '+words(a)+','+words(b)+','+words(v & MASK))
        source = c.OUT/(name+'-driver.s')
        source.write_text('\n'.join(lines)+'\n')
        obj = source.with_suffix('.o')
        c.run([c.CC65/'ca65.exe', '--cpu', '65816', '-g', '-o', obj, source])
        _, rom, labels = c.compile_case(name, 'int int64_probe(void); int main(void){return int64_probe();}',
                                       extra_objects=[obj,c.OUT/'workspace.o',archive])
        selected = next(group for group in groups.values() if name in group)
        assert {n for n in all_vectors if '_'+n+'64' in labels} == selected, name
        helper = labels['_'+name+'64']
        checks = f'''
local helper_calls=0
emu.addMemoryCallback(function() helper_calls=helper_calls+1 end,emu.callbackType.exec,{helper},{helper})
emu.addMemoryCallback(function()
 require_value(helper_calls=={len(rows)},'helper call count: '..helper_calls)
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
        c.emulate(rom, labels, 0, extra_checks=checks)
        print(f'PASS {name}: {len(rows)} vectors', flush=True)

    # The bank-aware builder rewrites runtime JSR/RTS for long calls. Exercise
    # signed division, including its internal negate subroutine, in both long
    # runtime-call stages using the same independently generated vectors
    original = (c.OUT/'sdiv-driver.s').read_text()
    caller = c.OUT/'banked-driver.c'
    caller.write_text('int int64_probe(void); int main(void){return int64_probe();}')
    for stage in (3, 4):
        driver = c.OUT/f'banked-{stage}.s'
        text = original.replace('jsr .loword(__sdiv64)', 'jsl __sdiv64')
        if stage == 4:
            text = text.replace('    rts\n', '    rtl\n')
        driver.write_text(text)
        raw = c.OUT/f'banked-{stage}.raw'
        c.run([sys.executable, ROOT/'tools/build-rom.py', caller, '--assembly', driver,
               '--stage', str(stage), '-o', raw], timeout=120)
        labels = {n.removeprefix('_'): int(a,16) for a,n in re.findall(
            r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        rom = raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
        helper = labels['_sdiv64']
        count = len(all_vectors['sdiv'])
        checks = f'''
local helper_calls=0
emu.addMemoryCallback(function() helper_calls=helper_calls+1 end,emu.callbackType.exec,{helper},{helper})
emu.addMemoryCallback(function() require_value(helper_calls=={count},'banked helper calls') end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
        c.emulate(rom, labels, 0, extra_checks=checks)
        print(f'PASS banked stage {stage}: {count} signed division vectors', flush=True)


if __name__ == '__main__':
    main()
