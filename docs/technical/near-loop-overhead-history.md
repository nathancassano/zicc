# Loop overhead measurements

Before a loop touches its first array element, it has to find that element's
address. For example, a row ten bytes wide starts at an offset of `row * 10`.
This follow-up to cost-based unrolling measured ways to reduce
that setup work. See [address setup](loop-address-setup.md) and
[the unrolling policy](loop-unrolling.md).

## Address setup implemented

Pointer strides and function cursor synchronization reuse the bounded word
constant-multiply selector. The dynamic `row * 10` setup uses inline shifts and
an add. Selected unrolled loops simplify affine addresses with proven constant
initial indices. Fully expanded regions form their cursor in X without the
intermediate cursor-home store/reload.

The original index home and initialization remain available for body reads and
observable final indices. Runtime groups retain their cursor home across counter
setup. Frame layout and the existing interrupt/DP-counter ownership stay intact.

Entry-to-first-write latency includes prologue, setup and loading the first store
value. It helps locate setup savings but does not rank individual instruction
categories. Whole-call measurements include setup and return, with identical
opaque drivers/kernels in separate translation units, no LTO, and the same
FastROM/near-pointer runtime.

## Measured results

Complete opaque-kernel calls in SNES master clocks; each raw sequence was
reproduced in three emulator runs. The saved baseline used the earlier compiler with unrolling enabled, not the candidate's unrolling-disabled mode.

| Kernel | Before | After | Code bytes before/after |
|---|---:|---:|---:|
| Across five row elements | 1998 | 960-1000 | 100 / 77 |
| Down three column elements | 1086-1126 | 1058 | 83 / 78 |
| Three rows of five elements | 3764 | 2806 | 144 / 124 |
| Five columns of three elements | 5256-5296 | 4916-4956 | 127 / 122 |

Runtime row calls improve from 1556 to 1318 clocks at one element, 3252 to 3014
at 32, and 4936 to 4658 at 64. The kernel shrinks from 198 to 183 bytes. The
zero-element call measures 592 before and 632 after. A subsequent
[instruction trace and matched-phase investigation](zero-count-timing.md)
confirmed this is entirely DRAM refresh alignment: both versions execute the
same 27 instructions and 92 CPU cycles, and have identical 592/632-clock timings
at matched entry phases. The original raw samples remain retained.

Entry-to-first-write latency for the row kernel falls from 1602 to 604 clocks.
For nested rows it falls from 1150 to 804-844. The column case falls from 810 to
742-782 and nested columns from 1070 to 1002-1042. These are setup-latency
measurements, not isolated multiplication timings.

Evidence is local to this worktree under `build/loop-overhead-evidence/`:
`baseline-*.exe`, `before/source.zip`, the complete baseline loop outputs,
`comparison/results.json`, repeated raw profiling logs and full-check logs.
Final loop outputs are in `build/loop-unroll-check/`. The comparison checks
identical kernel/driver sources and runtime inputs, and records source/compiler,
ROM and output hashes. `before/source.zip` contains the source used to build the baseline;
the historical runner's end-of-run live-source hashes can reflect edits made
after its executable was frozen.

Final `make check` passed 27/27 suites and 76/76 jobs in 317.00 seconds with the
hardware-thread default of 20 workers. Full logs and the input summary are in
`build/check/20261106T153140.383537Z/`. Earlier failed runs are retained alongside
the final evidence: one caught a selector type-construction mistake, and one
caught a stale test requiring the helper call that the optimization removes.

## Frame/home follow-up

The first cleanup milestone reduces the four opaque constant-span kernels from
12-byte to 8-byte frames and removes six code bytes from each. Row clocks improve
from 960-1000 to 942; column clocks from 1058 to 1000; nested rows from 2806 to
2592-2632; nested columns from 4916-4956 to 4626-4666. Runtime-row storage and
lowering stay intact, including identical controlled-phase zero-count timing.

The follow-up full check passed 27/27 suites and 76/76 jobs with the normal
20-worker default. [Implementation, limits and evidence](frame-home-cleanup.md)
include the frozen baseline, frame inventories and raw repeated measurements.

## Stack-argument follow-up

Ordinary functions now omit duplicate local reservations for incoming stack
arguments. Row/column frames shrink from 8 to 6 bytes, with two fewer measured
peak stack bytes and unchanged instructions, code sizes and timings. The runtime
row frame shrinks from 10 to 8 bytes; every measured count and controlled-phase
zero-count timing remains unchanged.

The mixed ABI fixture covers zero/two/four-byte frames, wide/float returns,
writable/address-taken parameters, eight arguments, recursion and relocated
objects/caches. It uses 40 fewer peak stack bytes and 172 fewer application code
bytes. The follow-up full check passed 27/27 suites, 76/76 jobs and all 200,873
arithmetic cases with the normal 20-worker default. See the
[implementation and evidence](stack-argument-reservations.md).

## Register-entry follow-up

The [first register-home stage](register-argument-homes.md) removes unused
register parameter homes and skips entry spills when a private parameter is
definitely overwritten in the straight-line prefix before its first read.
Address escapes and early cursor initialization retain incoming values.

Focused cases include 4-to-0 and 6-to-4-byte frame reductions. Their ABI fixture
shrinks from 1566 to 1480 application code bytes, while its overall peak stack
use stays unchanged. The existing opaque loop ROMs were byte-identical.
Full verification passed 27/27 suites, 76/76 jobs and all 200,873 arithmetic
cases with the default 20 workers.

## Entry-only cursor follow-up

The [entry-only leaf](entry-only-cursors.md) directly consumes X/A for
selected single fully unrolled affine word assignments. The row and column
kernels now have zero allocated frame bytes and zero callee-added stack depth,
down from six-byte frames and peak depths of eight/ten bytes. Code shrinks from
71 to 32 bytes and 72 to 19 bytes; complete calls improve from 942 to 458-498
clocks and from 1000 to 286 clocks, respectively.

Nested/runtime and unsupported forms retain their lowering. Controlled-phase
zero-count timing remains identical. Full verification passed 27/27 suites,
76/76 jobs and all 200,873 arithmetic cases with the default 20 workers. The
implementation report links all before/after artifacts and repeated raw samples.

## Five subsequent follow-ups completed

The [follow-up report](loop-follow-ups.md) records the five separately
committed milestones: byte/wide and incoming-A store values; directly returned
final indices; bounded nested expansion and runtime cursor formation; unused
function-cursor removal and simple pointer staging; and control-flow parameter
liveness with later escapes and deferred cursor entry initialization. Each keeps
conservative fallbacks and the existing unroll budget/ABI contracts.

Nested opaque kernels now have no frame or callee-added stack depth. Nested-row
calls fall to 860–900 clocks (66 code bytes) and nested-column calls to
1000–1040 (74 bytes). Runtime-row frames shrink to six bytes, and matched-phase
zero-count timing remains unchanged. The report retains individual baseline and
candidate executables, sources, generated assembly, ROMs, assertions, hashes,
repeated profiles and full-check results. These measurements use the earlier
bank `$80` near-memory ABI.
