"""Check where near data fits in memory and run its startup code in Mesen."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from mesen_core import Core

spec = importlib.util.spec_from_file_location('build_rom', ROOT / 'tools/build-rom.py')
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


def labels(path):
    return {name: int(address, 16) for address, name in
            re.findall(r'^al (\w+) \.(\S+)$', path.read_text(), re.M)}


def record(rom, output, label_file=None):
    symbols = labels(label_file or rom.with_suffix('.labels'))
    expected = {}
    image = rom.read_bytes()
    for key, count in sorted(symbols.items()):
        if not key.startswith(('__NEAR_DATA_', '__NEAR_BSS_')) or not key.endswith('_SIZE__'):
            continue
        name = key.removesuffix('_SIZE__')
        run = symbols[name + '_RUN__'] - 0x7e0000
        load = symbols.get(name + '_LOAD__', 0) - 0xc00000
        data = image[load:load + count] if name.startswith('__NEAR_DATA_') else bytes(count)
        assert len(data) == count
        expected[name] = (run, data.hex())
    seed, checks = [], []
    for run, data in expected.values():
        seed.append(f'visit({run},"{data}",function(i,v) poke(i,v ~ 255) end)')
        checks.append(f'visit({run},"{data}",check)')
    for name in ('LORAM_BSS', 'BSS'):
        size = symbols.get(f'__{name}_SIZE__', 0)
        if size:
            run = symbols[f'__{name}_RUN__'] - 0x7e0000
            seed.append(f'for i={run},{run+size-1} do poke(i,165) end')
            checks.append(f'for i={run},{run+size-1} do check(i,0) end')
    if 'fixture_done' in symbols:
        # Two alignment bytes. The first is carried by the short direct
        # copy and the second by the longer DMA. The end canary is outside
        # both spans, while bank $7F verifies a DMA count encoded as zero
        seed.extend(f'poke({i},165)' for i in (0x201, 0x207, 0x21b, 0x10000, 0x1ffff))
        checks.extend((f'check({i},{value})' for i, value in (
            (0x201, 0), (0x207, 0), (0x21b, 165), (0x10000, 18),
            (0x12345, 126), (0x1ffff, 52))))
        checks.append('for i=0x10001,0x1fffe do check(i,126) end')
    near_done = symbols.get('ram_cleared', symbols['data_copied'])
    script = '''
local wram=emu.memType.snesWorkRam
local function poke(at,v) emu.write(at,v,wram) end
local function check(at,v)
  local actual=emu.read(at,wram,false)
  if actual~=v then error(string.format('WRAM $%05X: expected %02X got %02X',at,v,actual)) end
end
local function visit(at,hex,fn)
  for i=1,#hex,2 do fn(at+(i-1)//2,tonumber(hex:sub(i,i+1),16)) end
end
local start, reset, near_clocks
''' + f'''
emu.addMemoryCallback(function()
  reset=emu.getState().masterClock
  {chr(10).join(seed)}
end,emu.callbackType.exec,{symbols['reset_entry']},{symbols['reset_entry']})
emu.addMemoryCallback(function()
  start=emu.getState().masterClock
end,emu.callbackType.exec,{symbols['__initialize_extra_ram']},{symbols['__initialize_extra_ram']})
emu.addMemoryCallback(function()
  near_clocks=emu.getState().masterClock-start
end,emu.callbackType.exec,{near_done},{near_done})
emu.addMemoryCallback(function()
  local now=emu.getState().masterClock
  {chr(10).join(checks)}
  emu.log('NEAR_OK '..near_clocks..' '..(now-reset))
  emu.breakExecution()
end,emu.callbackType.exec,{symbols['data_copied']},{symbols['data_copied']})
'''
    output.mkdir(parents=True, exist_ok=True)
    lua = output / 'near.lua'
    lua.write_text(script)
    core = Core(output / 'mesen')
    try:
        core.load(rom, lua, script)
        core.start()
        log = core.wait_for('NEAR_OK', 15)
    finally:
        core.close_with_log(output / 'mesen.log')
    near_clocks, reset_clocks = map(int, re.search(r'NEAR_OK (\d+) (\d+)', log).groups())
    (output / 'result.json').write_text(json.dumps(dict(
        near_clocks=near_clocks, reset_clocks=reset_clocks, objects=expected), indent=2) + '\n')


def verify_fallback(output):
    output.mkdir(exist_ok=True)
    # The interrupt group spills both 4 KiB arrays into ordinary WRAM
    # Two large code units leave separate ROM bank tails. The combined
    # data cannot fit either tail, but each individual object fits
    source = output / 'init.c'
    source.write_text('''
volatile unsigned char left[4096] = {0x12};
volatile unsigned char right[4096] = {0x34};
__interrupt(nmi) void vblank(void) { if (left[0] != right[0]) left[1] = 3; }
int main(void) { return !(left[0] == 0x12 && right[0] == 0x34); }
''')
    flags = []
    for name in ('pad_a.s', 'pad_b.s'):
        pad = output / name
        pad.write_text('.segment "CODE"\n.res 60000, $ea\n')
        flags.extend(('--assembly', pad))
    raw = output / 'init.raw'
    log = builder.BuildTranscript(output)
    builder.run([sys.executable, '-B', ROOT / 'tools/build-rom.py', source, *flags,
                 '--stage', 4, '--stack-size', 256, '--max-rom', 131072,
                 '-o', raw], log)
    manifest = json.loads(raw.with_suffix('.allocation.json').read_text())
    assert manifest['capacity'] == 131072
    assert any(row['capacity'] == 131072 and row['grouped_data'] and 'BATCH_' in row['error']
               for row in manifest['history'])
    units = [u for u in manifest['units'] if u['name'].startswith('NEAR_DATA_')]
    assert len(units) == 2 and len({u['address'] >> 16 for u in units}) == 2
    assert all((u['address'] & 65535) + u['size'] <= 65536 for u in units)
    asm = Path(manifest['evidence']) / 'stage4/ram-init-unbatched.s'
    assert asm.read_text().count('    boot_dma_known ') == 2
    rom = raw.with_suffix('.sfc')
    title = output / 'title.txt'
    title.write_text('NEAR FALLBACK\n')
    builder.run([ROOT / 'build/romtool.exe', raw, rom, title])
    # MesenCore supports one initialization per process
    builder.run([sys.executable, '-B', Path(__file__), output / 'verify',
                 '--rom', rom, '--labels', raw.with_suffix('.labels')], log)


def fixture(output):
    log = builder.BuildTranscript(output)
    specs = [
        ('NEAR_DATA_BYTE', 1, b'\x92'),
        ('NEAR_DATA_WORD', 2, b'\x31\x80'),
        ('NEAR_BSS_SEP', 1, bytes(2)),
        ('NEAR_DATA_HEAD', 1, b'\x51'),
        ('NEAR_DATA_ALIGNED', 2, bytes(range(16, 32))),
        ('NEAR_BSS_TAIL_WORD', 2, bytes(2)),
        ('NEAR_BSS_TAIL_BYTE', 1, bytes(1)),
    ]
    objects = [(name, alignment) for name, alignment, _ in specs]
    sizes = {name: len(data) for name, _, data in specs}
    spans = builder.near_layout(objects, (), sizes, 0x7e0200)
    runs = builder.initializer_runs(spans, True)
    batches = [run for run in runs if not run[0].clear]
    assert [builder.run_size(run) for run in batches] == [4, 18]
    assert [builder.run_cost(run)[0] for run in batches] == [True, False]
    assert len(runs[-1]) == 2 and builder.run_size(runs[-1]) == 3
    initializer = builder.assemble_ram_initializer(output, runs, [], log)
    source = output / 'fixture.s'
    obj = source.with_suffix('.o')
    text = '''
.setcpu "65816"
.include "runtime/startup-dma.inc"
.import __initialize_extra_ram
.export reset_entry, data_copied, fixture_done, startup_zero
.segment "FIXTURE"
.a8
.i8
reset_entry:
    sei
    clc
    xce
    rep #$30
    .a16
    .i16
    ldx #$01ff
    txs
    boot_dma_known $C10000, $7F0000, $10000, $00
    jsl __initialize_extra_ram
data_copied:
fixture_done:
    bra fixture_done
startup_zero:
    .byte 0
.segment "FULL"
    .byte $12
    .res $fffe, $7e
    .byte $34
'''
    for name, _, data in specs:
        text += f'.segment "{name}"\n'
        text += (f'.res {len(data)}\n' if name.startswith('NEAR_BSS_') else
                 '.byte ' + ','.join(map(str, data)) + '\n')
    builder.save(source, text)
    ca65, ld65 = (builder.CC65 / f'{name}.exe' for name in ('ca65', 'ld65'))
    objects_to_link = [initializer]
    for asm, target in ((source, obj), (ROOT / 'runtime/vectors.s', output / 'vectors.o'),
                        (ROOT / 'runtime/rom_header.s', output / 'header.o')):
        builder.run([ca65, '-D', 'HIROM=1', '-I', ROOT, '-o', target, asm])
        objects_to_link.append(target)
    measured, _, _ = builder.inspect(obj, log)
    init_sizes, _, _ = builder.inspect(initializer, log)
    align = dict(objects)
    units = [builder.Unit(name, size, align.get(name, alignment),
                          'code' if name in {'FIXTURE', 'C_NEAR_INIT'} else 'data', 'application')
             for name, size, alignment in measured + init_sizes if size and not name.startswith('NEAR_BSS_')]
    placements, _ = builder.pack(units, 2, 1, batches)
    assert placements['FULL'] == (1, 0)
    cfg = output / 'fixture.cfg'
    builder.save(cfg, builder.config(units, placements, 2, [], near_objects=objects,
                                     stack_size=256, batches=batches))
    raw = output / 'fixture.raw'
    rom = output / 'fixture.sfc'
    builder.run([ld65, '-C', cfg, '-Ln', rom.with_suffix('.labels'), '-o', raw, *objects_to_link])
    bad_source = output / 'cross-bank.s'
    bad_object = bad_source.with_suffix('.o')
    builder.save(bad_source, text.replace('$C10000', '$C10001'))
    builder.run([ca65, '-I', ROOT, '-o', bad_object, bad_source])
    try:
        builder.run([ld65, '-C', cfg, '-o', output / 'cross-bank.raw',
                     initializer, bad_object, *objects_to_link[2:]], log)
    except RuntimeError as error:
        assert 'startup DMA source crosses a bank' in str(error)
    else:
        raise AssertionError('linker accepted a DMA across a source bank')
    title = output / 'title.txt'
    title.write_text('NEAR STARTUP\n')
    builder.run([ROOT / 'build/romtool.exe', raw, rom, title])
    return rom


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--rom', type=Path)
    parser.add_argument('--labels', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.rom:
        record(args.rom.resolve(), output, args.labels)
    else:
        verify_fallback(output / 'fallback')
        record(fixture(output), output)
        print('Near startup packing and WRAM initialization passed')


if __name__ == '__main__':
    main()
