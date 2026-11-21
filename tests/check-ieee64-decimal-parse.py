"""Target checks for the internal, decimal-only binary64 text parser."""
import os
import importlib.util
import argparse
from pathlib import Path
import random
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-decimal-parse-check'
c.OUT.mkdir(parents=True, exist_ok=True)

# Input, bytes consumed, expected bits, expected errno after initializing to 42
def f(value):
    return int.from_bytes(struct.pack('<d', float(value)), 'little')

CASES = [
    ('0', 1, 0, 42), ('-0.000e+7x', 9, 1<<63, 42),
    ('  +1.25x', 7, f('1.25'), 42), ('-.5!', 3, f('-0.5'), 42),
    ('12.34.56', 5, f('12.34'), 42), ('1e+', 1, f('1'), 42),
    ('  -xyz', 0, 0, 42), ('.', 0, 0, 42),
    ('000012345678901234567890.125e-5!', 31, f('12345678901234567890.125e-5'), 42),
    ('1.00000000000000011102230246251565404236316680908203125!', 55,
     f('1.00000000000000011102230246251565404236316680908203125'), 42),
    ('1.7976931348623157e308!', 22, f('1.7976931348623157e308'), 42),
    ('4.9406564584124654e-324!', 23, 1, 34),
    ('1e-999999!', 9, 0, 34), ('1e999999!', 8, 0x7ff0000000000000, 34),
    ('0e999999!', 8, 0, 42), ('-INFx', 4, 0xfff0000000000000, 42),
    ('Infinity!', 8, 0x7ff0000000000000, 42),
    ('nan(foo)!', 8, 0x7ff8000000000000, 42),
    ('-NaN(bad-)', 4, 0xfff8000000000000, 42),
]
minimum_half = 5 ** 1075
for integer, expected in ((minimum_half, 0), (minimum_half+1, 1)):
    subject = str(integer)+'e-1075'
    CASES.append((subject+'!', len(subject), expected, 34))
overflow_half = ((1 << 54)-1) << 970
for integer, expected, errno in ((overflow_half-1, 0x7fefffffffffffff, 42),
                                 (overflow_half, 0x7ff0000000000000, 34)):
    subject = str(integer)
    CASES.append((subject+'!', len(subject), expected, errno))
rng = random.Random(0xdec1a164)
for _ in range(12):
    digits = str(rng.randrange(10**16, 10**17))+''.join(str(rng.randrange(10)) for _ in range(12))
    point = rng.randrange(1, len(digits))
    subject = ('-' if rng.randrange(2) else '')+digits[:point]+'.'+digits[point:]+'e'+str(rng.randrange(-250, 251))
    CASES.append((subject+'!', len(subject), f(subject), 42))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=int, choices=(1, 2, 3, 4))
    args = parser.parse_args()
    _, plain, _ = c.compile_case('plain', 'int main(void){return 0;}')
    _, archive, labels = c.compile_case('archive', 'int main(void){return 0;}', extra_objects=[ROOT/'build/libc.a'])
    assert plain.read_bytes() == archive.read_bytes()
    assert '_ieee64_parse_decimal' not in labels
    source = c.OUT/'main.c'
    source.write_text('int parse_probe(void);int main(void){return parse_probe();}\n')
    # Keep exceptionally long exact midpoint subjects in separate ROMs
    batches=[];pending=[]
    for row in CASES:
        if len(row[0])>300:
            if pending:batches.append(pending);pending=[]
            batches.append([row])
        else:
            pending.append(row)
            if len(pending)==6:batches.append(pending);pending=[]
    if pending:batches.append(pending)
    for stage in ((args.stage,) if args.stage else (1, 2, 3, 4)):
        call = 'jsr .loword(__ieee64_parse_decimal)' if stage in (1, 2) else 'jsl __ieee64_parse_decimal'
        ret = 'rtl' if stage == 4 else 'rts'
        for batch, rows in enumerate(batches):
            lines = ['.setcpu "65816"', '.a16', '.i16', '.importzp __arith_lhs',
                     '.import __ieee64_parse_decimal, _errno',
                     '.export _parse_probe, _parse_after, _parsed_end',
                     '.segment "BSS"', '_parsed_end: .res 4', '.segment "CODE"', '_parse_probe:', 'phy']
            for i, _ in enumerate(rows):
                lines += ['lda #42', 'sta a:.loword(_errno)', f'pea .bankbyte(_text_{i})',
                          f'pea .loword(_text_{i})', 'lda #.loword(_parsed_end)',
                          'ldy #$5aa5', call, 'jsr .loword(_parse_after)',
                          'tsc', 'clc', 'adc #4', 'tcs']
            lines += ['lda #0', 'ply', ret, '_parse_after:', 'rts', '.segment "RODATA"']
            for i, (text, _, _, _) in enumerate(rows):
                lines += [f'.export _text_{i}', f'_text_{i}: .asciiz "{text}"']
            driver = c.OUT/f'driver-{stage}-{batch}.s'
            driver.write_text('\n'.join(lines)+'\n')
            raw = c.OUT/f'parse-{stage}-{batch}.raw'
            c.run([sys.executable, ROOT/'tools/build-rom.py', source, '--assembly', driver, '--stage', str(stage), '-o', raw], timeout=120)
            sy = {n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
            rom = raw.with_suffix('.sfc')
            c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
            entries = ','.join('{0x%016x,%d,%d}'%(value, sy[f'text_{i}']+end, errno) for i,(_,end,value,errno) in enumerate(rows))
            checks = f'''
local expected={{{entries}}};local calls=0
emu.addMemoryCallback(function()
 calls=calls+1;local s=emu.getState();local e=expected[calls]
 local function w(a)return emu.read16(a,emu.memType.snesWorkRam,false)end
 local got=w(0x02)|(w(0x04)<<16)|(w(0x06)<<32)|(w(0x08)<<48)
 local p=w({sy['parsed_end']&0x1ffff})|(w({(sy['parsed_end']&0x1ffff)+2})<<16)
 require_value(s['cpu.y']==0x5aa5 and got==e[1],'parse bits/Y '..calls..' got '..got..' expected '..e[1])
 require_value(p==e[2] and w({sy['errno']&0x1ffff})==e[3],'parse end/errno '..calls..' end '..p..' expected '..e[2])
end,emu.callbackType.exec,{sy['parse_after']},{sy['parse_after']})
emu.addMemoryCallback(function()require_value(calls=={len(rows)},'parse call count')end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
            c.emulate(rom, sy, 0, extra_checks=checks, timeout_seconds=30)
    print(f'PASS: {len(CASES)} binary64 decimal parsing cases, '+(f'stage {args.stage}' if args.stage else 'stages 1/2/3/4'))

if __name__ == '__main__':
    main()
