# Loop overhead integration with DBR $7E

The compiler gained these loop shortcuts while keeping its near pointers into
memory bank `$7E`. See the
[current allocation rules](operations.md#direct-page-homes-and-register-cursors)
for the later direct-page and register optimizations.

## Compatibility decisions

- Keep main's near-memory ABI: A/X/Y16, D=$0000, DBR=$7E, 16-bit near
  pointers and four-byte far pointer values. Near globals remain at $7E:2000
  and above. Entry leaves emit ordinary absolute-indexed stores through DBR;
  they neither change DBR nor assume the bank-zero low-RAM mirror.
- Keep main's far-pointer rejection guards in affine/strength planning, its
  named-ROM absolute-long loads, and its far/indexed-far leaf selectors ahead
  of the new near leaves. New near-entry address matching explicitly rejects
  far-valued address expressions and banked destinations.
- Share the bounded scale selector with named ROM accesses by passing the
  already-evaluated index expression. Complex/call indices are staged once;
  the selector never re-evaluates side effects.
- Preserve `copy_prepare` before slot planning, then relocate aggregate
  temporary symbols along with ordinary symbols/cursors/caches when slots
  compact. Preserve main's switch control targets and switch-depth reset.
- Skip affine planning inside switches, matching main's existing prohibition
  on optimized loop emission there. Case labels may enter past initializers;
  such loops must keep ordinary homes. Parameter liveness treats switch/case
  regions conservatively.
- Preserve main's bank-zero-only indexed direct-page eligibility. General
  near pointers and high WRAM arrays never acquire bank-zero addressing.
- Retain main's interrupt DBR=$7E setup and all near/far conversions, type,
  initializer, union/aggregate, library, runtime and linker changes.
- The [near-loop milestone history](near-loop-overhead-history.md) records the
  old ABI. Its bank-$80 timings predate the ABI migration.

## Verification and evidence

The baseline executable, source and loop artifacts are saved in
`build/integration-evidence/before/`. Every integration comparison
uses this bank-$7E-compatible baseline and the same migrated runtime. The
comparison/replay tools reject old bank-$80 generated assembly rather than
linking it to the new runtime.

`tests/bank7e_loop_cases.c` runs in the existing frame suite. Its high arrays
are above $7E:6000, outside the low-RAM mirror. It checks near byte/word/wide
stores, nested/runtime loops, far multidimensional fallback, mixed far/word/wide
stack arguments, call-indexed ROM record scaling, aggregate-value temporaries,
switch-contained loops, canaries and whole-array contents. MSVC provides an
independent C reference. Per-call hooks require DBR=$7E and preserve Y/D/DBR/SP.
Existing queue boundaries and all arithmetic vectors are unchanged.

The focused frame/strength run and final `make check` results, plus repeated
opaque-kernel/ABI/controlled-zero-count comparisons, are recorded below after
completion. Evidence uses fresh directories and retains failed attempts.

HiROM layout files and runtime boot support remain exactly as in main; this
integration does not add the separate HiROM startup/finalizer support noted in
those layout files. Executable validation uses the supported LoROM runtime.

## Matched bank-$7E results

The focused frame/strength run passed 2/2 suites in 131.08 seconds. The frame
suite now contains 13 sequential fixtures inside its original queue job.

Three repeated opaque-kernel replays require identical calls, inputs, byte-write
counts, final indices and full array contents. Complete callee master clocks
include return and observed refresh stalls:

| Kernel | Baseline | Integrated | Code bytes before/after | Frame bytes before/after | Peak stack below call entry before/after |
|---|---:|---:|---:|---:|---:|
| Five elements across a row | 2052 | 458-498 | 100 / 32 | 12 / 0 | 16 / 0 |
| Three elements down a column | 1126 | 286 | 83 / 19 | 12 / 0 | 16 / 0 |
| Three rows of five elements | 3764 | 900 | 144 / 66 | 12 / 0 | 18 / 0 |
| Five columns of three elements | 5296 | 1040 | 127 / 74 | 12 / 0 | 18 / 0 |

The runtime-row frame shrinks from ten to six bytes. Calls at counts 1/32/64
change from 1556/3252/4936 to 1278/2974/4658 clocks in the retained driver.
All counts 0..65 pass three repetitions. The raw zero-count sample moves from
592 to 632 clocks, but the matched-phase replay is identical: 1024 calls across
331 entry phases, repeated three times, each version executing 27 instructions
and 92 CPU cycles. Each replay has 565 calls at 592 and 459 at 632 clocks. This
is refresh alignment, not added zero-count work.

The high-WRAM migration fixture passes an MSVC reference and three independent
ABI replays. Application code shrinks from 3715 to 3254 bytes. Its global minimum
observed SP rises from 8138 to 8144 (six fewer peak stack bytes). Near leaves
have zero frames; far_matrix remains a far fallback and shrinks from a ten-byte
to four-byte ordinary frame through reservation cleanup. Mixed far/wide argument
homes shrink from eighteen to eight frame bytes. Aggregate-copy temporaries and
switch loops retain their correct ordinary homes. The fixture's whole-program
time is ABI/correctness evidence and is not a kernel-throughput claim.

Evidence: `loop-comparison/results.json`, `bank-abi-comparison/results.json`,
`zero-count/results.json`, raw replay/instruction logs and all baseline/candidate
sources/assembly/ROMs under `build/integration-evidence/`. The tools compare
source/runtime hashes and reject incompatible old-ABI artifacts.

## Ready-to-merge verification

Final `make check` passed 27/27 logical suites and 76/76 queue jobs, including
all 200,873 arithmetic cases, in 360.79 seconds with the default 20 workers.
The candidate executable hash matches the full-check summary. Logs and complete
job status: `build/check/20261107T022648.042828Z/` and
`build/integration-evidence/make-check.log`. Union, aggregate-copy, switch,
legacy-function, near/far bank-pointer, library, far-loop, far-loop interrupt,
time, general interrupt and scratch-preservation coverage all remain included.

The integration worktree is archived in `E:/archived-compiler/worktree-loop-overhead-integration.zip`,
under `.worktrees/loop-overhead-integration/`.
