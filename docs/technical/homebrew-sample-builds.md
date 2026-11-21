# Homebrew sample ports and 600-logical-frame timings

In this trial, all three BouncingSprites builds put the same sprites in the
same places for 600 updates. Each took two video frames per update, though the
CPU spent different amounts of that time working in each build. These results
predate the arithmetic-region and runtime changes.

Work is isolated at `C:/snesdev/compiler/build/worktrees/homebrew-samples`, based
on the source LTO baseline. The original checkout and its ongoing PI investigation were not
changed. Nothing is committed.

## BouncingSprites results

Two fresh NTSC runs per build execute exactly 600 logical updates. Startup is
excluded. Every update is checked against a host reference: all ten positions
and velocities, all 544 OAM-shadow bytes, the 281-byte HDMA table and its phase.
All six runs agree on the complete state sequence (SHA-256
`0bad2bb9b559eb75c14a74746e26f6122a74175e2d3291d8deb1742b5576fd1d`).
Their final screenshots are pixel-identical, RGB SHA-256
`31f30fb3c18a97acbb3e58b3b7d8341e3289865420afda2a34fff77933192b5a`.

| Build | Average update master clocks | Average update ms | Average master clocks including wait | Average ms including wait |
| --- | ---: | ---: | ---: | ---: |
| zicc-fast | 430,994.45 | 20.067467 | 714,731.90 | 33.278523 |
| zicc-slow | 510,386.01 | 23.764005 | 714,731.83 | 33.278520 |
| vbcc-slow | 397,479.03 | 18.506961 | 714,732.07 | 33.278531 |

Each run covers 600 logical frames across **1,200 physical frames**. Both repeats
agree exactly on total clocks, update clocks and physical-frame counts. The
small differences in wait-inclusive averages reflect instruction/polling phase;
all three builds sustain one logical update every two physical frames.
Milliseconds use the existing comparison convention of 21,477,272 master clocks
per second. Master-clock totals are the primary measurements.

An update starts after the two VBlank wait loops, immediately before argument
setup for `LoadOAMCopy`. It ends after gradient, motion/collision and OAM-shadow
updates, at the return to the outer loop's first wait. This includes OAM DMA,
call/argument overhead and hardware DMA/HDMA stalls. Wait-inclusive time spans
600 intervals from that start boundary to the next start, ending before update
601. It is not an average over physical screen refreshes. No instrumentation
instructions are inserted into the ROM; Mesen execution callbacks observe the
existing linked instruction addresses. Generated assembly was checked against
the C loop to identify those boundaries.

The main loop's calculations, initial inputs and iteration counts match between
compilers. zicc-specific adaptations affect ROM/RAM pointers, bank-zero MMIO
and HDMA source-address construction. zicc uses near `$7E` data pointers where
possible and the project HiROM startup/runtime; stock VBCC uses its far-pointer
ABI, LoROM startup/runtime and SNES multiplication helper. `zicc-slow` versus
`vbcc-slow` matches ROM speed. These are application-update measurements with
those target/ABI/runtime differences, not an isolated instruction-selector test.

### Historical build

The build command attempts both demos and exits 1 because Whetstone remains
blocked for zicc; the BouncingSprites images are produced successfully.
Omit `--fetch-support` when the pinned support cache is present. Output directories
must be fresh. Pillow is required. The profiler currently recognizes the retained
assembly's named loop boundaries; inspect/update those mappings for changed code.
New runs save the expected frame data as `expected-frames.bin`.

Accepted build evidence: `build/homebrew-samples/ported5/results.json` and each
configuration's assembly, map, labels and ROM. Accepted measurements:
`build/homebrew-samples/logical600-final/results.json`, plus each run's Lua,
expected frame data, log, result and screenshot. The build manifest records source,
compiler and VBCC runtime hashes; measurements record ROM, Lua and emulator hashes.
Earlier `ported1`..`ported4` and `logical600*` directories retain rejected or
superseded attempts. Initial profiling exposed Mesen's log-line and log-buffer
limits; the accepted harness asserts every state in Lua and emits compact final
measurements instead of relying on a truncated per-frame log.

## Compiler changes

`void main(void)` is accepted alongside `int main(void)` as a freestanding SNES
entry point. Startup calls it with JSL, ignores its result and enters `main_exit`
on return. Parameterized or other-return-type definitions remain rejected;
calling main from C remains prohibited. Runtime tests cover explicit void return,
fallthrough, side effects, stack balance and DBR preservation.

Profiling also exposed a pre-existing signed-char typedef bug. Declaration parsing
copied the typedef's type, then unconditionally applied plain-char unsignedness.
Consequently `int8_t` velocities such as -2 were loaded as 254. The fix preserves
an alias's signedness, while retaining the default unsigned plain char. Tests
execute every byte value through alias chains, arrays, parameters and pointers.
The timing results above use this correction; incorrect-animation timings were
rejected.

## Port and Whetstone status

The samples used for these measurements had import manifests and MIT licenses.
They originate
from [Flipphone22/snes-homebrew](https://github.com/Flipphone22/snes-homebrew/tree/bcaeb12e4aab9336a5b1df9afa8542f875d4fc9b/SimpleCDemos),
commit `bcaeb12e4aab9336a5b1df9afa8542f875d4fc9b`.
The build runner stages shared dependencies and generated assets under `build`.

With DBR=$7E, ROM strings/data cannot travel through ordinary near pointers.
The staged zicc port uses explicit far source parameters/casts, bank-zero far
MMIO pointers and a widened `$7E` RAM pointer when extracting the HDMA bank.
Whetstone's immutable function-local palette arrays move to file scope, its NMI
body receives the native interrupt attribute, and its unsafe manual clearing of
live C RAM is omitted because startup already initializes WRAM.

`--whetstone-math approximate` explicitly enables Whetstone's existing VBCC/LLVM
local approximations for `sin`, `cos`, `atan`, `sqrt`, `exp` and `log` (the default).
`--whetstone-math library` instead uses compiler-supplied binary32 assembly math.
Runtime integer/float conversion support allows both modes to compile and link
as FastROM or SlowROM. The approximation mode retains the upstream algorithms
and their limitations; it is distinct from the range-reduced library routines.
The archived Whetstone check executed all eight original kernels using opaque
`xtra=x100=1` from a separate driver translation unit, without LTO or inlining.
It checks outputs against a strict binary32 host reference and requires actual
math/pa/p3/po call counts. Timing/UI are omitted from this reduced semantic test;
it is not a throughput measurement or the full `x100=100` benchmark.
Both VBCC samples link with stock r2 `+snes-lo -O3 -msfp4`, `libms4.a` and
`libvc.a`; the optional unavailable vcpr6502 step is omitted. VBCC compilations
are serialized and use private temporary directories.

## Verification

The complete `make check` run after the entry-point change used the default
20 hardware threads and retained `build/check/20261108T081302.624726Z`. It finished
25/27 logical suites in 440.52 seconds, with 81 cached and 1,259 emulated runs.
Failures were missing fresh-checkout `malloc.o`/`free.o` prerequisites for loram,
embed executing before the standalone preprocessor driver was available, and a
frame-worker result/stack assertion under load. The frames collector consequently
did not run.

Focused follow-ups preserve the unaffected passing evidence. After generating
the missing prerequisites, preprocessor, embed and loram pass. The failed
`integer_operations_runtime` frame worker passes on its isolated rerun. Following
the typedef correction, the all-256-values typedef test, main-entry test and
scalar-values semantic/interrupt suite pass, as do all six 600-update sprite runs.
Raw follow-up logs are `build/followup-*.log` and `build/compiler-check`. The full
aggregate was not rerun after the typedef fix; no all-green aggregate is claimed.
