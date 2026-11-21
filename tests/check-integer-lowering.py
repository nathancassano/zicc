"""Count the work for word and long division by powers of two and for shifts whose count is supplied at run time."""
import os
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'integer-lowering-check'
sys.path.insert(0, str(ROOT / 'tools'))
from mesen_core import Core

spec = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def division_cases(bits):
    result = []
    for signed in (False, True):
        for shift in range(bits):
            for negative in ((False, True) if signed else (False,)):
                if signed and shift == bits-1 and not negative:
                    continue
                divisor = -(1 << shift) if negative else 1 << shift
                for remainder in (False, True):
                    name = f'{"s" if signed else "u"}_{"r" if remainder else "q"}_{shift}_{int(negative)}'
                    t = ('long' if bits == 32 else 'int') if signed else ('unsigned long' if bits == 32 else 'unsigned')
                    literal = str(divisor) + ('L' if signed and bits == 32 else 'UL' if bits == 32 else 'U' if not signed else '')
                    if signed and divisor == -(1 << (bits-1)):
                        literal = f'(-{(1 << (bits-1))-1}' + ('L' if bits == 32 else '') + '-1)'
                    expression = f'x {"%" if remainder else "/"} {literal}'
                    def expected(value, d=divisor, s=signed, r=remainder):
                        if not s:
                            return value % d if r else value // d
                        n = value if value < 1 << (bits-1) else value-(1 << bits)
                        q = (abs(n)//abs(d)) * (-1 if (n < 0) != (d < 0) else 1)
                        return (n-q*d if r else q) & ((1 << bits)-1)
                    result.append(dict(name=name, type=t, expr=expression, expected=expected,
                                       skip_min=signed and divisor == -1))
    return result


def shift_cases():
    return [
        dict(name='left', type='unsigned', expr='x << count', expected=lambda x: (x << (x & 15)) & 65535),
        dict(name='right', type='unsigned', expr='x >> count', expected=lambda x: x >> (x & 15)),
        dict(name='signed_right', type='int', expr='x >> count',
             expected=lambda x: ((x if x < 32768 else x-65536) >> (x & 15)) & 65535),
        dict(name='shared_right', type='unsigned', expr='x >> x', count_is_input=True,
             expected=lambda x: x >> (x & 15)),
        dict(name='signed_shared_right', type='int', expr='x >> x', count_is_input=True,
             expected=lambda x: ((x if x < 32768 else x-65536) >> (x & 15)) & 65535),
        dict(name='lookup_mod', type='unsigned', expr='2 << ((x % 4) * 2)', expected=lambda x: 2 << ((x % 4)*2)),
        dict(name='lookup_mask', type='unsigned', expr='7U << (1 + (x & 3))', expected=lambda x: 7 << (1+(x & 3))),
        dict(name='lookup_signed', type='int', expr='-128 >> ((x & 7) + 1)',
             expected=lambda x: (-128 >> ((x & 7)+1)) & 65535),
    ]


def run_group(name, bits, cases, modes):
    rng = random.Random(65816 + bits)
    mask = (1 << bits)-1
    values = sorted({0, 1, 2, 3, 4, 7, 8, 15, 16, 127, 128, 255, 256,
                     (1 << (bits-1))-1, 1 << (bits-1), mask-3, mask-2, mask-1, mask,
                     *(rng.getrandbits(bits) for _ in range(24))})
    scalar = 'unsigned long' if bits == 32 else 'unsigned'
    suffix = 'UL' if bits == 32 else 'U'
    kernels = '\n'.join(f'{row["type"]} {row["name"]}({row["type"]} x, unsigned count)'
                        f'{{return {row["expr"]};}}' for row in cases)
    declarations = '\n'.join(f'{row["type"]} {row["name"]}({row["type"]}, unsigned);' for row in cases)
    reports = {}
    for mode in modes:
        checks, call_counts = [], []
        for i, row in enumerate(cases):
            excluded = (1 << (bits - 1)) if row.get('skip_min') else None
            # Only the native word path promises modulo-16 behavior for raw counts
            max_input = 15 if mode == 'fallback' and row.get('count_is_input') else mask
            condition = f'input != {excluded}{suffix} && ' if excluded is not None else ''
            if max_input < mask:
                condition += f'input <= {max_input}{suffix} && '
            checks.append(f'if ({condition}({scalar}){row["name"]}(({row["type"]})input, (unsigned)input & 15) != expected[{i}]) return {i+1};')
            call_counts.append(sum(value != excluded and value <= max_input for value in values))
        driver = declarations + f'''
{scalar} input, expected[{len(cases)}];
__noinline int check_vector(void){{
{chr(10).join(checks)}
return 0;}}
int main(void){{unsigned i;for(i=0;i<{len(values)};i++)if(check_vector())return 1;return 0;}}
'''
        directory = OUT / (name + '-' + mode)
        directory.mkdir(parents=True, exist_ok=True)
        c.OUT = directory
        flags = ['--no-strength-reduction'] if mode == 'fallback' else []
        source = directory / 'kernels.c'
        source.write_text(kernels, encoding='ascii')
        c.run([ROOT / 'build/zicc.exe', source, '-o', source.with_suffix('.s'), *flags])
        assembly = source.with_suffix('.s').read_text()
        if mode == 'optimized':
            assert not re.search(r'\b__(?:u|s)(?:div|mod)(?:8|16|32)\b|\b__shl32\b|\b__sshr32\b|\b__ushr32\b', assembly), name
            if name == 'shifts':
                assert assembly.count('; bounded word shift lookup') >= 3
                assert assembly.count('; native variable word shift') >= 3
                for kernel in ('shared_right', 'signed_shared_right'):
                    body = assembly.split('_'+kernel+':\n', 1)[1].split('__size_'+kernel, 1)[0]
                    assert '    cpx #$0010\n' in body, body
        c.run([c.CC65 / 'ca65.exe', '--cpu', '65816', '-g', '-o', source.with_suffix('.o'), source.with_suffix('.s')])
        workspace = directory / 'workspace.s'
        workspace.write_text('.exportzp __arith_lhs,__arith_rhs\n.segment "DP_SCRATCH": zeropage\n__arith_lhs:.res 4\n__arith_rhs:.res 28\n')
        c.run([c.CC65 / 'ca65.exe', '-o', workspace.with_suffix('.o'), workspace])
        _, rom, sy = c.compile_case('driver', driver, flags=flags,
                                    extra_objects=[source.with_suffix('.o'), workspace.with_suffix('.o'), ROOT / 'build/integers.o'])
        script = 'local vector=0\nlocal calls={}\nlocal cases=' + json.dumps(values).replace('[', '{').replace(']', '}') + '\n'
        expected = [[row['expected'](value) for row in cases] for value in values]
        script += 'local expected={' + ','.join('{' + ','.join(map(str, row)) + '}' for row in expected) + '}\n'
        script += '''local mem=emu.memType.snesWorkRam
local function write(address,value,bytes)
 for i=0,bytes-1 do emu.write((address+i)&0x1ffff,(value>>(8*i))&255,mem) end
end
local function check(ok,msg)if not ok then error(msg)end end
'''
        for row in cases:
            key = row['name']
            script += f"calls['{key}']=0;emu.addMemoryCallback(function()calls['{key}']=calls['{key}']+1 end,emu.callbackType.exec,{sy[key]},{sy[key]})\n"
        script += f'''emu.addMemoryCallback(function()
 vector=vector+1;check(cases[vector]~=nil,'extra vector')
 write({sy['input']},cases[vector],{bits//8})
 for i,v in ipairs(expected[vector]) do write({sy['expected']}+(i-1)*{bits//8},v,{bits//8}) end
end,emu.callbackType.exec,{sy['check_vector']},{sy['check_vector']})
emu.addMemoryCallback(function()
 local s=emu.getState();check(s['cpu.a']==0,'result '..s['cpu.a']);check(s['cpu.sp']==0x4ff,'stack')
 check(s['cpu.d']==0 and s['cpu.dbr']==0x7e and s['cpu.y']==0,'register ABI')
 check(vector=={len(values)},'vector count')
'''
        for row, count in zip(cases, call_counts):
            script += f"check(calls['{row['name']}']=={count},'{row['name']} execution count')\n"
        script += f"emu.log('PASS integer lowering {name} {mode}');emu.breakExecution()end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})\n"
        lua = directory / 'check.lua'
        lua.write_text(script, encoding='ascii')
        # Mesen's DLL lifecycle permits one Core instance in each process
        c.run([sys.executable, __file__, '--worker', rom, lua, directory / 'emulator'], timeout=90)
        reports[mode] = dict(rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
                             vectors=len(values), functions=len(cases),
                             calls=sum(call_counts))
        (directory / 'report.json').write_text(json.dumps(reports[mode], indent=2) + '\n')
        print('PASS', name, mode, reports[mode], flush=True)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', nargs=3)
    parser.add_argument('--group', action='append', choices=('word', 'long', 'shifts'))
    parser.add_argument('--mode', action='append', choices=('optimized', 'fallback'))
    args = parser.parse_args()
    if args.worker:
        rom, lua, home = map(Path, args.worker)
        core = Core(home)
        try:
            core.load(rom, lua, lua.read_text())
            core.start()
            print(core.wait_for('PASS integer lowering', 60))
        finally:
            core.close()
        return
    OUT.mkdir(parents=True, exist_ok=True)
    results = {name: run_group(name, bits, cases, args.mode or ('optimized', 'fallback')) for name, bits, cases in
               [('word', 16, division_cases(16)), ('long', 32, division_cases(32)), ('shifts', 16, shift_cases())]
               if not args.group or name in args.group}
    (OUT / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    main()
