"""Check where each storage qualifier puts a variable, how startup fills it, and how ordinary pointers reach it."""
import os
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'application-wram-check'
sys.path.insert(0, str(ROOT / 'tools'))
import application_wram as wram
from runtime_ram import backfill

spec = importlib.util.spec_from_file_location('wram_support', ROOT / 'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
CC65 = c.CC65
ACCESS = ROOT / 'tests/wram/access.c'
OBJECTS = ROOT / 'tests/wram/objects.c'
CROSSING = ROOT / 'tests/wram/crossing.c'
ROWS = ROOT / 'tests/wram/wide-rows.c'
HEAP = ROOT / 'tests/wram/heap.c'
HEAP_CROSSING = ROOT / 'tests/wram/heap-crossing.c'
LEGACY = [ROOT / 'tests/wram/legacy.c', ROOT / 'tests/wram/legacy-helper.c']


def build(name, sources, *options, checkout=ROOT):
    raw = OUT / f'{name}.raw'
    c.run([sys.executable, checkout / 'tools/build-rom.py', *sources, *options, '-o', raw],
          cwd=checkout, timeout=180, binary64=False)
    return raw


def reject(command, name, diagnostic):
    proc = subprocess.run(list(map(str, command)), cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert proc.returncode and diagnostic in proc.stderr, (name, command, proc.stdout, proc.stderr)


def labels(raw):
    return {n.removeprefix('_'): int(a, 16) for a, n in
            re.findall(r'^al (\w+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}


def manifest(raw):
    return json.loads(raw.with_suffix('.allocation.json').read_text())


def disassemble(raw, label, address, size, mode):
    image = raw.read_bytes()
    if len(image) >= 65536 and image[0xFFD5] == 0x31:
        offset = address - 0xC00000
    else:
        offset = ((address >> 16) & 0x7F) * 0x8000 + (address & 0x7FFF)
    base = OUT / f'{raw.stem}-{label}'
    excerpt = base.with_suffix('.bin')
    info = base.with_suffix('.info')
    output = base.with_suffix('.dis')
    excerpt.write_bytes(image[offset:offset+size])
    start = address & 0xFFFF
    info.write_text(f'RANGE {{ START ${start:04X}; END ${start+size-1:04X}; TYPE Code; ADDRMODE "{mode}"; }};\n')
    c.run([CC65 / 'da65.exe', '--cpu', '65816', '-S', hex(start), '-i', info, '-o', output, excerpt])
    return output


def checkpoint_address(sy, name):
    address = sy[name]
    if name in ('reset_entry', '_vector_nmi') and address >> 16 == 0x80:
        return address & 0xFFFF  # A LoROM hardware vector enters the bank-zero mirror
    return address


def target(raw, *, seed=True, interrupts=False, expected=0):
    sy = labels(raw)
    rom = raw.with_suffix('.sfc')
    c.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
    checks = f'''
local exit_seen=false
emu.addMemoryCallback(function()
 if not exit_seen then exit_seen=true; print('EXIT',emu.getState()['cpu.a']) end
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    if interrupts:
        nmi = checkpoint_address(sy, '_vector_nmi')
        checks += f'''
local filling=false
local during_fill=0
emu.addMemoryCallback(function() filling=true end,emu.callbackType.exec,{sy['far_memset']},{sy['far_memset']})
emu.addMemoryCallback(function()
 if filling then during_fill=during_fill+1 end
end,emu.callbackType.exec,{nmi},{nmi})
emu.addMemoryCallback(function()
 filling=false
 require_value(during_fill>0,'NMI did not interrupt far_memset')
 print('NMI_DURING_FILL',during_fill)
end,emu.callbackType.exec,{sy['check_fill']},{sy['check_fill']})
'''
    return c.emulate(rom, sy, expected, seed=seed, extra_checks=checks, timeout_seconds=25)


def source(name, code):
    path = OUT / f'{name}.c'
    path.write_text(code)
    return path


def compile_object(path, directory, checkout=ROOT):
    asm = directory / (path.stem + '.s')
    c.run([checkout / 'build/zicc.exe', path, '-o', asm, '-I', checkout / 'include'], binary64=False)
    return assemble(asm, directory)


def assemble(path, directory, *flags):
    obj = directory / (path.stem + '.o')
    c.run([CC65 / 'ca65.exe', '--cpu', '65816', '-g', '-I', ROOT, *flags, '-o', obj, path])
    return obj


def manual(name, layout, units, extra=(), *, checkout=ROOT, startup=None, wrapped=True):
    raw = OUT / f'{name}.raw'
    cfg = checkout / 'linker' / (layout + '.cfg')
    hirom = layout.startswith('hirom')
    directory = OUT / ('manual-' + checkout.name)
    directory.mkdir(exist_ok=True)
    vectors = directory / ('vector-hi' if hirom else 'vector-lo')
    vectors.mkdir(exist_ok=True)
    vector = assemble(checkout / 'runtime/vectors.s', vectors, *(['-D', 'HIROM=1'] if hirom else []))
    if hirom:
        header_source = vectors / 'header.s'
        header_source.write_text('.segment "HEADER"\n.res 21,0\n.byte $31\n.res 10,0\n')
    else:
        header_source = checkout / 'runtime/rom_header.s'
    header = assemble(header_source, directory)
    startup = startup or assemble(checkout / 'runtime/startup.s', directory)
    linker = [sys.executable, checkout / 'tools/link-runtime-ram.py'] if wrapped else [CC65 / 'ld65.exe']
    return raw, [*linker, '-C', cfg, *(['-D', '__NEAR_ROM_SIZE__=64'] if hirom else []), *extra,
                 '-o', raw, '-m', raw.with_suffix('.map'), '-Ln', raw.with_suffix('.labels'),
                 '--dbgfile', raw.with_suffix('.dbg'),
                 startup, *units, vector, header]


def allocation_checks():
    runtime = backfill([])
    start = 0x7E0500

    def obj(name, size, alignment=1, crossing=False):
        return wram.Object(name, crossing, (wram.Part(name, size, alignment, True),))

    # A greedy near-first assignment of size 9 wastes the space needed by
    # sizes 6 and 5. The second-bank size 9 assignment fits
    constrained = dict(runtime, lower=wram.BOUNDARY + 9)
    alternative = wram.place([obj('a', 9), obj('b', 6), obj('c', 5)],
                             start, wram.BOUNDARY - 11, constrained, False)
    assert next(o for o in alternative['objects'] if o['name'] == 'a')['address'] == wram.BOUNDARY
    heap_first = wram.place([obj('whole', 200, crossing=True)], start, start, runtime, True)
    assert heap_first['objects'][0]['address'] == wram.BOUNDARY and not heap_first['objects'][0]['crossing']
    heap_best = wram.place([obj('a', 10), obj('b', 8), obj('c', 8)], start, start,
                          dict(runtime, lower=wram.BOUNDARY + 16), True)
    assert heap_best['near_end'] == start + 10
    capacity = 0x800000 - start
    exact = wram.place([obj('exact', capacity, 2, True)], start, start, runtime, True)
    assert exact['objects'][0]['address'] == start and exact['heap']['payload'] == 0
    for items, bottom, live in [
        ([obj('overflow', capacity + 1, 1, True)], start, runtime),
        ([obj('padding', 3, 2)], wram.BOUNDARY-3, dict(runtime, lower=wram.BOUNDARY)),
        ([obj('collision', 65536, 2)], start, backfill([dict(name='runtime', size=1, alignment=1)])),
    ]:
        try:
            wram.place(items, start, bottom, live, False)
        except ValueError as error:
            assert 'overflow' in str(error)
        else:
            raise AssertionError(f'accepted overflowing object {items[0]}')


def frontend_checks(directory):
    cases = {
        'automatic': ('void f(void) { __hiram int x; }', 'static-storage'),
        'parameter': ('void f(__xbankram int x);', 'static-storage'),
        'function': ('__hiram int f(void);', 'cannot qualify a function'),
        'typedef': ('typedef __farram int my_int;', 'conflicting WRAM placement'),
        'conflict': ('__hiram __xbankram unsigned x;', 'conflicting WRAM placement'),
        'low-conflict': ('__loram __hiram unsigned x;', 'conflicting WRAM placement'),
        'dp-conflict': ('__dpage __hiram unsigned x;', 'conflicting WRAM placement'),
        'redeclare': ('extern __hiram int x; __xbankram int x;', 'conflicting WRAM placement'),
        'const-store': ('__hiram const unsigned x=1; void f(void) { x=2; }', 'writable scalar'),
        'near-parameter': ('void f(char *p); __hiram char s[5]; void g(void) { f(s+1); }', 'incompatible argument'),
        'near-cast': ('struct A {char byte;}; __hiram struct A x; char *p=(char *)&x.byte;', 'spillable WRAM address'),
        'hiram-limit': ('__hiram char huge[65537UL];', 'object size exceeds 65536 bytes'),
        'near-limit': ('char huge[65537UL];', "object size exceeds 65534 bytes for 'huge' in ordinary 16-bit WRAM"),
    }
    for name, (text, diagnostic) in cases.items():
        path = source(name, text)
        reject([ROOT / 'build/zicc.exe', path, '-o', directory / (name + '.s')], name, diagnostic)


def codegen_checks(report):
    padding = source('spill-padding', 'unsigned char ordinary[64252];\n')
    cache = ['--compile-cache', OUT / 'compile-cache']
    for name, inputs, options, near in (
        ('near', [OBJECTS, ACCESS], cache, True),
        ('spill', [OBJECTS, ACCESS, padding], cache, False),
        ('lto', [OBJECTS, ACCESS], ['--lto'], True),
    ):
        raw = build(name, inputs, *options)
        data = manifest(raw)
        sy = labels(raw)
        layout = data['application_wram']
        assert (sy['pixels'] < wram.BOUNDARY) == near
        assert layout['specialized'] == near
        assert next(r['size'] for r in layout['objects'] if r['name'].endswith('fixed_palette')) == 8
        image = raw.read_bytes()
        load = sy['read_pixel'] - 0xC00000
        opcode = bytes.fromhex('bd' if near else 'bf')
        operand = sy['pixels'].to_bytes(3, 'little')[:2 if near else 3]
        instruction = image.find(opcode+operand, load, load+64)
        assert instruction >= 0, (name, image[load:load+32].hex())
        disassemble(raw, 'indexed-load', instruction + 0xC00000, 1+len(operand), 'Mx')
        if near:
            update = sy['update_pixel'] - 0xC00000
            assert bytes.fromhex('fe')+operand in image[update:update+64]
        report[name] = target(raw)
    shifted = build('stack-override', [OBJECTS, ACCESS], '--stack-size', '1536')
    assert manifest(shifted)['application_wram']['near_start'] == 0x7E0700
    report['stack-override'] = target(shifted)


def target_checks(report, directory):
    near_full = source('near-overflow', '''unsigned char primary[64256], remaining[2];
int main(void) { return 0; }
''')
    near_error = '16-bit WRAM in bank $7E is full.'
    reject([sys.executable, ROOT / 'tools/build-rom.py', near_full, '-o', OUT / 'near-overflow.raw'],
           'automatic-near-overflow', near_error + ' Static allocations and alignment need 64,258 bytes')
    raw, command = manual('manual-near-overflow', 'lorom32', [compile_object(near_full, directory)])
    reject(command, 'manual-near-overflow', near_error +
           ' Static allocations exceed the available space by at least 2 bytes')
    exact = source('exact', '__xbankram unsigned char all[129792UL]; int main(void){return 0;}\n')
    raw = build('exact', [exact])
    layout = manifest(raw)['application_wram']
    assert layout['objects'][0]['end'] == 0x800000
    report['exact'] = target(raw)
    reject([sys.executable, ROOT / 'tools/build-rom.py', exact, '--stack-size', '1025',
            '-o', OUT / 'overflow.raw'], 'stack-overflow', 'expanded WRAM overflow')
    over = source('one-byte-over', '__xbankram unsigned char all[129793UL]; int main(void){return 0;}\n')
    reject([sys.executable, ROOT / 'tools/build-rom.py', over, '-o', OUT / 'one-byte-over.raw'],
           'one-byte-over', 'expanded WRAM overflow')
    rows = build('wide-rows', [ROWS])
    report['wide-rows'] = target(rows)
    # Keep each preprocessing token small while spanning more than 64 KiB
    # of a single initialized field and placing the following member beyond it
    text = '\n'.join('"' + 'a' * 1000 + '"' for _ in range(66))
    record = source('wide-record', '''
struct wide { unsigned char text[66000UL]; unsigned long last; };
__xbankram struct wide wide_record = {
''' + text + ''',
    0x12345678UL
};
__noinline unsigned long copy_and_read(struct wide * __far to, const struct wide * __far from)
{
    *to = *from;
    return to->last;
}
int main(void)
{
    if (sizeof(wide_record) != 66004UL || wide_record.text[65536UL] != 'a')
        return 1;
    if ((unsigned long)&wide_record.last - (unsigned long)&wide_record != 66000UL)
        return 2;
    return copy_and_read(&wide_record, &wide_record) != 0x12345678UL;
}
''')
    report['wide-record'] = target(build('wide-record', [record]))
    exhausted = source('near-exhausted', '''#include <stdlib.h>
__xbankram unsigned char crossing[80000UL];
int main(void){crossing[0]=42;return malloc(1)!=0 || crossing[0]!=42;}
''')
    raw = build('near-exhausted', [exhausted])
    assert manifest(raw)['application_wram']['heap']['payload'] == 0
    report['near-exhausted'] = target(raw)
    heap = build('heap', [HEAP])
    assert manifest(heap)['application_wram']['heap']['linked']
    report['heap'] = target(heap)
    heap_long = build('heap-long-calls', [HEAP], '--stage', '4')
    report['heap-long-calls'] = target(heap_long)
    heap_crossing = build('heap-crossing', [HEAP_CROSSING], '--stage', '3')
    report['heap-crossing'] = target(heap_crossing)
    crossing = build('crossing', [CROSSING])
    assert manifest(crossing)['application_wram']['objects'][0]['crossing']
    report['crossing'] = target(crossing, interrupts=True)

    # A live runtime reservation makes this previously exact fit impossible
    reservation = directory / 'live-ram.s'
    reservation.write_text('.segment "RUNTIME_BSS"\n.res 1\n')
    reject([sys.executable, ROOT / 'tools/build-rom.py', exact, '--assembly', reservation,
            '-o', OUT / 'collision.raw'], 'backfill-collision', 'expanded WRAM overflow')


def manual_checks(report, directory):
    defs = compile_object(OBJECTS, directory)
    driver = compile_object(ACCESS, directory)
    cross = compile_object(CROSSING, directory)
    wrong = compile_object(source('wrong-decl', 'extern unsigned char pixels[]; int main(void){return pixels[0];}'), directory)
    archive = directory / 'objects.a'
    archive.unlink(missing_ok=True)
    c.run([CC65 / 'ar65.exe', 'a', archive, defs])
    libs = [ROOT / 'build/dp-scratch.o', ROOT / 'build/integers.o', ROOT / 'build/arithmetic.o']
    for config in sorted((ROOT / 'linker').glob('*.cfg')):
        raw, command = manual('manual-'+config.stem, config.stem, [driver, archive, *libs])
        c.run(command)
        assert manifest(raw)['application_wram']['objects']
        if config.stem in {'lorom32', 'hirom64'}:
            report[raw.stem] = target(raw)
    raw, command = manual('bare-ld65', 'lorom32', [driver, defs, *libs], wrapped=False)
    reject(command, 'bare-ld65', 'ZWRAM_')
    raw, command = manual('wrong-decl', 'lorom32', [wrong, defs, *libs])
    reject(command, 'wrong-decl', 'conflicting WRAM placement')
    memory = compile_object(ROOT / 'runtime/far-memory.c', directory)
    for mapping in ('lorom128', 'hirom128'):
        raw, command = manual('cross-'+mapping, mapping, [cross, memory, *libs])
        c.run(command)
        parts = manifest(raw)['application_wram']['objects'][0]['parts']
        assert len({p['load'] >> 16 for p in parts}) >= 2
        if mapping.startswith('lorom'):
            assert all(p['load'] & 0xFFFF >= 0x8000 for p in parts)
        assert all((p['load'] & 0xFFFF) + p['size'] <= 0x10000 for p in parts)
        report[raw.stem] = target(raw, interrupts=True)
    heap = compile_object(HEAP, directory)
    heap_lib = directory / 'far-library.a'
    heap_lib.unlink(missing_ok=True)
    c.run([CC65 / 'ar65.exe', 'a', heap_lib, memory,
           assemble(ROOT / 'runtime/far-heap.s', directory)])
    raw, command = manual('manual-heap', 'lorom32', [heap, heap_lib, *libs, ROOT / 'build/libc.a'])
    c.run(command)
    report[raw.stem] = target(raw)


def clock_callbacks(sy, points):
    callbacks = ['local hits={}']
    for name in points:
        address = checkpoint_address(sy, name)
        callbacks.append(f'''
emu.addMemoryCallback(function()
 if not hits['{name}'] then
  hits['{name}']=true
  print('CLOCK {name}',emu.getState().masterClock)
 end
end,emu.callbackType.exec,{address},{address})
''')
    return '\n'.join(callbacks)


def console_clocks(raw, rom, sy):
    points = ('reset_entry', 'ram_cleared', 'main', '_vector_nmi')
    address = sy['console_flush_done']
    script = clock_callbacks(sy, points) + f'''
local flush=0
emu.addMemoryCallback(function()
 flush=flush+1
 print('CLOCK flush_'..flush,emu.getState().masterClock)
 if flush==2 then emu.stop(0) end
end,emu.callbackType.exec,{address},{address})
'''
    runs = []
    for repeat in range(2):
        stem = OUT / f'{raw.stem}-run{repeat+1}'
        lua = stem.with_suffix('.lua')
        lua.write_text(script + f'\n-- {stem.name}\n')
        result = c.run([c.mesen_executable(), '--testRunner', '--doNotSaveSettings',
                        '--timeout=25', rom, lua], cwd=OUT, timeout=35).stdout
        clocks = dict(re.findall(r'CLOCK (\w+)\s+(\d+)', result))
        assert clocks.keys() == {*points, 'flush_1', 'flush_2'}, result
        runs.append(clocks)
    return runs


def compatibility_checks(baseline):
    console = source('compat-console', """#include <stdio.h>
int main(void) {
    printf("%.1f\\n", 1.5);
    fflush(stdout);
    printf("%.1f\\n", 2.5);
    fflush(stdout);
    return 0;
}
""")
    pairs = {}
    for case, sources, extra in (
        ('minimal', ['samples/minimal.c'], []),
        ('prompt', ['samples/prompt.c'], ['--console']),
        ('console', [console], ['--console', '--input', ROOT / 'samples/input.txt']),
        ('legacy-separate', LEGACY, []),
        ('legacy-lto', LEGACY, ['--lto']),
        ('legacy-binary64', LEGACY, ['--binary64']),
    ):
        pairs[case] = [build(f'{case}-{version}', sources, *extra, checkout=checkout)
                       for version, checkout in (('base', baseline), ('current', ROOT))]
    compiled = []
    for checkout in (baseline, ROOT):
        directory = OUT / ('compat-objects-' + checkout.name)
        directory.mkdir(exist_ok=True)
        compiled.append([compile_object(path, directory, checkout) for path in LEGACY])
    for old, new in zip(*compiled):
        instructions = lambda asm: re.findall(r'^    [a-z]{3}(?: .*)?$', asm.read_text(), re.M)
        assert instructions(old.with_suffix('.s')) == instructions(new.with_suffix('.s')), new
    for mapping in ('lorom32', 'hirom64'):
        pairs['legacy-' + mapping] = []
        for checkout, objects, version in zip((baseline, ROOT), compiled, ('base', 'current')):
            raw, command = manual(f'legacy-{mapping}-{version}', mapping,
                                  [*objects, ROOT / 'build/dp-scratch.o', ROOT / 'build/integers.o',
                                   ROOT / 'build/arithmetic.o', ROOT / 'build/libc.a'],
                                  checkout=checkout)
            c.run(command)
            pairs['legacy-' + mapping].append(raw)
    report = {}
    checkpoints = ('reset_entry', 'ram_cleared', 'main', 'legacy_sum', '_vector_nmi', 'main_exit')
    for case, (old, new) in pairs.items():
        sy_old, sy_new = labels(old), labels(new)
        assert old.read_bytes() == new.read_bytes(), f'{case}: raw ROM changed'
        for label in set(sy_old) & set(sy_new):
            assert sy_old[label] == sy_new[label], (case, label, sy_old[label], sy_new[label])
        runs = []
        images = []
        for raw in (old, new):
            rom = raw.with_suffix('.sfc')
            c.run([ROOT / 'build/romtool.exe', raw, rom, ROOT / 'tests/title.txt'])
            images.append(rom.read_bytes())
            sy = labels(raw)
            disassemble(raw, 'reset', sy['reset_entry'], sy['reset_native'] - sy['reset_entry'], 'MX')
            if case == 'console':
                runs.extend(console_clocks(raw, rom, sy))
            if not case.startswith('legacy-'):
                continue
            callbacks = clock_callbacks(sy, checkpoints)
            for repeat in range(2):
                extra = callbacks + f'\n-- {raw.stem} repetition {repeat}\n'
                result = c.emulate(rom, sy, 0, seed=True, extra_checks=extra, timeout_seconds=25)
                clocks = dict(re.findall(r'CLOCK (\w+)\s+(\d+)', result))
                assert clocks.keys() == set(checkpoints), (case, result)
                runs.append(clocks)
        assert images[0] == images[1], f'{case}: final ROM changed'
        if runs:
            assert all(clocks == runs[0] for clocks in runs), (case, runs)
        report[case] = dict(raw_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
                            rom_sha256=hashlib.sha256(images[1]).hexdigest(), runs=runs)
    (OUT / 'compatibility.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS {len(pairs)} byte-identical ROM pairs and {sum(len(r["runs"]) for r in report.values())} matched Mesen runs')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, help='checkout with the pre-WRAM compiler built')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    c.OUT = OUT
    if args.baseline:
        compatibility_checks(args.baseline.resolve())
        return
    directory = OUT / 'objects'
    directory.mkdir(exist_ok=True)
    allocation_checks()
    frontend_checks(directory)
    report = {}
    codegen_checks(report)
    target_checks(report, directory)
    manual_checks(report, directory)
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'PASS expanded WRAM in {len(report)} Mesen runs')


if __name__ == '__main__':
    main()
