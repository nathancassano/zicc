"""Verify cartridge SRAM configuration, access, placement, and persistence."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CC65 = Path(os.environ.get('CC65_BIN', 'C:/bin/cc65/bin'))
BUILDER = ROOT / 'tools/build-rom.py'
MANUAL = ROOT / 'tools/link-runtime-ram.py'
ZICC = ROOT / 'build/zicc.exe'
ROMTOOL = ROOT / 'build/romtool.exe'


def run(arguments, error=None):
    result = subprocess.run([str(x) for x in arguments], cwd=ROOT, text=True,
                            capture_output=True, timeout=120)
    if error is None:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode and error in result.stderr, result.stdout + result.stderr
    return result.stdout


def source(directory, name, code):
    path = directory / (name + '.c')
    path.write_text(code)
    return path


def automatic(directory, name, code, *flags, sources=()):
    raw = directory / (name + '.raw')
    run([sys.executable, BUILDER, source(directory, name, code), *sources, '-o', raw, *flags])
    return raw


def assemble(directory, path):
    obj = directory / (path.stem + '.o')
    run([CC65/'ca65.exe', '--cpu', '65816', '-g', '-I', ROOT, '-o', obj, path])
    return obj


def manual(directory, name, code, kib, cfg):
    raw = directory / (name + '.raw')
    asm = source(directory, name, code).with_suffix('.s')
    options = ['--sram-layout', f'112,32768,{kib * 1024}'] if kib else []
    run([ZICC, asm.with_suffix('.c'), '-o', asm, '-I', ROOT/'include', *options])
    units = [assemble(directory, asm)]
    units.extend(assemble(directory, ROOT/'runtime'/file)
                 for file in ('startup.s', 'rom_header.s', 'vectors.s', 'dp-scratch.s'))
    library = directory/'manual-sram.a'
    if not library.exists():
        run([CC65/'ar65.exe', 'r', library, assemble(directory, ROOT/'runtime/sram.s')])
    units.append(library)
    command = [sys.executable, MANUAL, '--sram-size', kib, '-o', raw, '-Ln',
               raw.with_suffix('.labels'), *units, '-C', ROOT/'linker'/f'{cfg}.cfg']
    run(command)
    return raw, command


def finish(raw, header, size, map_mode, kib):
    rom = raw.with_suffix('.sfc')
    run([ROMTOOL, raw, rom, ROOT/'tests/title.txt'])
    linked, image = raw.read_bytes(), rom.read_bytes()
    fields = (map_mode, 2 if kib else 0, kib.bit_length() - 1 if kib else 0)
    assert tuple(linked[header + i] for i in (21, 22, 24)) == fields
    assert tuple(image[header + i] for i in (21, 22, 24)) == fields
    assert len(image) == size
    assert image[header + 32:header + 64] == linked[header + 32:header + 64]
    assert all(image[header + i] >= 0x80 for i in range(33, 64, 2))
    complement = int.from_bytes(image[header + 28:header + 30], 'little')
    checksum = int.from_bytes(image[header + 30:header + 32], 'little')
    assert complement ^ checksum == 0xFFFF
    assert (sum(image) + (sum(image[0x400000:]) if size == 6 * 1024 * 1024 else 0)) & 0xFFFF == checksum
    return rom


def emulate(emulator, rom, expected, addresses, *, reset=False, strict=False):
    labels = dict((name, int(address, 16)) for address, name in
                  re.findall(r'^al (\w+) \.(\w+)$', rom.with_suffix('.labels').read_text(), re.M))
    strict_check = '''
 local mapped=emu.convertAddress(0x806000)
 assert(mapped and mapped.memType==emu.memType.snesSaveRam and mapped.address==0,
        'expected ExHiROM SRAM at $80:6000')
 local alias=emu.convertAddress(0x206000)
 assert(not alias or alias.memType~=emu.memType.snesSaveRam, 'ExHiROM compatibility alias is enabled')
''' if strict else ''
    bus_checks = '\n'.join(f' assert(emu.read({address},emu.memType.snesMemory)=={expected[offset]},'
                           f'"CPU address {address:06X}")' for address, offset in addresses.items())
    lua = rom.with_suffix('.lua')
    lua.write_text(f'''
local visits,done,result=0,false,nil
emu.addMemoryCallback(function()
 if result~=nil or done then return end
 result=emu.getState()['cpu.a']
 assert(emu.getState()['cpu.sp']=={labels['__STACK_TOP__']}, 'stack balance')
{strict_check}{bus_checks}
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
emu.addEventCallback(function()
 if result==nil or done then return end
 if result~=0 then print('FAIL return',result); done=true; emu.stop(1); return end
 visits=visits+1
 result=nil
 if visits=={2 if reset else 1} then
  done=true; print('PASS SRAM',visits); emu.stop(0)
 else
  emu.reset()
 end
end,emu.eventType.endFrame)
''')
    args = ['--snes.enableStrictBoardMappings=true'] if strict else []
    out = run([emulator, '--testRunner', '--doNotSaveSettings', '--timeout=12', *args, rom, lua])
    assert ('PASS SRAM\t2' if reset else 'PASS SRAM\t1') in out and 'FAIL' not in out, out


def api_source(capacity, boundary):
    return f'''
#include <sram.h>
#define CAPACITY {capacity}UL
#define BOUNDARY {boundary}UL
static unsigned char data[2] = {{0xB6,0xC7}};
static unsigned char result[2];
static volatile unsigned long beyond = 0xFFFFFFFFUL;
int main(void) {{
    if (sram_capacity() != CAPACITY || sram_read(CAPACITY, 0, 0) ||
        sram_write(CAPACITY, 0, 0)) return 1;
    if (!sram_read(beyond, result, 2) || !sram_write(beyond, data, 2) ||
        !sram_read(CAPACITY, result, 1) || !sram_write(CAPACITY, data, 1) ||
        !sram_read(0, 0, 1) || !sram_write(0, 0, 1)) return 2;
    if (result[0] || result[1]) return 3;
    if (CAPACITY == 0) return 0;
    if (!sram_write(CAPACITY-1, data, 2) || !sram_read(CAPACITY-1, result, 2) ||
        result[0] || result[1]) return 4;
    if (sram_read(0, result, 1)) return 5;
    if (result[0] == 0) {{
        if (sram_write(BOUNDARY-1, data, 2) || sram_write(CAPACITY-1, data+1, 1) ||
            sram_write(0, data, 1)) return 6;
    }} else if (result[0] != 0xB6) return 7;
    if (sram_read(BOUNDARY-1, result, 2) || result[0]!=0xB6 || result[1]!=0xC7 ||
        sram_read(CAPACITY-1, result, 1) || result[0]!=0xC7 ||
        sram_read(123, result, 1) || result[0]!=0x6C) return 8;
    return 0;
}}
'''


def check_api(directory, emulator):
    for name, kib, window, first, base, header, size, mode, flags in [
        ('none', 0, 0, 0xA0, 0x6000, 0xFFC0, 65536, 0x31, []),
        ('hirom', 32, 8192, 0xA0, 0x6000, 0xFFC0, 65536, 0x31, []),
        ('exhirom6', 32, 8192, 0x80, 0x6000, 0x40FFC0, 6*1048576, 0x35,
         ['--mapping', 'exhirom', '--rom-size', '6144', '--stage', '3']),
        ('exhirom8', 128, 8192, 0x80, 0x6000, 0x40FFC0, 8*1048576, 0x35,
         ['--mapping', 'exhirom', '--rom-size', '8192', '--stage', '4']),
        ('lorom-small', 2, 32768, 0x70, 0, 0x7FC0, 32768, 0x30, ['lorom32']),
        ('lorom', 64, 32768, 0x70, 0, 0x7FC0, 2*1048576, 0x30, ['lorom2048']),
    ]:
        capacity = kib * 1024
        boundary = window if capacity > window else 255
        code = api_source(capacity, boundary)
        if name.startswith('lorom'):
            raw, command = manual(directory, name, code, kib, flags[0])
            if name == 'lorom':
                bad = [ROOT/'linker/lorom32.cfg' if item == ROOT/'linker/lorom2048.cfg' else item
                       for item in command]
                bad[bad.index('-o')+1] = directory/'rejected.raw'
                run(bad, 'requires a ROM of at least 2 MiB')
                small_raw = directory/'rejected-size.raw'
                image = raw.read_bytes()[:32768]
                small_raw.write_bytes(image)
                run([ROMTOOL, small_raw, small_raw.with_suffix('.sfc'), ROOT/'tests/title.txt'],
                    'requires a ROM of at least 2 MiB')
        else:
            raw = automatic(directory, name, code, '--sram-size', kib, *flags)
        rom = finish(raw, header, size, mode, kib)
        save = emulator.parent/'Saves'/f'{name}.srm'
        if not kib:
            emulate(emulator, rom, {}, {})
            assert not save.exists()
            continue
        seed = bytearray(capacity)
        seed[123] = 0x6C
        save.write_bytes(seed)
        expected = bytearray(seed)
        expected[0] = expected[boundary-1] = 0xB6
        expected[boundary] = expected[-1] = 0xC7
        addresses = {((first + offset // window) << 16) + base + offset % window: offset
                     for offset in (0, 123, boundary-1, boundary, capacity-1)}
        strict = name.startswith('exhirom')
        emulate(emulator, rom, expected, addresses, reset=True, strict=strict)
        assert save.read_bytes() == expected, name
        emulate(emulator, rom, expected, addresses, strict=strict)
        assert save.read_bytes() == expected, name


ARRAY_DECL = 'typedef struct { unsigned char bytes[4096]; } record_t;\n'


def check_declarations(directory, emulator):
    code = ARRAY_DECL + '''
#include <sram.h>
__sram(0) record_t saves[8];
static record_t * __far record = &saves[5];
static volatile unsigned slot;
static unsigned char byte;
extern unsigned char last(record_t * __far p);
int main(void) {
    if (sizeof(saves) != 32768U || sizeof saves[slot] != 4096) return 1;
    for (slot=0; slot<8; ) {
        unsigned n=slot;
        if (saves[n].bytes[13]!=0xA5) return 2;
        saves[slot++].bytes[0]=(unsigned char)(n+11);
        saves[n].bytes[4095]=(unsigned char)(n+21);
        if (last(&saves[n])!=n+21 ||
            sram_read((unsigned long)n*4096UL, &byte, 1) || byte!=n+11) return 3;
    }
    *(volatile unsigned char * __far)0xA16000UL=41;
    if (saves[2].bytes[0]!=41 || record->bytes[0]!=16) return 4;
    byte=59;
    if (sram_write(28672UL, &byte, 1) || saves[7].bytes[0]!=59) return 5;
    return 0;
}
'''
    other = source(directory, 'array-extern', ARRAY_DECL + '''
extern __sram(0) record_t saves[8];
unsigned char last(record_t * __far p) {
    return p->bytes[4095] == saves[2].bytes[4095] && p == &saves[2]
           ? saves[2].bytes[4095] : p->bytes[4095];
}
''')
    raw = automatic(directory, 'array', code, '--sram-size', 32, sources=[other])
    rom = finish(raw, 0xFFC0, 65536, 0x31, 32)
    allocation = json.loads(raw.with_suffix('.allocation.json').read_text())
    obj, = allocation['sram']['objects']
    assert obj['name'] == 'saves' and obj['offset'] == 0 and obj['size'] == 32768
    assert [part['address'] for part in obj['parts']] == [0xA06000 + i*65536 for i in range(4)]
    assert all(not entry['name'].startswith('ZSRAM_') for entry in allocation['units'])
    save = emulator.parent/'Saves'/'array.srm'
    expected = bytearray([0xA5])*32768
    save.write_bytes(expected)
    for i in range(8):
        expected[i*4096] = i+11
        expected[i*4096+4095] = i+21
    expected[8192], expected[28672] = 41, 59
    emulate(emulator, rom, expected, {0xA16000: 8192, 0xA37000:28672})
    assert save.read_bytes() == expected

    raw = automatic(directory, 'partial', ARRAY_DECL + '''
__sram(1) record_t records[3];
__sram(2) unsigned char tail[4092];
__sram(2) unsigned long counter;
int main(void) {
    records[2].bytes[0]=61;
    tail[0]=62;
    counter=0x67452301UL;
    return records[2].bytes[0]!=61 || tail[0]!=62 || counter!=0x67452301UL;
}
''', '--sram-size', 32)
    layout = json.loads(raw.with_suffix('.allocation.json').read_text())['sram']['objects']
    assert [(obj['offset'], obj['size']) for obj in layout] == [(8192, 12288), (20480, 4092), (24572, 4)]
    rom = finish(raw, 0xFFC0, 65536, 0x31, 32)
    emulate(emulator, rom, {16384:61, 20480:62, 24572:1, 24575:0x67},
            {0xA26000:16384, 0xA27000:20480, 0xA27FFC:24572, 0xA27FFF:24575})

    raw = automatic(directory, 'direct', '''
int main(void) {
    *(volatile unsigned char * __far)0xA06000UL=72;
    return 0;
}
''', '--sram-size', 2)
    rom = finish(raw, 0xFFC0, 65536, 0x31, 2)
    save = emulator.parent/'Saves'/'direct.srm'
    save.write_bytes(bytes(2048))
    emulate(emulator, rom, {0:72}, {0xA06000:0, 0xA06800:0})
    assert save.read_bytes() == bytes([72])+bytes(2047)

    for kib in (2, 8):
        name = f'one-window-{kib}'
        code = f'''
__sram(1-1) unsigned char bytes[{kib * 1024}];
int main(void) {{
    unsigned char * __far last=bytes+sizeof bytes-1;
    *last=73;
    return bytes[sizeof bytes-1]!=73;
}}
'''
        if kib == 2:
            raw, _ = manual(directory, name, code, kib, 'lorom32')
            rom = finish(raw, 0x7FC0, 32768, 0x30, kib)
            first = 0x700000
        else:
            raw = automatic(directory, name, code, '--sram-size', kib)
            rom = finish(raw, 0xFFC0, 65536, 0x31, kib)
            first = 0xA06000
        obj, = json.loads(raw.with_suffix('.allocation.json').read_text())['sram']['objects']
        assert (obj['address'], obj['offset'], obj['size']) == (first, 0, kib * 1024)
        end = first + kib * 1024 - 1
        emulate(emulator, rom, {0:73}, {end:0})


def check_diagnostics(directory):
    for declaration, message, capacity in [
        ('__sram(0) char x;', 'requires a build', 0),
        ('__sram(1) char x;', 'outside installed', 2048),
        ('__sram(-1) char x;', 'outside installed', 32768),
        ('__sram(0) char x=0;', 'explicit initializer', 32768),
        ('__sram(0) char x[2]={0};', 'explicit initializer', 32768),
        ('__sram(0) const int x;', 'complete writable type', 32768),
        ('__sram(0) extern char x[];', 'complete writable type', 32768),
        ('__sram(0) __hiram char x;', 'conflicting SRAM placement', 32768),
        ('__sram(0) struct X { char b[8193]; } x;', 'does not fit', 32768),
        ('__sram(0) char x[3000][3];', 'split an element', 32768),
        ('void f(void) { static __sram(0) int x; }', 'require file scope', 32768),
        *[(ARRAY_DECL + '__sram(0) record_t x[8]; void f(void) {' + stmt + ';}',
           'requires direct indexing', 32768)
          for stmt in ('x+1', '&x', '(char * __far)x', 'void g(record_t * __far); g(x)')],
    ]:
        path = source(directory, 'invalid', declaration)
        flags = ['--sram-layout', f'160,8192,{capacity}'] if capacity else []
        run([ZICC, path, '-o', path.with_suffix('.s'), *flags], message)

    def reject_link(code, message, *extra):
        path = source(directory, 'bad-link', code)
        run([sys.executable, BUILDER, path, *extra, '-o', path.with_suffix('.raw'),
             '--sram-size', 32], message)

    reject_link('__sram(0) char a[8192], b[1]; int main(void){return 0;}', 'overflows window')
    reject_link('__sram(0) char a[16384]; __sram(1) char b[16384]; int main(void){return 0;}',
                'overlaps another array')
    definition = source(directory, 'definition', ARRAY_DECL + '__sram(0) record_t a[6];')
    for decl, message in [('extern __sram(0) record_t a[5];', 'conflicting SRAM declaration'),
                          ('extern __sram(1) record_t a[6];', 'conflicting SRAM declaration'),
                          ('extern record_t a[6];', 'missing __sram')]:
        reject_link(ARRAY_DECL + decl + 'int main(void){return a[1].bytes[0];}', message, definition)
    reject_link(ARRAY_DECL + 'extern __sram(0) record_t a[5]; int main(void){return sizeof a;}',
                'conflicting SRAM declaration', definition)
    wrong_layout = definition.with_suffix('.s')
    run([ZICC, definition, '-o', wrong_layout, '--sram-layout', '128,8192,32768'])
    reject_link('int main(void){return 0;}', 'compiled with a different cartridge layout',
                '--assembly', wrong_layout)

    small = source(directory, 'invalid-size', 'int main(void){return 0;}')
    for kib in (1, 6, 512):
        run([sys.executable, BUILDER, small, '-o', small.with_suffix('.raw'),
             '--sram-size', kib], 'must be 0 or a power of two')


def check_exhirom_maximum(directory):
    # Mesen clamps generic cartridge SRAM at 256 KiB. Check the full
    # address profile and its header on the host
    raw = automatic(directory, 'exhirom-max', '''
#include <sram.h>
__sram(63) unsigned char last_window[8192];
int main(void) {
    last_window[8191]=88;
    return sram_capacity()!=524288UL;
}
''', '--mapping', 'exhirom', '--rom-size', 6144, '--sram-size', 512)
    rom = finish(raw, 0x40FFC0, 6*1048576, 0x35, 512)
    obj, = json.loads(raw.with_suffix('.allocation.json').read_text())['sram']['objects']
    assert (obj['address'], obj['offset'], obj['size']) == (0xBF6000, 63*8192, 8192)
    assert 'al 080000 .__sram_capacity' in raw.with_suffix('.labels').read_text()
    bad = bytearray(rom.read_bytes())
    bad[0x40FFD8] = 10
    invalid = directory/'invalid-header.raw'
    invalid.write_bytes(bad)
    run([ROMTOOL, invalid, invalid.with_suffix('.sfc'), ROOT/'tests/title.txt'],
        'unsupported cartridge type')


def main():
    output = Path(os.environ.get('ZICC_LOGS_DIR', ROOT/'logs')).resolve()
    output.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(prefix='sram-check-', dir=output) as stem:
        directory = Path(stem)
        emulator = directory/'mesen'/'Mesen.exe'
        (emulator.parent/'Saves').mkdir(parents=True)
        shutil.copyfile('C:/bin/Mesen/Mesen.exe', emulator)
        (emulator.parent/'settings.json').write_text('{}')
        check_api(directory, emulator)
        check_declarations(directory, emulator)
        check_diagnostics(directory)
        check_exhirom_maximum(directory)
    print('PASS cartridge SRAM on LoROM, HiROM, and ExHiROM')


if __name__ == '__main__':
    main()
