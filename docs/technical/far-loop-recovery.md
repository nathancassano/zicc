# Far loop recovery

After near memory moved to bank `$7E`, passing a pointer to a ROM string or table made some loops recalculate a four-byte address on every pass. The compiler can now keep a running address for the supported loops, even when the data crosses a bank boundary. The earlier register, shared-element, and counted-sum rules had accepted only near pointers.

## Selection and ownership

`src/far_loops.inc` consumes the byte-loop IR from `register_loops.inc`.
Eligible leaf functions keep up to two private byte cursors at $E0-$E7. The
region stays in A8 and supports loads/stores, constant byte arithmetic,
prefix/postfix unit steps, short-circuit byte predicates, counted loops and
byte temporaries. It recovers affine word results from the cursor distance and
retains eligible final constant byte stores. Mixed near/far parameters follow
the existing register/stack ABI. Near cursors retain their bank; far cursors
carry/borrow through all 24 address bits. Reads and writes remain byte accesses.

The function saves each occupied DP word on entry and restores it on exit;
Y is also preserved. No pointer frame homes or per-iteration scalar counters
are needed. The region contains no calls. Escaping pointers, unsupported side
effects, mixed signed/unsigned byte comparisons and unsupported control flow
retain the general emitter. Existing near loop backends retain their selectors
and X/Y addressing.

`counted_reductions.inc` retains its narrow, previously verified reduction
grammar: signed word field widened to unsigned long, multiplied by an unsigned
long field, accumulated over a signed count. Its far backend keeps one cursor
at $F0-$F3, advances it once per record, guards nonpositive counts and uses the
existing `__mul16x32` helper. The cursor lives outside that helper's $E0-$EB
workspace and is locally saved/restored. Field offsets use long-indirect,Y,
including a field or record crossing a bank boundary.

Expression-local shared-member lowering now computes a pure far structure
address once at $F8-$FB, then uses field displacements for both operands.
Those words are transient compiler scratch, covered by the existing selective
interrupt preservation. Calls, mutations and unequal addresses remain barriers.

## Validation

`tests/check-far-loops.py` builds identical drivers and kernels as separate
translation units. Optimized and disabled-loop variants run on NTSC and PAL.
Cases cover empty/599-byte strings, source/destination overlap, both directions
across bank boundaries, unsigned bytes above 127, mixed-sign fallback, preserved
byte temporaries, affine counter results, zero/negative counts, negative fields,
non-power-of-two record strides and negative indices into shared members.
`--baseline PATH` also executes an optional saved compiler of the same ABI.
The normal `make check` compiler suite includes these checks and the library
NTSC/PAL checks.

## Measurements

The baseline already includes the four assembly library additions and
before these optimizer edits. Both stages use FastROM, DBR=$7E, the same pointer
ABI and application/runtime sources. Runtime C is built with each stage's
compiler; saved baseline binaries are never mixed with candidate objects. Measurements use the existing execution-checked sample
harness, including original and separate-driver/kernel forms without LTO, with
two matching repetitions per build. Calls, actual loop work, inputs, results and
hardware multiplication counts are asserted. These are complete sample master
clocks including setup, calls and returns, not isolated instruction timings.

| Sample | Form | Before clocks | After clocks | Change | Code bytes before / after |
|---|---|---:|---:|---:|---:|
| minimal | original | 18560 | 18560 | +0.00% | 94 / 94 |
| minimal | runtime | 18560 | 18560 | +0.00% | 104 / 104 |
| prompt | original | 374578 | 374578 | +0.00% | 2114 / 2114 |
| prompt | runtime | 374646 | 374646 | +0.00% | 2124 / 2124 |
| calc | original | 644700 | 644700 | +0.00% | 15162 / 15079 |
| calc | runtime | 644700 | 644700 | +0.00% | 15162 / 15079 |
| insertion_sort | original | 30008 | 30008 | +0.00% | 518 / 518 |
| insertion_sort | runtime | 30008 | 30008 | +0.00% | 518 / 518 |
| string_processing | original | 86932 | 24174 | -72.19% | 980 / 727 |
| string_processing | runtime | 86932 | 24174 | -72.19% | 980 / 727 |
| integer_operations | original | 26642 | 26642 | +0.00% | 2077 / 2077 |
| integer_operations | runtime | 45762 | 45762 | +0.00% | 2183 / 2183 |
| function_calls | original | 104656 | 104656 | +0.00% | 1902 / 1902 |
| function_calls | runtime | 104656 | 104656 | +0.00% | 1902 / 1902 |
| structures_and_tables | original | 31166 | 16554 | -46.88% | 2140 / 1972 |
| structures_and_tables | runtime | 31166 | 16554 | -46.88% | 2140 / 1972 |

Code bytes are STARTUP+CODE. All image files remain 32768 bytes. String used ROM
falls from 1083 to 830 bytes; structure used ROM falls from 2228 to 2060 bytes.
The other six sample timings are unchanged. Rebuilding decimal.c selects the
far byte loop for dec_copy and removes 83 code bytes from both calculator forms;
the other five sample sizes are unchanged. Strings take 72.2% less
time; the structure sample takes 46.9% less. These do not fully recover the older
near-only ABI's timings: far addressing, bank carry/borrow, scratch saves and
stack-passed far parameters still cost work.

Baseline inputs, source snapshot, assembly, maps, ROMs and measurements are in
`build/far-loop-recovery/baseline/` and `baseline-sources.zip`. Final measurements
are in `build/far-loop-recovery/final/candidate/`; `inputs.json` records the exact
compiler/runtime/source hashes. The initial trial is retained under `candidate/`.
Full generated assembly is retained for every sample and both differential
kernel variants in `build/far-loop-check/`. Individual worker logs retain any
emulator timeout and subsequent isolated retry evidence.

`make check` passed all 27 suites / 76 jobs at the hardware-thread default of
20 workers in 322.34 seconds, preserving all 200873 arithmetic cases. Evidence:
`build/check/20261106T184502.306844Z/summary.json`. Compiler SHA256:
`bb79230770dfb2ca077a6d26ba166cf54ce73d074bbdd52346834040e486daf9`.
The separate-unit kernels also pass on NTSC and PAL with the saved prechange
compiler (`build/far-loop-recovery/baseline-*.exe`).

Dhrystone now compiles, assembles and links against the real library archive.
The build copies include `<stdlib.h>`/`<string.h>` and remove the obsolete
`char *malloc()` declaration; the untracked sample originals are untouched.
Evidence is in `build/far-loop-recovery/dhrystone/`. This is a link check, not a
benchmark result: Dhrystone still needs explicit NMI enabling, region-aware
clock-rate integration and supported formatted output before a timing run.

