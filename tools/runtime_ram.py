"""Reserve space for the runtime in working RAM, filling from the top of bank $7F."""
RUNTIME_RAM = ('CONSOLE_MAP', 'RUNTIME_BSS', 'RUNTIME_CLOCK', 'RUNTIME_CONSOLE')
LOW = 0x7F0000
HIGH = 0x800000


def backfill(records, reserved=()):
    """Place live segments downward, rejecting bank/collision/alignment overflow.

    Records retain the linker segment's measured size/alignment and contributing
    member ownership. Ordinary application BSS is never implicitly reclassified.
    Fixed application extents, when supplied, reserve holes in the same bank.
    """
    holes = sorted(reserved)
    for i, (lo, hi) in enumerate(holes):
        if not LOW <= lo < hi <= HIGH or i and holes[i-1][1] > lo:
            raise ValueError('invalid/overlapping reserved runtime-bank extents')
    cursor = HIGH
    placed = []
    for record in sorted(records, key=lambda r: r['name']):
        size, alignment = record['size'], record['alignment']
        if size < 0 or alignment < 1 or alignment & (alignment-1):
            raise ValueError('invalid runtime RAM size/alignment')
        if not size:
            continue
        end = cursor
        while True:
            start = (end-size) & -alignment
            conflict = next(((lo, hi) for lo, hi in reversed(holes)
                             if start < hi and end > lo), None)
            if conflict is None:
                break
            end = conflict[0]
        if start < LOW:
            raise ValueError(f"runtime RAM overflow at {record['name']}: required {size} bytes, "
                             f"alignment {alignment}, padding/skipped {cursor-end+end-size-start}, "
                             f"available {max(0,cursor-LOW)} bytes in bank $7F")
        placed.append(dict(record, address=start, end=start+size,
                           padding=cursor-start-size))
        cursor = start
    return dict(bank=0x7F, lower=cursor, upper=HIGH, used=HIGH-cursor,
                payload=sum(r['size'] for r in placed),
                padding=sum(r['padding'] for r in placed), objects=placed,
                reserved=[list(h) for h in holes])
