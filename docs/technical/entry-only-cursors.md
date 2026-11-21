# Entry-only cursor inputs

Some functions only fill a short run of array cells. If the compiler knows how many cells to fill and the value stays the same, it can use the incoming registers to find the first cell and write the whole run without a stack frame.

This work followed the removal of unused register parameter homes and entry spills. The compiler tries the rules in `src/codegen/entry_cursors.inc` after its existing special cases.

## Eligibility and lowering

The first supported form is an ordinary, non-variadic void function containing
one fully unrolled affine word assignment loop, optionally followed by a plain
void return. Empty declarations/statements are harmless. The existing cached
unroll plan must select a constant full span, invariant value, and dead local
index. The store must be a numeric word assignment.

Parameter 0 is a near pointer in X; parameter 1 is a word integer in A. A pure
address planner substitutes the constant initial index and describes the start
as `X + A * coefficient + constant`, modulo the 16-bit near-pointer width. It
supports the existing affine additions/subtractions, constant products and
type-preserving casts. Narrowing/discontinuous or unsupported expressions retain
ordinary lowering. The existing word-scale selector must accept bounded inline
setup; no multiplication helper is called by this leaf.

The scalar is scaled in A while X retains the base. When needed, the arithmetic
RHS word stages the scale input; after scaling, it stages X for the final add.
The final address stays in X. The invariant store value must be a literal or a
private word parameter in position 2 or later, optionally with word-to-word
integer casts. Stack offsets include preceding stacked arguments of their actual
ABI widths. The routine has made no pushes, so parameter 2 is at `3,S`; a word
after a preceding stacked long is at `7,S`.

The leaf emits the existing selected span of fixed-displacement word stores and
RTS. It needs no parameter homes, index home, intermediate cursor slot, Y frame
base or frame/return cleanup. It does not change Y/D/DBR or S. A/X and arithmetic
scratch retain their normal caller-clobbered contracts. Void functions need no
synthetic zero result. The near return address and caller-pushed arguments still
occupy the caller's stack; zero callee-added depth does not eliminate that ABI
cost.

An empty selected region emits only RTS: it does not form an address or load a
store value. This permits a zero-trip call with a null base, just as the C loop
does. Calls, additional statements, branches, nested loops, observable indices,
global reloads, byte/wide stores, values needing X/A after setup and unsupported
arithmetic keep their existing lowering. The unroll policy and budgets remain
unchanged. No source name or array dimension selects this path.

## Verification

The existing frame suite includes `tests/entry_cursor_cases.c` with MSVC reference
execution, target execution, ABI hooks and instruction-boundary stack tracking.
It checks negative input rows, nonzero/negative starts, unsigned starts near
65535, negative/zero/repeated scalar coefficients, constant/base-only addresses,
non-power-of-two row strides, literals, unsigned words, explicit void return and
stacked values after a wide argument. Empty calls check that a null base is not
used. Assembly assertions require no stack/Y operations for selected leaves.

Fallback execution checks cover an inline-scale cost rejection, narrowing casts,
global reloads at every assignment, extra statements, returned indices, byte
stores and wide stores. The target fixture makes the same 57 instrumented C
calls in both versions, with complete matrix/result checks and Y/D/DBR/stack
restoration. Three retained-ROM replays reproduce the outcomes and per-function
stack depths with matched source/runtime hashes. Its application CODE shrinks
from 3850 to 3316 bytes; its global minimum SP remains 8152 because fallback
functions still determine the maximum. This single-TU ABI fixture is not used
as a kernel-throughput comparison.

The opaque timing kernels and drivers remain identical C sources compiled as
separate translation units without LTO. Execution hooks verify inputs, actual
calls, exact byte-write counts, complete contents and return/stack results.
Both use the same FastROM, near-pointer ABI and runtime objects. Every raw timing
sequence is reproduced three times, including refresh-phase differences.

| Kernel | Frame bytes before/after | Peak bytes below call entry before/after | Code bytes before/after | Complete-call master clocks before | After |
|---|---:|---:|---:|---:|---:|
| Across five row elements | 6 / 0 | 8 / 0 | 71 / 32 | 942 | 458-498 |
| Down three column elements | 6 / 0 | 10 / 0 | 72 / 19 | 1000 | 286 |
| Three rows of five elements | 8 / 8 | 12 / 12 | 118 / 118 | 2592-2632 | 2592-2632 |
| Five columns of three elements | 8 / 8 | 14 / 14 | 116 / 116 | 4626-4666 | 4626-4666 |

These are complete calls, including setup and return. The speedups include the
removed ordinary prologue, spills, staged addresses and return cleanup; they
are not isolated arithmetic timings. Nested kernels retain their lowering;
individual samples can move by a refresh stall as preceding calls become shorter.

Entry-to-first-write latency drops from 586 to 250-290 clocks for the row and
from 724 to 158 for the column. Those setup-inclusive observations are retained
alongside the complete-call samples, not used as an instruction-category ranking.

The runtime row retains its ordinary lowering. Controlled zero-count replay
matches for 1024 paired calls across 331 horizontal phases, repeated three times:
567 calls at 592 master clocks and 457 at 632 in each version. It still executes
27 instructions and 92 CPU cycles. Original zero-count driver samples are both
632 clocks.

Final `make check` passed 27/27 suites, 76/76 jobs and all 200,873 arithmetic
cases in 281.07 seconds with the hardware-thread default of 20 workers. The
shared queue and arithmetic batches are unchanged; the new ABI fixture runs
inside the existing sequential frame suite. Full logs/summary:
`build/check/20261106T175809.397768Z/` (UTC naming; November 7 locally).

## Evidence

`build/entry-cursor-evidence/` retains the frozen baseline compiler/source ZIP,
baseline and candidate fixture outputs, assembly, objects, ROMs, debug labels,
source/compiler/runtime hashes, raw execution logs, repeated profiles and full
verification.


Each replay output contains `results.json` and the raw runs. Candidate sources,
patch and executable are frozen alongside the before/after evidence.

## Subsequent extensions

This report describes the first entry-only cursor implementation. The
[five follow-up milestones](loop-follow-ups.md) extend stores/values, final
indices and nested/runtime regions, then improve address storage/staging and
parameter liveness. Their scope, verification and evidence are recorded separately.
