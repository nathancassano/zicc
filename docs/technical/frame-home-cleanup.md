# Unrolled-loop frame homes

When the compiler writes out all the iterations of a loop, the generated code may no longer need to store the next address or the loop index. This change removes the stack space for the address first, then removes the index slot if the program never reads it again.

The first stack cleanup followed the analysis of DRAM refresh alignment in the zero-count timing measurements.

## Plan before storage

Affine collection uses the same eligibility predicate as register-loop emission
and freezes the existing cost-based unroll decision. Emission consumes that plan.
A fully expanded region forms its cursor in X and receives no affine frame slot.
Rolled and runtime-grouped regions retain their cursor storage.

After affine planning, a private local induction word may lose its home when:

- the region is fully expanded and has a constant initializer;
- body values and final-index recovery do not require the C index;
- no use outside that region or escaped address observes it; and
- address setup can fold its uses or obtain an initialized function cursor,
  without loading the index home.

For example, an address containing `j+offset` still needs the index home when
the entry emitter leaves that scalar expression dynamic. Index-valued stores,
returned indices, runtime spans and shared indices retain their homes. The
analysis follows the actual address selector, including existing function cursors.

The eliminated initializer is a pure constant assignment. Its store is omitted,
while any derived function cursors are synchronized from a normalized literal.
Empty dead regions need no such synchronization. The AST is retained.

## Layout and ownership

Compaction removes complete two-byte holes and shifts retained symbol and cursor
offsets by the same amount. Existing alignment/padding and distinct homes survive;
there is no sharing of slots between live objects. Div/mod storage is allocated
after this pass. Final frame size, incoming stack-argument offsets, and wide-return
scratch are then calculated through the existing ABI path.

Emitter guards reject an unexpected read/write through an eliminated home. Loop
plans and bounds refer to symbols, so their offsets follow compaction. Existing
DP counter, arithmetic workspace, caller-register and interrupt ownership apply.

This milestone kept stack-argument frame reservations and live register-argument
homes.

The later [stack-argument reservation cleanup](stack-argument-reservations.md)
removes the incoming-argument reservations in the ordinary framed path and
handles transitions down to zero allocated local bytes.

## Verification

The existing strength suite checks that the four opaque constant-span kernels
have eight-byte frames and eliminated induction homes. The runtime kernel keeps
its ten-byte frame and index home. Additional MSVC/emulator cases exercise empty
regions, cast initializers with derived cursors, dynamic-offset fallbacks,
escaped neighboring structs, retained arrays/scalars, stack arguments, wide
returns and recursion. Existing visible-index, unsigned-boundary, width, runtime
tail and NTSC/PAL handler checks remain enabled.

Before/after evidence is under `build/frame-home-evidence/`: the baseline compiler,
source archive and complete loop outputs were frozen before source edits. The
same separately compiled opaque drivers/kernels are used without LTO, with
input/call/write/result assertions, identical FastROM/near-pointer runtime,
linked sizes and repeated raw timing samples. The comparison tool also records
frame inventories. Zero-count comparisons use the existing controlled-phase
replay tool with explicit baseline and candidate evidence directories.

## Results

Both versions enabled unrolling. The saved baseline used the earlier affine address setup optimization. Each raw sample sequence
was reproduced three times. Clocks cover the complete opaque call, including
setup and return; refresh ranges are retained.

| Kernel | Frame bytes before/after | Code bytes before/after | Master clocks before | Master clocks after |
|---|---:|---:|---:|---:|
| Across five row elements | 12 / 8 | 77 / 71 | 960-1000 | 942 |
| Down three column elements | 12 / 8 | 78 / 72 | 1058 | 1000 |
| Three rows of five elements | 12 / 8 | 124 / 118 | 2806 | 2592-2632 |
| Five columns of three elements | 12 / 8 | 122 / 116 | 4916-4956 | 4626-4666 |
| Runtime row | 10 / 10 | 183 / 183 | See retained samples | Same lowering |

Each constant-span kernel saves one affine cursor word and one induction word.
Frame-size immediates shrink, but the large-frame allocation instruction count
does not change. The executed savings come from removing the initializer
load/store: six code bytes, executed once per expanded region. Refresh alignment
can hide or expose another 40 clocks in the complete-call samples.

The unrolling-disabled kernel assembly matches the baseline byte for byte.
The zero-count runtime path retains 27 instructions and 92 CPU cycles. Its
controlled replay has identical results for all 1024 paired calls over 331
horizontal phases, repeated three times: 567 calls at 592 master clocks and 457
at 632 in each version. Both original driver zero-count samples are 632 clocks.

Final `make check` passed 27/27 suites and 76/76 jobs in 286.78 seconds, using
the hardware-thread default of 20 workers. Logs and compiler/input summary:
`build/check/20261106T155934.758330Z/` (UTC naming; completed November 7 locally).
All existing arithmetic batches and coverage remain intact.

Evidence:

- `build/frame-home-evidence/baseline-*.exe` and `before/source.zip`:
  frozen baseline compiler and source.
- `build/frame-home-evidence/before/loop-unroll-check/` and `after/`:
  complete kernel/driver assembly, objects, ROMs, maps, debug data and raw runs.
- `build/frame-home-evidence/comparison/results.json`: matched source/runtime
  hashes, frame inventory, sizes, complete-call timings and setup-latency replay.
- `build/frame-home-evidence/zero-count/results.json`: controlled-phase ROMs,
  instruction traces, repeated samples and emulator/tool/runtime hashes.
- `build/frame-home-evidence/make-check.log`: complete verification launcher log.
