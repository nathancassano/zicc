# Running cursors for struct arrays

The general cursor path below remains the fallback. Eligible whole-function
reductions now use the smaller countdown frame described in
[counted-reductions.md](counted-reductions.md).

To move to the next struct in an array, add the size of one struct to the
current address. This also works for structs larger than two or four bytes.
For eligible loops, each call keeps its own near pointer. It starts at the
element chosen by the current index. When the index increases by one, the
pointer moves to the next struct. Field reads use fixed offsets from there.
In `inventory_value`, each struct takes eight bytes.

```asm
lda a:$0009,y       ; keep the C index
inc a
sta a:$0009,y
lda a:$000B,y       ; current element cursor
clc
adc #$0008
sta a:$000B,y
```

Its body loads X from `$000B,y`, with no index-scaling shifts. The cursor survives
arithmetic helpers in its frame home. This is not a register pinned across calls.
The C index retains its normal value in conditions, arguments, returned values,
pre/post increments and assignments. Break/continue and nested calls use the
existing control flow and index-update hooks.

Declared arrays and unchanged pointer parameters are eligible; indices must be
local/parameter word integers. Escaping index/base addresses or explicit pointer
base writes disable a candidate. Global/local pointer variables and non-affine
accesses retain the old path. Up to 32 base/index pairs are selected within the
existing frame limit, with two frame bytes per pair. Recursion owns separate
slots. These are the pre-existing conservative safety rules.

Constant initialization and copying another cursor can avoid scaling entirely.
Parameter indices and nonlinear assignments synchronize by scaling at that write:
power-of-two sizes use shifts; other struct sizes use `__mul16`. Ordinary unit
increments do not multiply. The old two/four-byte paths retain their shifts.
Explicit ROM initializer images are also excluded from the WRAM addressing hint,
so ROM data keeps absolute accesses through the normal FastROM bank.

## Matched inventory measurement

The baseline includes shared structure-element addresses. Same unchanged C,
startup, integer runtime and FastROM layout; two fresh MesenCE runs per compiler
agree exactly, return zero, balance the stack and retain identical call counts.
Timing starts at main entry and ends after return, excluding startup/exit cleanup.

| Metric | Shared addresses | Plus running cursors |
| --- | ---: | ---: |
| Master clocks | 21,282 | 20,826 |
| Microseconds at 21.477272 MHz | 990.91 | 969.68 |
| Application code bytes | 414 | 412 |
| All linked code bytes | 1,690 | 1,688 |
| Used non-asset ROM bytes | 1,778 | 1,776 |
| inventory_value allocated frame bytes | 12 | 14 |

The incremental gain is 456 master clocks (2.14% elapsed time), two code bytes,
and two additional frame bytes. Maintaining a cursor has a cost; zero-trip and
short loops can pay initialization without recovering it. No index elimination
or new register allocation is introduced. These are master clocks, not CPU cycles.

Evidence is under `build/struct-cursor-trial/`: `measurements.json` combines
source/compiler/ROM hashes, commands, sizes, profiler records, frame sizes and
timings. Baseline/candidate directories retain emitted assembly, maps, symbols,
ROMs, Lua and logs. The private baseline is `baseline.exe` in that trial directory.

`tests/check-struct-cursors.py` runs twelve MSVC/Mesen on/off programs plus the
catalog. It covers 6/8/12-byte strides, parameter and negative starts, empty/null
loops, local and ROM arrays, index copies/reassignment, nonlinear updates,
break/continue, descending/non-unit steps, used pre/post results, wrapping and
recursion. Escaped indices, mutated bases and escaped bases are checked for
fallback. Shape checks require the eight-byte advance and absence of scaling in
the inventory function. `--baseline PATH` also executes the same sources through
a saved compiler. Default on/off checks are included in `make check`.

Validation completed: full `make check` passed. Final paired checks include
affine offsets and a post-loop read; those results and fresh two-run timing
measurements match the final compiler hash. Cursor edits remain uncommitted.
