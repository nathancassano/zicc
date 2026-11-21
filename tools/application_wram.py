"""Choose an address in working RAM for each application object when linking the program."""
from dataclasses import dataclass
import re

from runtime_ram import LOW as BOUNDARY


PART = re.compile(r'ZWRAM_([BD])_([HX])_(\d+)_(\w+)')
UNQUALIFIED = 'ZICC_WRAM_UNQUAL_'
TAIL = 'ZWRAM_NEAR_TAIL'
HEAP_EXPORTS = {'_malloc', '_calloc', '_realloc', '_free'}


@dataclass(frozen=True)
class Part:
    name: str
    size: int
    alignment: int
    clear: bool


@dataclass(frozen=True)
class Object:
    name: str
    crossing: bool
    parts: tuple

    @property
    def size(self):
        return sum(part.size for part in self.parts)

    @property
    def alignment(self):
        return self.parts[0].alignment


def objects(records):
    groups = {}
    for name, size, alignment in records:
        match = PART.fullmatch(name)
        if not match or not size:
            continue
        storage, kind, index, symbol = match.groups()
        group = groups.setdefault((symbol, kind, storage), {})
        if int(index) in group:
            raise ValueError(f'duplicate expanded WRAM segment for {symbol}')
        group[int(index)] = Part(name, size, alignment, storage == 'B')
    result = []
    names = set()
    for (symbol, kind, storage), parts in groups.items():
        if (symbol in names or set(parts) != set(range(len(parts)))
                or any(p.alignment != 1 for i, p in parts.items() if i)):
            raise ValueError(f'invalid expanded WRAM segments for {symbol}')
        names.add(symbol)
        result.append(Object(symbol, kind == 'X', tuple(parts[i] for i in range(len(parts)))))
    return result


def align_up(address, alignment):
    return (address + alignment - 1) & -alignment


def near_exhaustion(detail):
    return (f'16-bit WRAM in bank $7E is full. {detail}\n'
            'If a buffer can use far pointers, move it to __hiram or __xbankram.')


def assignments(items, near, far, prefer_far, bridge=None):
    """Search both assignments, keeping alignment-sensitive frontier states."""
    order = sorted(items, key=lambda o: (-o.alignment, -o.size, o.name))
    remaining = [bridge.size if bridge else 0]
    for obj in reversed(order):
        remaining.append(remaining[-1] + obj.size)
    remaining.reverse()

    # linked choice nodes preserve the preferred path without copying it at
    # each step. The explicit stack accommodates large numbers of objects
    stack = [(0, near, far if bridge else BOUNDARY, None)]
    seen = set()
    best_end, best = BOUNDARY + 1, None
    optimize_heap = prefer_far and bridge is None
    while stack:
        i, n, f, choices = stack.pop()
        key = i, n, f
        if key in seen:
            continue
        seen.add(key)
        available = f - n if bridge else (BOUNDARY - n) + (far - f)
        if remaining[i] > available:
            continue
        if optimize_heap and n + max(0, remaining[i] - (far - f)) >= best_end:
            continue
        if i == len(order):
            result = []
            if bridge:
                start = align_up(max(n, BOUNDARY - bridge.size + 1), bridge.alignment)
                if start >= BOUNDARY or start + bridge.size > f:
                    continue
                result.append((bridge, start))
            while choices is not None:
                obj, address, choices = choices
                result.append((obj, address))
            if not optimize_heap or n == near:
                return result
            best_end, best = n, result
            continue
        obj = order[i]
        ns = align_up(n, obj.alignment)
        fs = ((f - obj.size) & -obj.alignment) if bridge else align_up(f, obj.alignment)
        limit = BOUNDARY if bridge else far
        near_option = (i + 1, ns + obj.size, f, (obj, ns, choices))
        far_option = (i + 1, n, fs if bridge else fs + obj.size, (obj, fs, choices))
        options = ((far_option, fs >= BOUNDARY), (near_option, ns + obj.size <= BOUNDARY))
        if not bridge:
            options = ((far_option, fs + obj.size <= limit), options[1])
        stack.extend(option for option, valid in (options[::-1] if prefer_far else options) if valid)
    return best


def place(items, near_start, near_end, runtime, heap):
    if near_end > BOUNDARY:
        required = near_end - near_start
        available = BOUNDARY - near_start
        excess = required - available
        stack = near_start - 0x7E0100
        raise ValueError(near_exhaustion(
            f'Static allocations and alignment need {required:,} bytes, with {available:,} available '
            f'above the {stack:,}-byte stack ({excess:,} {"byte" if excess == 1 else "bytes"} over).'))
    if not items:
        return None
    far_end = runtime['lower']
    if not near_start <= near_end <= BOUNDARY:
        raise ValueError('required application data does not fit in near WRAM')
    placed = assignments(items, near_end, far_end, heap)
    if placed is None:
        for bridge in sorted((o for o in items if o.crossing and o.size > 1),
                             key=lambda o: (-o.size, o.name)):
            if any(o.size > max(BOUNDARY-near_end, far_end-BOUNDARY)
                   for o in items if o != bridge):
                continue
            placed = assignments([o for o in items if o != bridge], near_end, far_end, heap, bridge)
            if placed is not None:
                break
    if placed is None:
        raise ValueError(f'expanded WRAM overflow: {sum(o.size for o in items)} object bytes, '
                         f'{BOUNDARY-near_end} near and {far_end-BOUNDARY} bank-$7F bytes free '
                         'before alignment and single-bank constraints')

    result = []
    cursors = [near_end, BOUNDARY]
    padding = 0
    for obj, start in sorted(placed, key=lambda pair: pair[1]):
        end = start + obj.size
        bank = int(start >= BOUNDARY)
        parts = []
        address = start
        for part in obj.parts:
            parts.append(dict(name=part.name, address=address, size=part.size,
                              alignment=part.alignment, clear=part.clear))
            address += part.size
        pad = align_up(cursors[bank], obj.alignment) - cursors[bank]
        padding += pad
        result.append(dict(name=obj.name, address=start, end=end, size=obj.size,
                           alignment=obj.alignment, crossing=start < BOUNDARY < end,
                           placement='xbankram' if obj.crossing else 'hiram',
                           alignment_padding=pad, preceding_gap=start-cursors[bank], parts=parts))
        cursors[bank] = min(end, BOUNDARY) if bank == 0 else end
        if start < BOUNDARY < end:
            cursors[1] = end
    first_header = min(BOUNDARY, align_up(cursors[0], 2))
    return dict(near_start=near_start, mandatory_near_end=near_end, near_end=cursors[0],
                far_end=far_end, runtime_backfill=runtime['used'], alignment_padding=padding, objects=result,
                heap=dict(linked=heap, start=first_header, end=BOUNDARY,
                          payload=max(0, BOUNDARY-first_header-2)))


def parts(layout):
    if layout:
        yield from (part for obj in layout['objects'] for part in obj['parts'])


def run_regions(layout):
    return [f' RAM_{p["name"]}: start=${p["address"]:06X}, size=${p["size"]:X}, type=rw, file="";'
            for p in parts(layout)]


def segment(part, load=None):
    name = part['name']
    if part['clear']:
        return f' {name}: load=RAM_{name}, type=bss, define=yes, align={part["alignment"]};'
    return f' {name}: load={load}, run=RAM_{name}, type=rw, define=yes, align={part["alignment"]};'


def near_tail(layout):
    # ld65 derives __NEAR_LAST__ from the highest byte claimed in NEAR
    # The annotated segments have independent run regions, so mark their end
    if layout and layout['near_end'] > layout['mandatory_near_end']:
        return f' {TAIL}: load=NEAR, type=bss, start=${layout["near_end"]-1:06X};'
    return None


def init_lines(layout):
    """Every DATA part is packed into a contiguous hardware ROM window."""
    for p in parts(layout):
        name, size = p['name'], p['size']
        dest = f'__{name}_RUN__'
        yield f'.import {dest}'
        source = 'startup_zero'
        if not p['clear']:
            source = f'__{name}_LOAD__'
            yield f'.import {source}'
        for offset in range(0, size, 0x10000):
            mode = '$08' if p['clear'] else '$00'
            yield f'    boot_dma_known {source}, {dest}+{offset}, {min(size-offset, 0x10000)}, {mode}'


def verify(layout, linked, symbols, loads):
    for p in parts(layout):
        name = p['name']
        if linked.get(name) != (p['address'], p['size']):
            raise RuntimeError(f'final WRAM run extent differs for {name}')
        if not p['clear']:
            if symbols.get(f'__{name}_LOAD__') != loads[name]:
                raise RuntimeError(f'final WRAM load extent differs for {name}')
            p['load'] = loads[name]
    if layout and symbols.get('__NEAR_LAST__') != layout['near_end']:
        raise RuntimeError('final __NEAR_LAST__ differs from the expanded WRAM plan')
