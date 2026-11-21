"""Check handwritten binary64 hex parsing against host IEEE conversion."""
import os
import importlib.util
from pathlib import Path
import random
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-hexparse-check'
c.OUT.mkdir(parents=True, exist_ok=True)

def f(subject, negative=False):
    try:
        value = float.fromhex(subject)
    except OverflowError:
        value = float('inf')
    if negative:
        value = -value
    return int.from_bytes(struct.pack('<d', value), 'little')

CASES = []
def add(subject, end=None, negative=False, errno=42, expected=None):
    if end is None:
        end = subject.index('!') if '!' in subject else len(subject)
    if expected is None:
        expected = f(subject[:end], negative)
    CASES.append((subject, end, int(negative), expected, errno))

add('0x1p0!')
add('0X1.8P+2!', negative=True)
add('0x0p99999!')
add('0x1p+', end=3)
add('0x.p2', end=1, expected=0)
add('0x', end=1, negative=True, expected=1<<63)
add('0x1.00000000000008p0!')
add('0x1.000000000000080000000001p0!')
add('0x1.00000000000018p0!')
add('0x1.fffffffffffffp1023!')
add('0x1.fffffffffffff7ffffffffp1023!')
add('0x1.fffffffffffff8p1023!', errno=34)
add('0x1p1024!', errno=34)
add('0x1p-1074!', errno=34)
add('0x1p-1075!', errno=34)
add('0x1.0000000001p-1075!', errno=34)
add('0x1p-999999!', errno=34)
add('0x000000.0000abc00p-7!')
rng = random.Random(0x64aabbcc)
for _ in range(18):
    digits = '0123456789abcdef'[rng.randrange(1,16)] + ''.join('0123456789abcdef'[rng.randrange(16)] for _ in range(27))
    point = rng.randrange(1, len(digits))
    add('0x'+digits[:point]+'.'+digits[point:]+'p'+str(rng.randrange(-900, 901))+'!', negative=bool(rng.randrange(2)))
for _ in range(24):
    digits = '0123456789abcdef'[rng.randrange(1,16)] + ''.join('0123456789abcdef'[rng.randrange(16)] for _ in range(24))
    point = rng.randrange(1, 6)
    exponent = rng.randrange(-1100, -999) if rng.randrange(2) else rng.randrange(990, 1051)
    subject = '0x'+digits[:point]+'.'+digits[point:]+'p'+str(exponent)+'!'
    negative = bool(rng.randrange(2))
    expected = f(subject[:-1], negative)
    exponent_bits = expected & 0x7ff0000000000000
    errno = 34 if exponent_bits in (0, 0x7ff0000000000000) else 42
    add(subject, negative=negative, errno=errno, expected=expected)

def main():
    _, plain, _ = c.compile_case('plain', 'int main(void){return 0;}')
    _, archive, labels = c.compile_case('archive', 'int main(void){return 0;}', extra_objects=[ROOT/'build/libc.a'])
    assert plain.read_bytes() == archive.read_bytes() and '_ieee64_hexparse' not in labels
    source = c.OUT/'main.c'
    source.write_text('int hex_probe(void);int main(void){return hex_probe();}\n')
    for stage in (1, 2, 3, 4):
        call = 'jsr .loword(__ieee64_hexparse)' if stage in (1,2) else 'jsl __ieee64_hexparse'
        ret = 'rtl' if stage == 4 else 'rts'
        lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                 '.import __ieee64_hexparse, _errno', '.export _hex_probe, _hex_after, _hex_end',
                 '.segment "BSS"', '_hex_end: .res 4', '.segment "CODE"', '_hex_probe:', 'phy']
        for i, (_, _, sign, _, _) in enumerate(CASES):
            lines += ['lda #42', 'sta a:.loword(_errno)', f'pea {sign}', f'pea .bankbyte(_text_{i})',
                      f'pea .loword(_text_{i})', 'lda #.loword(_hex_end)', 'ldy #$5aa5',
                      call, 'jsr .loword(_hex_after)', 'tsc', 'clc', 'adc #6', 'tcs']
        lines += ['lda #0', 'ply', ret, '_hex_after:', 'rts', '.segment "RODATA"']
        for i, (text, _, _, _, _) in enumerate(CASES):
            lines += [f'.export _text_{i}', f'_text_{i}: .asciiz "{text}"']
        driver = c.OUT/f'driver-{stage}.s'
        driver.write_text('\n'.join(lines)+'\n')
        raw = c.OUT/f'hex-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',source,'--assembly',driver,'--stage',str(stage),'-o',raw],timeout=120)
        sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        rom=raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        rows=','.join('{0x%016x,%d,%d}'%(value,sy[f'text_{i}']+end,err) for i,(_,end,_,value,err) in enumerate(CASES))
        checks=f'''
local expected={{{rows}}};local calls=0
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState();local e=expected[calls]
 local function w(a)return emu.read16(a,emu.memType.snesWorkRam,false)end
 local got=w(0x02)|(w(0x04)<<16)|(w(0x06)<<32)|(w(0x08)<<48)
 local p=w({sy['hex_end']&0x1ffff})|(w({(sy['hex_end']&0x1ffff)+2})<<16)
 require_value(s['cpu.y']==0x5aa5 and got==e[1],'hex bits/Y '..calls..' got '..got..' expected '..e[1])
 require_value(p==e[2] and w({sy['errno']&0x1ffff})==e[3],'hex end/errno '..calls..' end '..p..' expected '..e[2])
end,emu.callbackType.exec,{sy['hex_after']},{sy['hex_after']})
emu.addMemoryCallback(function()require_value(calls=={len(CASES)},'hex call count')end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
        c.emulate(rom,sy,0,extra_checks=checks)
    print(f'PASS: {len(CASES)} binary64 hexadecimal parsing cases, stages 1/2/3/4')

if __name__ == '__main__':
    main()
