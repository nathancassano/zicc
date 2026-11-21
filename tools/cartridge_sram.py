"""Shared cartridge SRAM configuration for automatic and manual ROM links."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Profile:
    first_bank: int
    last_bank: int
    base: int
    window_size: int
    header_offset: int
    map_mode: int

    @property
    def maximum_kib(self):
        mapped_kib = (self.last_bank - self.first_bank + 1) * self.window_size // 1024
        return 1 << (mapped_kib.bit_length() - 1)


PROFILES = {
    'lorom': Profile(0x70, 0x7D, 0, 32768, 0x7FC0, 0x30),
    'hirom': Profile(0xA0, 0xBF, 0x6000, 8192, 0xFFC0, 0x31),
    'exhirom': Profile(0x80, 0xBF, 0x6000, 8192, 0x40FFC0, 0x35),
}
LINK_SYMBOLS = {'__sram_capacity', '__sram_window_size', '__sram_window_shift',
                '__sram_base', '__sram_first_bank'}
PART = re.compile(r'ZSRAM_(\d+)_(\d+)_(\d+)_(\d+)_(\d+)_(\w+)')


@dataclass(frozen=True)
class CartridgeSram:
    mapping: str
    kib: int

    def __post_init__(self):
        if self.kib != 0 and (self.kib < 2 or self.kib & (self.kib - 1)
                              or self.kib > self.profile.maximum_kib):
            raise ValueError(f'--sram-size for {self.mapping} must be 0 or a power '
                             f'of two from 2 through {self.profile.maximum_kib} KiB')

    @property
    def profile(self):
        return PROFILES[self.mapping]

    @property
    def capacity(self):
        return self.kib * 1024

    def check_rom_size(self, size):
        if self.mapping == 'lorom' and self.capacity > self.profile.window_size and size < 2 * 1024 * 1024:
            raise ValueError('LoROM SRAM above 32 KiB requires a ROM of at least 2 MiB '
                             '(use linker/lorom2048.cfg or linker/lorom4096.cfg)')

    def manifest(self):
        return dict(profile=self.mapping, capacity=self.capacity,
                    first_bank=self.profile.first_bank, base=self.profile.base,
                    window_size=self.profile.window_size)

    def header_bytes(self):
        return (2, self.kib.bit_length() - 1) if self.kib else (0, 0)

    def check_manual_header(self, path):
        self.check_rom_size(path.stat().st_size)
        with path.open('r+b' if self.capacity else 'rb') as rom:
            rom.seek(self.profile.header_offset + 21)
            header = rom.read(4)
            if len(header) != 4 or header[0] not in (0, self.profile.map_mode):
                raise ValueError(f'manual link header conflicts with the {self.mapping} SRAM profile')
            cart_type, exponent = self.header_bytes()
            if (header[1], header[3]) not in ((0, 0), (cart_type, exponent)):
                raise ValueError('linked cartridge header conflicts with --sram-size')
            if self.capacity:
                rom.seek(self.profile.header_offset + 21)
                rom.write(bytes((self.profile.map_mode, cart_type, header[2], exponent)))

    def linker_symbols(self):
        values = (('__sram_capacity', self.capacity, 'far'),
                  ('__sram_window_size', self.profile.window_size, 'absolute'),
                  ('__sram_window_shift', self.profile.window_size.bit_length() - 1, 'absolute'),
                  ('__sram_base', self.profile.base, 'absolute'),
                  ('__sram_first_bank', self.profile.first_bank, 'absolute'))
        return [f' {name}: type=export, value=${value:X}, addrsize={address_size};'
                for name, value, address_size in values]

    def compiler_flags(self):
        if not self.capacity:
            return []
        return ['--sram-layout', f'{self.profile.first_bank},{self.profile.window_size},{self.capacity}']

    def windows(self):
        for index, offset in enumerate(range(0, self.capacity, self.profile.window_size)):
            address = ((self.profile.first_bank + index) << 16) + self.profile.base
            yield address, min(self.profile.window_size, self.capacity - offset)

    def allocate(self, segments, unqualified=()):
        windows = list(self.windows())
        objects = {}
        for segment, size, alignment in segments:
            match = PART.fullmatch(segment)
            first, window, capacity, start, part = map(int, match.groups()[:5])
            name = match[6]
            if (first, window, capacity) != (self.profile.first_bank, self.profile.window_size, self.capacity):
                raise ValueError(f"SRAM object '{name}' was compiled with a different cartridge layout")
            obj = objects.setdefault(name, dict(name=name, window=start, parts={}))
            if obj['window'] != start or part in obj['parts']:
                raise ValueError(f"conflicting SRAM sections for '{name}'")
            obj['parts'][part] = dict(segment=segment, size=size, alignment=alignment)
        conflicts = objects.keys() & set(unqualified)
        if conflicts:
            raise ValueError(f"conflicting SRAM placement for '{min(conflicts)}': missing __sram on a reference")

        used = [0] * len(windows)
        result = []
        # A spanning array starts at offset zero of its first window. Allocate
        # those fixed ranges before fitting ordinary objects into spare space
        for obj in sorted(objects.values(), key=lambda item: len(item['parts']) == 1):
            parts = obj['parts']
            spanning = len(parts) > 1
            placed = []
            for part, block in sorted(parts.items()):
                index = obj['window'] + part
                if index >= len(windows) or part != len(placed):
                    raise ValueError(f"invalid SRAM window {index} for '{obj['name']}'")
                address, usable = windows[index]
                alignment = block['alignment']
                if spanning and used[index]:
                    raise ValueError(f"SRAM array '{obj['name']}' overlaps another array in window {index}")
                offset = (used[index] + alignment - 1) & -alignment
                end = offset + block['size']
                if end > usable:
                    raise ValueError(f"SRAM object '{obj['name']}' overflows window {index} ({usable} usable bytes)")
                used[index] = end
                placed.append(dict(block, window=index, address=address + offset,
                                   offset=index * self.profile.window_size + offset))
            result.append(dict(name=obj['name'], window=obj['window'], parts=placed,
                               size=sum(block['size'] for block in placed),
                               address=placed[0]['address'], offset=placed[0]['offset']))
        return result

    def linker_regions(self, objects):
        memory = [f' CART_SRAM_{i}: start=${address:06X}, size=${usable:X}, type=rw, file="";'
                  for i, (address, usable) in enumerate(self.windows())]
        blocks = sorted((block for obj in objects for block in obj['parts']), key=lambda block: block['address'])
        segments = [f' {block["segment"]}: load=CART_SRAM_{block["window"]}, '
                    f'type=bss, start=${block["address"]:06X};' for block in blocks]
        return memory, segments


def verify(objects, linked):
    for obj in objects:
        for block in obj['parts']:
            if linked.get(block['segment']) != (block['address'], block['size']):
                raise RuntimeError(f"final SRAM placement differs for '{obj['name']}'")
