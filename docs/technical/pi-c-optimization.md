# Compiler audit of the new C π sample

This audit follows the calculation of 896 digits of π from the first arithmetic step through the final picture. It times the calculation while checking that each version produces the same digits and intermediate values.

The benchmark builds the three sample C translation units independently, with
FastROM and no LTO. The 896-digit precision reaches the kernel at runtime. The
verifier checks every emitted character, 247,507 term-limb writes, the fixed-point
state before conversion, the final VRAM map and the rendered frame.

## Baseline functions

The baseline compiler is pinned in `build/pi-c-optimization/baseline-*.exe`.
The table covers every emitted C function. Inclusive clocks overlap between
callers and callees. The main row uses an entry/return hook. Its self count is
the profiler's root-frame entry.

| C function | Bytes | Calls | Self master clocks | Inclusive master clocks | Assembly finding |
| --- | ---: | ---: | ---: | ---: | --- |
| `main` | 16 | 1 | 176 | 1,044,235,416 | Two calls, an immediate zero result and the startup ABI return. |
| `calculate_pi` | 281 | 1 | 91,468,832 | 1,038,641,338 | The decimal conversion repeatedly rescales the same index, uses a shift/add chain for multiplication by 100 and reloads the limb value before shifting the carry. |
| `arctangent` | 296 | 3 | 2,465,526 | 940,740,924 | The power-array clear loop scales its cursor on every store. The series advances two byte-address cursors alongside the limb index and repeatedly stages invariant call arguments. |
| `divide` | 217 | 1,884 | 490,200,568 | 773,641,992 | Hot loops materialize both pointer post-increments, spill paired results and reload the count. The byte-divisor branch used the generic divider, and the staged correction multiply discarded its mixed-width proof. |
| `accumulate` | 232 | 968 | 164,633,406 | 164,633,406 | The compiler held the logical counter in Y but repeatedly rebuilt its byte address in X. The signed lower-bound check and the six shifts for each carry remain. |
| `pi_emit` | 20 | 898 | 280,892 | 6,082,034 | The wrapper pushes its X argument into an unread home and pops it at return. The constant `"%c"` format still runs through the variadic formatter. |

## General changes and measured trials

- Refine a private scalar from its declared type when a branch comparison
  provides its first known bound. Select 16/8 unsigned division from the
  divisor proof, even with a full word dividend. Signed selection still
  requires a nonnegative dividend. The paired hardware helper saves a
  nested call and preserves both result words.
- Use the same operand-width selection in staged and recursive arithmetic.
  The first trial picked the mixed-width multiplier but slowed the sample
  because the helper always issued the high partial product. The retained
  helper checks the high byte while the first hardware product runs and
  issues a second product only when needed.
- Reuse a scaled array index within a basic block when its input and X
  still agree. Recreate A and N/Z with TXA when live. Keep the original
  computation if the shift's carry is live.

| Trial | Kernel master clocks | Power-on to completed display |
| --- | ---: | ---: |
| Baseline | 1,044,063,632 | 48.667 s |
| Paired byte divisor | 994,347,818 | 46.355 s |
| Mixed operand selection with old multiplier | 1,004,863,054 | 46.837 s |
| Mixed operand selection with conditional high product | 979,452,836 | 45.656 s |
| Reuse scaled index | 958,513,562 | 44.691 s |
| Preserve the multiplier's scratch result on the short path | 961,327,416 | 44.807 s |

The scaled-index change reduces `accumulate` from 232 to 219 bytes. The
retained build saves 61,599,214 inclusive clocks in `divide` and
20,898,600 in `accumulate`. The final mixed-width helper keeps
its scratch result on both paths, and standalone quotient and remainder
helpers are only assumed to return their result in A. The assembly
reference remains at 18.201 seconds.

The first cached `make check` ran 817 jobs across 27 suites. The source
clobber checker could not see the initial macro-generated helper entries.
The frame test also failed once and passed on the same ROM on replay.
After making the helper bodies explicit and preserving their scratch
result, the focused DP-home, arithmetic-region, frame, value-reuse,
private-region and integer-hardware checks passed.
The full queue and initial failures are in `build/check/pi-c-first-pass`.

## Division and decimal conversion

| Trial | Kernel master clocks | Power-on to completed display |
| --- | ---: | ---: |
| Remove dead stack-frame stores | 921,854,610 | 42.977 s |
| Index private word cursors directly at post-update accesses | 858,800,578 | 40.048 s |
| Inline paired 16/8 hardware division in a loop | 783,802,174 | 36.554 s |
| Count unsigned post-test loops in direct page | 769,337,742 | 35.872 s |
| Reuse a scaled index after its entry test | 758,437,216 | 35.373 s |

The late stack pass normalizes frame accesses across pushes and removes
stores when both bytes are dead on every outgoing path. It removed four
quotient and remainder spills from `divide`. Word-pointer post-updates now
load X from the private cursor home, access the old address, and write the
advanced X back. The source and destination arrays may alias. The cursor
objects themselves must be private and unescaped. The direct-load case was
added to the inline hardware division trial after binary and store forms
were measured separately.

The paired hardware path uses an established byte-divisor bound and
preserves both output words. The wide divisor path still calls the
general runtime helper. Both division loops use the saved direct-page
counter for the unsigned predecrement condition. A zero start wraps and
runs 65,536 iterations. The arithmetic-region fixture checks that case,
nested borrowing, early break, continue, and a body that reads the C counter.

In decimal conversion, the load that tests the loop counter also supplies
the first scaling shift. The scaled-index pass now recognizes a tested
entry with no alternate predecessor, including the inverted branch over
a long jump before relaxation. The subsequent store reuses X. The resulting
sequence also keeps the value in A for the mask and drops a reload.

The 896-digit C runs match all 898 output characters, the fixed-point
state, 247,507 term-limb writes, VRAM, and the final screenshot. The
assembly ROM remains byte-identical and completes in 18.201 seconds.
The guard variant that only recognized an ordinary conditional fallthrough
produced a byte-identical C ROM to the countdown trial. The retained
variant is in `build/pi-c-optimization/second-pass-verified`.

| C function | Calls | Self master clocks | Remaining assembly work |
| --- | ---: | ---: | --- |
| `main` | 1 | 176 | The driver makes its two required calls and returns the startup status. |
| `calculate_pi` | 1 | 80,859,268 | Decimal conversion still spends six shifts per carry, and the zero-fill loop builds each byte address from a word index. |
| `arctangent` | 3 | 2,467,386 | The zero-fill loop scales each index, and adjacent calls to `divide` stage the same arguments again. |
| `divide` | 1,884 | 448,666,158 | The scaled divisor is a word in the compiler's range model, so the runtime checks its high byte per limb. The correction multiply also runs through a helper. |
| `accumulate` | 968 | 143,734,426 | Y holds the descending index, which is rescaled on each trip. The signed bound test and carry shifts remain. |
| `pi_emit` | 898 | 281,852 | The unread X home still takes a push and pull. The variadic `%c` formatter accounts for most of the 6,081,214 inclusive clocks. |

The retained function profile is in
`build/pi-c-optimization/second-pass-verified-profile/profile.json`.

## Guarded division and unused saves

| Trial | Kernel master clocks | Power-on to completed display |
| --- | ---: | ---: |
| Inline a guarded byte path for a narrowed word divisor | 747,052,142 | 34.840 s |
| Drop adjacent stack saves and restores when their flags are dead | 739,172,018 | 34.474 s |
| Drop an unread saved X below a wrapper's outgoing arguments | 739,135,386 | 34.474 s |

If a paired divide's unsigned divisor is known to be nonzero and its
narrowed range straddles 256, the loop tests the actual value. The byte
case uses the inline hardware divider. The word case retains the
`__udiv16` helper. The arithmetic-region fixture compares both results
against Python at divisors 255, 256, 257 and 1,023, with the caller's
range guards checked at 0 and 1,024. In the π run the guarded path
absorbs 96,936 helper calls. `divide` inclusive clocks fall from
520,569,298 to 509,177,466 after the three trials.

The stack cleanup drops adjacent push/pull pairs when the pull's N/Z
are dead. It removes one such pair from the complement path in
`accumulate`, reducing its self time to 135,854,262 clocks. The
single-call wrapper pass uses the emitted argument cleanup and stack
depth to prove that the saved X is outside the outgoing block, and
checks that the restore and cleanup results are dead. It removes the
`PHX`/`PLX` around the variadic call in `pi_emit`. The NTSC and PAL
printf cursor probes verify the exact output, truncation to a byte,
return ABI, cursor restoration and nested NMI. The variadic formatter
still handles the call.

Both repeated C runs pass the complete 896-digit verifier. The
hand-written kernel uses the same compiled C wrapper, so the final
assembly ROM image changes and its kernel interval drops by 66,800
master clocks. The completed frame remains at 18.201 seconds.
See `build/pi-c-optimization/third-pass-verified` and
`build/pi-c-optimization/third-pass-verified-profile/profile.json`.

The preceding cached full run finished 26 of 27 suites across 817
jobs. The body-codegen fixture reached its expected emulator result
before its assembly assertion failed. Removing dead frame stores lets
the initial `ADC #$4800` and `ADC #$0400` combine into
`ADC #$4C00`. The test now checks that initial add and three remaining
stride adds, and its complete focused rerun passed. The aggregate
report is `build/check/pi-c-second-pass/summary.json`.

The third-pass snapshot subsequently passed all 27 suites and 817 jobs
in the cached `make check`. Its report is
`build/check/pi-c-third-pass/summary.json`.

## Signed descending loops and fixed word fills

| Trial | Kernel master clocks | Power-on to completed display |
| --- | ---: | ---: |
| Retain the scaled word-array index in X | 736,048,618 | 34.324 s |
| Count signed descending trips with the saved DP word | 731,173,250 | 34.108 s |
| Combine the signed countdown with the retained index | 728,138,812 | 33.958 s |
| Count fixed-array word fills with a retained displacement | 727,843,756 | 33.942 s |

The retained-index pass seeds X from Y before the loop and advances X
by two alongside the logical index. It checks all incoming edges, X
and Y writes, and the original scale's A and flag liveness. The initial
trial ran too early to see the two loops after redundant X saves had
been removed. The combined form also handles the counted loop's
entry jump and both backward edges.

For a signed descending loop with an invariant lower bound, the
entry still performs the original signed comparison. The hot loop
decrements the remaining trip count instead. Break exits preserve the
current logical index and continue reaches the decrement. The
inclusive minimum-bound case retains the target's wraparound behavior
after the first count expires. The standalone test covers negative
bounds, empty ranges, early exits, final index recovery, and all 65,535
iterations of the largest strict signed span.

A single constant word store to a fixed array can retain its byte
displacement in X and use the same counted tail. It handles both
strict and inclusive upper bounds, zero fills with `STZ`, and nonzero
patterns with `STA`. The source's empty-range and final-index
behavior are preserved. This replaces the indexed zero-fill loops
in `arctangent` and `calculate_pi`.

The final profile puts `accumulate` at 124,909,436 self clocks, down
from 135,854,262. `arctangent` drops from 2,532,446 to 2,289,630 self
clocks. Both 896-digit runs verified the full output and work.
The hand-written build retains its 18.201 s completed frame.
See `build/pi-c-optimization/fourth-pass-verified` and
`build/pi-c-optimization/fourth-pass-verified-profile/profile.json`.

The fourth-pass aggregate reached 26 of 27 suites. Its index-elimination
test found that the countdown attempted to load a cursor index whose
home had already been eliminated. Countdown and fill selection now defer
to an active cursor elimination for that index. The complete focused
index-elimination rerun passed, including the previously failing case
at 4,894 clocks with elimination and 6,696 clocks without it.
The aggregate report is `build/check/pi-c-fourth-pass/summary.json`.

## Loop-carried remainder bounds

The range pass interprets one unrestricted iteration of a structured
loop and joins the resulting private scalar facts with the entry facts.
For defined unsigned remainder operations, the result is smaller than
the nonzero divisor. In `divide`, the zero entry value and the range
of the byte divisor therefore prove that the carried remainder has a
zero high byte. Existing word-shift selection uses `XBA; LSR; LSR` in
place of six left shifts. The standalone arithmetic fixture checks
this sequence and verifies that a wide entry remainder keeps the
full-width shift. The retained build completed in 33.393 seconds at
715,907,486 kernel clocks in two matched runs. `divide` inclusive
time dropped from 509,175,546 to 497,275,896 master clocks.
The focused index-elimination, arithmetic-region, known-value and
byte-shuffle checks passed. See `build/pi-c-optimization/inductive-verified`
and `build/pi-c-optimization/inductive-verified-profile/profile.json`.

## Final comparison

The baseline and retained build use identical C translation units and
FastROM HiROM mapping. Power-on to the completed frame fell from 48.667
to 33.393 seconds, a 31.4% reduction. The kernel interval fell from
1,044,063,632 to 715,907,486 master clocks. Application code grew from
1,062 to 1,181 bytes and all linked code grew from 7,599 to 7,748 bytes,
as counted from the allocation manifests. The ROM container is 64 KiB
in both runs.

| Function | Baseline bytes | Retained bytes | Baseline self clocks | Retained self clocks |
| --- | ---: | ---: | ---: | ---: |
| `main` | 16 | 16 | 176 | 176 |
| `calculate_pi` | 281 | 299 | 91,468,832 | 80,797,566 |
| `arctangent` | 296 | 314 | 2,465,526 | 2,289,410 |
| `divide` | 217 | 270 | 490,200,568 | 470,110,864 |
| `accumulate` | 232 | 264 | 164,633,406 | 124,909,556 |
| `pi_emit` | 20 | 18 | 280,892 | 223,836 |

Self clocks exclude called routines. `divide` also removed repeated
helper calls, reducing its inclusive interval from 773,641,992 to
497,275,896 clocks. The display wrapper still uses the stock formatter.

The final cached `make check` passed all 27 suites and 817 jobs in
418.00 seconds with the hardware-thread default of 18 workers.
The aggregate report at `build/check/pi-c-final/summary.json` identifies
the same compiler hash as the matched 896-digit ROM allocation manifest.

## Word multiplication by a two-bit factor

The wide-divisor correction in `divide` multiplied a word quotient by a
factor already proven to be in `0..3`. Word code generation now uses that
bound on either operand to select zero, the original word, twice the
word, or twice the word plus the original. This avoids the mixed-width
multiply helper and preserves the low word of the product.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Before | 715,907,486 | 33.393 s | 1,181 bytes |
| Two-bit factor lowering | 692,060,738 | 32.278 s | 1,196 bytes |

Two runs per build verified all 898 characters, fixed-point state,
247,507 term-limb writes, VRAM, and the same screenshot hash. The ideal
assembly ROM was byte-identical. The arithmetic-region fixture exercised
all four factors in either operand position with a wrapping word
product and passed its six build modes. Matched artifacts are in
`build/pi-c-optimization/two-bit-multiply-baseline` and
`build/pi-c-optimization/two-bit-multiply-trial`.

The post-change profile attributes 473,491,068 self master clocks to
`divide`, across 1,884 calls, with no division or multiplication helper
calls from that function. The profile is in
`build/pi-c-optimization/two-bit-multiply-profile/profile.json`.

The multiply-only build tests the invariant scaled divisor against 256
for every limb. Counting the reference power lengths at 896 digits
gives 481,911 division steps. Of those, 384,975 use the direct byte
path and 96,936 use the scaled byte path. The largest odd divisor is
1,021, so this workload never takes the scaled word fallback.

The full cached check passed all 27 suites in 349.16 seconds. Its
report is `build/check/pi-two-bit-multiply/summary.json`.

## Versioning a loop on divisor width

For a small structured post-test loop with a paired unsigned division
and a private invariant divisor whose proven nonzero range straddles
256, the compiler emits a single dispatch before the loop. The byte
version uses the hardware divider directly and the word version uses
the existing helper. Both versions use the same C loop semantics and
divmod cache. The selector excludes writes to the divisor, volatile
accesses, and bodies with labels, nested loops or inlined call markers.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Two-bit multiply | 692,060,738 | 32.278 s | 1,196 bytes |
| Also dispatch once per loop | 676,431,974 | 31.546 s | 1,310 bytes |

Both retained runs verified 898 characters, the fixed-point state,
247,507 term-limb writes and identical VRAM and screenshot hashes.
The ideal assembly ROM stayed byte-identical. The arithmetic-region
fixture verifies both sides at 255, 256, 257 and 1,023, and checks
that a loop whose divisor crosses the boundary during execution
keeps per-iteration selection. It passed all six build modes.
The ROMs, generated assembly and logs are in
`build/pi-c-optimization/divisor-loop-version-verified`.
The function profile measures 457,967,368 self master clocks in
`divide`, down from 473,491,068, across the same 1,884 calls.
Both hardware loops still reload and store their source and destination
cursors on every limb. The two cursor addresses are private and advance
independently of the remainder and quotient.

The full check passed 26 of 27 suites. Its `priority4` part reached
the runner's 180-second timeout. The focused rerun on the same compiler
passed, with evidence in
`build/check/pi-divisor-loop-version/priority4-rerun.log`.

## Keeping two post-update word cursors in registers

The late register pass recognizes private direct-page word cursors
whose only uses in a single-entry loop are their marked post-update
transfers. It loads the source and destination cursors into X and Y
once and publishes their final values on exit. It checks incoming and
outgoing edges, register and flag liveness, and balanced stack depth.
While Y is saved, stack-relative operands outside the loop's own
pushes move by two bytes. Calls and other register uses prevent the
transformation. Loads and stores retain their original order, including
when source and destination overlap.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Divisor-width dispatch | 676,431,974 | 31.546 s | 1,310 bytes |
| Also retain both cursors | 619,813,848 | 28.917 s | 1,311 bytes |

The arithmetic-region regression checks a descending source, ascending
destination, overlapping data and both divisor paths. It also checks
that both cursor values are available after the loop. The benchmark
and emitted assembly are in
`build/pi-c-optimization/post-cursor-register-verified`.
The full check passed 26 of 27 suites. The callback ROM build exceeded
its 30-second timeout under the full run. The focused rerun passed on
the same compiler. See
`build/check/pi-post-cursor-register/callbacks-rerun.log`.

## Filling divider wait slots and forwarding saved results

The divider starts with a five-NOP wait before reading its remainder.
The scheduler can move an independent index increment or decrement
into a wait slot. Each step replaces one NOP with an instruction of
the same duration. The scan stops at branch targets, calls, other
hardware accesses and consumers of the step's flags. It also checks
for intervening uses or writes of the index.

A second pass forwards interleaved word copies between distinct private
workspace homes. The remainder can be copied while it is still in A,
and the quotient can stay in A after its store. The rewrite also
accepts an immediate or a nonoverlapping workspace load for the second
value. It allows the latched divider quotient only after the remainder
read from that operation.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Retained cursors | 619,813,848 | 28.917 s | 1,311 bytes |
| Schedule index steps during division | 607,876,170 | 28.351 s | 1,307 bytes |
| Also forward saved words | 585,607,592 | 27.319 s | 1,303 bytes |

The isolated runs reproduced each timing twice and verified the digit
stream, fixed-point state, term-limb writes and screen. The ideal ROM
was byte-identical. The per-trial builds and generated assembly are
under `build/pi-c-optimization/divider-wait-trial/build`.
The integrated compiler reproduced the final measurement in two
more runs under `build/pi-c-optimization/divider-schedule-verified`.
The arithmetic-region fixture passed all six modes, including the
divisor-255 edge and the emitted decrement sequence in the wait.
The full cached check passed all 27 suites in 338.96 seconds. Its
report is `build/check/pi-divider-schedule/summary.json`.

## Carrying a private word in A across the loop

The next trial stores the quotient before reading the hardware
remainder, after the same divider wait. The 16-bit quotient and
remainder stores use disjoint workspace homes, and the indexed output
transfer uses a private cursor. The pass checks that the old A and
N/Z values are dead after that transfer.

A separate loop pass seeds a private word load once before the loop
if the latch already carries that exact stored word in A. It checks
for alternate entries and reads of the load's flags, and validates
the instructions from the last store to the latch. Together the
passes remove one remainder load per iteration of the byte-divisor
loop.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Divider scheduling and forwarding | 585,607,592 | 27.319 s | 1,303 bytes |
| Also retain the carried word | 574,498,822 | 26.804 s | 1,303 bytes |

The isolated trial passed two matched runs, with identical verified
output, fixed-point state, work count and screen. See
`build/pi-c-optimization/divider-remainder-trial/build/verified`.
The integrated compiler reproduced both timings under
`build/pi-c-optimization/divider-remainder-verified`. The arithmetic
regression passed all six modes and verifies the final remainder and
cursor values after both divider paths.
The isolated profile attributes 356,299,740 self master clocks to
`divide` across 1,884 calls. The two loops still store some divider
results into workspace slots after their final use on the byte path.
The same slots can be live on the word path, so dropping those stores
requires control-flow-aware workspace liveness.

The carried-word snapshot's full run passed 26 of 27 suites.
`priority4` and `ieee64-runtime` timed out in the compiler suite.
Both focused reruns passed on the same compiler. The report and rerun
logs are in `build/check/pi-divider-remainder`.

## Removing dead divider-result stores

The late pass tracks reads and writes to the 32 arithmetic-workspace
bytes across branches and loop backedges. It removes a divider-result
store when none of its bytes are live after the store. Calls and
unmodelled instructions conservatively read the whole workspace, and
direct-page or data-bank changes disable the pass. The byte path can
drop three saves per limb because the quotient is written directly to
the destination and the remainder stays in A.

The scaled path also used to save the remainder and load it again
immediately after saving the quotient. The divider-result ordering
pass now recognizes that reload and reads the ready remainder after
saving the quotient. Workspace liveness then drops the remainder
save if no later read needs it.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Carry remainder in A | 574,498,822 | 26.804 s | 1,303 bytes |
| Drop dead divider-result saves | 541,133,284 | 25.256 s | 1,297 bytes |
| Also read the scaled remainder directly | 535,511,804 | 24.990 s | 1,293 bytes |
| Also load only the divisor byte | 531,522,326 | 24.807 s | 1,293 bytes |

Both isolated builds verified the digit stream, fixed-point state,
term-limb writes and screen in two matched runs. Their artifacts are
in `build/pi-c-optimization/divider-remainder-trial/build` under
`verified-workspace-liveness` and `verified-direct-remainder`.
The isolated arithmetic regression also passed all six modes. Its
assembly checks require the discarded temporary in one function and
the retained final-remainder store in another.

The final isolated variant moves the switch to A8 before the private
divisor load. The hardware trigger uses only the low byte. The fixed
wait does not read A, and the ready-result load overwrites the full
accumulator. Both 896-digit runs passed. The ROMs and generated
assembly are in `verified-narrow-divisor` alongside the other trials.
The main checkout reproduced the final timing in two runs under
`build/pi-c-optimization/divider-workspace-verified`. All six
arithmetic-region modes passed there.

## Sharing an index across an immediate expression

The indexed selector can combine one word array operand with an
immediate operation on another word at the same displacement. It
checks that both nonvolatile subscripts have the same scale and
expression, and that the outer operation commutes. It computes the
inner operation in A and uses the first indexed word as the final
operand. In `accumulate`, that lets the compiler XOR the term with
63 and add the indexed sum directly, saving a workspace spill.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Divider workspace changes | 531,522,326 | 24.807 s | 1,293 bytes |
| Also share the indexed displacement | 524,356,602 | 24.474 s | 1,286 bytes |

Two isolated runs agreed on the timings and verified the full
896-digit workload. See
`build/pi-c-optimization/divider-remainder-trial/build/verified-indexed-immediate-pair`.
Two runs of the integrated compiler reproduced the result in
`build/pi-c-optimization/indexed-immediate-pair-verified`. All six
arithmetic-region modes passed, with fixtures covering the complement
and both immediate-subtraction orders.
The cached full check passed all 27 suites in
`build/check/pi-workspace-indexed`.

## Removing spills around conditional corrections and narrow products

When a conditional update adds to an already saved word, the late pass
keeps that word in A and uses the other addend as the ADC operand. It
requires the branch and any intervening increment or decrement to
preserve A and the saved word. It also checks that the update has no
alternate entry. The workspace liveness pass now removes any dead
direct store to the arithmetic workspace, including the preceding save
when neither branch reads it. The arithmetic fixtures exercise taken,
bypassed and zero-result cases and check a loop that still uses the
original saved value after the conditional.

The two-bit word multiplication selector can also use the original
operands when both have direct, nonvolatile addresses. The factor test
uses the original factor home, and the loads and add use the original
word home. The existing staged path still handles computed operands.
The arithmetic fixtures check both operand orders, all four factor
values and word wraparound.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Share the indexed displacement | 524,356,602 | 24.474 s | 1,286 bytes |
| Also keep the conditional addend in A | 521,149,150 | 24.324 s | 1,280 bytes |
| Also remove other dead workspace stores | 521,017,832 | 24.308 s | 1,272 bytes |
| Also use direct operands for two-bit multiplication | 515,411,468 | 24.058 s | 1,264 bytes |

Each isolated variant passed two matched 896-digit runs. The evidence is
under `build/pi-c-optimization/divider-remainder-trial/build` in
`verified-conditional-word`, `verified-general-workspace-dse` and
`verified-direct-small-factor`. The spill-removal variants left the
assembled sizes of the calculator, prompt, integer operations and
Dhrystone translation units unchanged in `workspace-corpus/sizes.json`.
The integrated spill-removal compiler passed all 27 suites in
`build/check/pi-conditional-workspace`. The integrated direct-operand
build reproduced the two matched runs in
`build/pi-c-optimization/direct-small-factor-verified`.
Its full check passed 26 of 27 suites. A stage-3 source-LTO ROM build
timed out in the compiler suite. The same compiler passed that build
and the remaining source-LTO cases on replay. See
`build/check/pi-direct-small-factor/source-lto-resume.log`.

The direct-operand profile records 304,491,348 self master clocks in
`divide` across 1,884 calls and 117,780,966 in `accumulate` across 968
calls.

## Forwarding shifts and scheduling a divider mask

A word already in A can be shifted before loading the other shifted
input to a commutative logical operation. This removes the reload of
the first word. The reorder requires the scratch result and carry to be
dead after the join, and the moved scratch store to leave the other
input intact.

When the hardware divider has three spare NOPs, the late scheduler can
use them to load and mask a private word for a later merge with the
remainder. It checks that any intervening quotient saves leave both
workspace values alone and that any index steps leave a register input
unchanged. The replacements meet the original hardware wait, and the
remainder stays in A through the final merge.

| FastROM C build | Kernel master clocks | Power-on to completed display | Application code |
| --- | ---: | ---: | ---: |
| Direct operands for two-bit multiplication | 515,411,468 | 24.058 s | 1,264 bytes |
| Also forward the shifted input | 512,604,246 | 23.925 s | 1,257 bytes |
| Also schedule the divider mask | 509,001,686 | 23.759 s | 1,254 bytes |

The isolated results reproduced in two 896-digit runs each, with
verified digits, state, work count and display. See
`verified-shift-forwarded` and `verified-wait-mask` under
`build/pi-c-optimization/divider-remainder-trial/build`. The arithmetic
fixture checks the shifted result and original unshifted input, and
checks the scheduled divider's quotient and remainder with separate
and in-place buffers. All six isolated arithmetic-region modes passed.
The integrated build reproduced the timings and both ROM hashes in
`build/pi-c-optimization/divider-wait-mask-verified`.
The cached full check passed all 27 suites in
`build/check/pi-divider-wait-mask`.
The calculator, prompt, integer operations and Dhrystone translation
units had byte-identical emitted assembly across these last two passes.

In the matched profiles, compiled division used 298,095,800 self master
clocks across 1,884 calls. The three assembly division routines used
270,382,800 across the same number of calls. Compiled `arctangent` and
`accumulate` together used 120,003,916 self clocks, compared with
52,342,678 for assembly `arctangent`, which includes accumulation.
The compiled inner loop still materializes the carry in a word and
shifts it six times per limb. The assembly loop keeps carry in the
processor flag, using the input limbs' radix-64 bounds. Profiles are in
`build/pi-c-optimization/divider-wait-mask-profiles`.

## Reproduction

```text
python tests/check-compiler.py --part arithmetic-regions
```

The run directories retain the assembly, allocation maps, compiler and
runtime input hashes, verification logs and screenshots. The function profiles
are in `build/pi-c-optimization/baseline-profile/profile.json` and
`build/pi-c-optimization/first-pass-verified-profile/profile.json`.
