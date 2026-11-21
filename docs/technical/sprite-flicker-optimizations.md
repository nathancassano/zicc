# General compiler optimizations from the sprite flicker investigation

The compiler gained seven ways to shorten code like Dragon's sprite updates. For example, it can divide by four without calling the general divider and can combine two scans when doing so leaves the reads and writes in the same effective order.

Implemented on 2026-11-11. All seven gaps in the
[original investigation](sprite-flicker-codegen-investigation.md) now have
general compiler support. Dragon's C and assembly sources are unchanged.
Selection uses types, expression structure, object bounds, memory effects and
existing code-growth budgets; it does not recognize game symbols or pool sizes.

## Implementation

| Gap | General implementation |
| --- | --- |
| Constant power-of-two division and remainder | `src/codegen/word_shifts.inc` selects native operations for signed/unsigned 16-bit and 32-bit values, including negative divisors. Signed division truncates toward zero; remainders retain the dividend's sign. `src/codegen/divmod.inc` leaves these expressions available to the selector instead of forcing a cached helper call. Compound assignments and pointer differences share the loaded-operand path. |
| Word shifts widened to a long helper | Runtime shifts with a promoted word result use a native word loop. A constant shifted by a small bounded mask/modulo expression becomes a byte/word ROM lookup. Byte projections can use an A8 lookup directly. `src/codegen/wide.inc` lets these expressions reach the word selector. |
| Discarded increments retain the old value | Statements, comma operands and `for` steps share `discarded_direct_increment` in `src/codegen/codegen.inc`. Mapped/global word homes use memory updates where available; other homes use load/update/store. Value-producing postincrements still preserve their old result. |
| Address reuse stops at loops and guards | `src/codegen/body_opt.inc` visits structured regions recursively. Linear addresses remain visible to induction/register planners; nonlinear repeated addresses can share a pointer inside a straight-line region. Range facts precede normalization, and unsigned subscript wrap must be excluded before moving a constant into an outer pointer add. Adjacent-store matching accounts for folded offsets. |
| Runtime conditional multi-array loops use generic emission | `src/codegen/byte_loop_regions.inc` keeps a word induction view in X/Y, optionally retains a second scaled view, and stays in A8 across eligible byte work and unsigned loop control. It handles conditional stores, gathers/scatters, backup-count updates, signed byte predicates, signed word bounds and sentinel loops. Private index homes remain synchronized for other expression emitters. Equivalent `while` tails with `i++` or `i += 1` can use the same planner. |
| Small copies remain byte loops | Fixed nonoverlapping copies of 2 through the existing full-unroll limit become word pairs plus an optional byte tail. Both object extents and offsets are checked, and a live final index is recovered. No particular copy length is recognized. |
| A small helper and its caller scan the same range twice | `src/codegen/loop_fusion.inc` proves that adjacent traversals commute before fusing them. Named objects and byte subranges describe their effects. A compatible static void helper can be inlined under the existing growth budget to expose the traversal. Identical guards are shared only when their observations are unchanged. |

Constant-branch folding also sees immediate comparisons through index-register
setup that leaves A unchanged. Complete external array declarations participate
in the same indexed-address selection as definitions.

The cheaper discarded update changes countdown profitability. A maintained C
index followed by a cheap immediate comparison should not also maintain a
second counter in memory. DP-counter selection now recognizes that case. The
semantic loop-shape check is separate from this cost decision: full unrolling
and entry-only cursor leaves do not require a profitable runtime countdown.
The existing DP benchmark again improves in every kernel; nested columns use
932 rather than 967 CPU cycles with countdown selection enabled.

The conservative paths remain available. Unknown pointer aliases, volatile
observations, calls or exits in a byte region, changing bounds, dependent
traversals, overlapping copies, narrowing indices and unproved wrap retain
ordinary emission. Fusion rejects counter-dependent starts/bounds, exposed
counters and cross-iteration memory dependencies. The width and register
planners retain the ABI's A16/X16, stack, Y, D and DBR contracts.

## Matched FastROM measurements

The baseline is the frozen production ROM from the investigation, not the
archived handwritten assembly. Both ROMs have identical game C/assembly source
hashes, identical generated RAM initialization bytes and the same HiROM memory
mapping. Both are 256 KiB. Two fresh full fixture runs were made per ROM:
832 samples and 106,496 slot checks for each build, alternating both phases.
Each run also checks high-table contents and capacity for 128 backups.

Times run from function entry through caller resumption, including return but
excluding call. Prepare includes its callees. Refresh stalls and interrupts are
included; upload/wait is excluded. Percentages use 357366 master clocks per NTSC
frame. Means below include prepare plus restore; percentages are maxima.

| Case | Baseline mean clocks | Optimized mean clocks | Mean reduction | Baseline frame max | Optimized frame max |
| --- | ---: | ---: | ---: | ---: | ---: |
| inactive_full | 639 | 577 | 9.70% | 0.19% | 0.17% |
| full_probe | 890 | 832 | 6.54% | 0.25% | 0.24% |
| probe_recovery | 910 | 853 | 6.26% | 0.26% | 0.24% |
| active_empty | 6431 | 3434 | 46.60% | 1.80% | 0.96% |
| active_sparse | 37928 | 13866 | 63.44% | 10.98% | 3.98% |
| fireballs_full | 69759 | 29802 | 57.28% | 19.53% | 8.34% |
| explosions_full | 69760 | 29790 | 57.30% | 19.53% | 8.34% |
| sorted_full | 221810 | 63565 | 71.34% | 62.07% | 17.79% |
| items_full | 39194 | 17020 | 56.58% | 10.97% | 4.77% |
| all_full_mixed | 188382 | 62744 | 66.69% | 52.86% | 17.62% |
| all_full_kept | 92992 | 29474 | 68.31% | 26.03% | 8.25% |
| all_full_player | 92994 | 29480 | 68.30% | 26.03% | 8.25% |
| all_full_hidden | 376138 | 128010 | 65.97% | 105.26% | 35.84% |

All 64 baseline all-hidden samples were interrupted; no optimized sample was
interrupted. All-hidden remains a capacity stress input rather than a balanced
A/B distribution. These are synthetic function measurements, not gameplay
averages or whole-game frame rates. The archived assembly was not benchmarked.

An additional instrumented full run asserts executed work rather than inferring
it from correct output alone. For full pools the old ROM executes 128 group
tests in the small helper plus another 48 in the sorted helper. The optimized
ROM executes 80 fixed-pool tests plus 48 fused sorted tests. Every live entry
still receives its required test. All 416 helper/scan-count assertions pass.
The optimized prepare executes zero `__sdiv16`, `__udiv16` and `__shl32` calls,
including the full 48-entry hidden sorted case.

Fresh default compilation matches all four linked flicker function instruction
streams after the normal builder width pass. Static instruction counts for
small/sorted/restore change from 72/71/43 to 37/58/38. Prepare grows from 147 to
151 instructions while executing less work, including its widened copies.

Final compiler SHA-256:
`d22831e360c9a9477fe65c07223c5290837b86ac7d1dcd29c43330c79ee13cae`.

Final ROM SHA-256:
`1e4e65115fd348282b21cf8d64c376423f3451b8f3abfbb858d19ac0f8e489b0`.

Baseline ROM SHA-256:
`d1cbbddb7ebba611483ad80f797c79c2b8971ecfe2e69ac50329f67908c07962`.

## Verification and evidence

The new checks are registered as compiler parts, so normal `make check` includes
them:

- `tests/check-integer-lowering.py`: 94 word kernels, 190 long kernels and six
  shift kernels, with 43 deterministic opaque vectors. Separate drivers and
  kernels prevent whole-program folding. Both optimized and fallback modes
  verify exact calls/results and ABI preservation: 4,040 word, 8,168 long and
  258 shift calls per mode. Signed minimum divided by minus one is excluded
  because that operation has undefined behavior.
- `tests/check-structured-byte-loops.py`: renamed arrays, a different high-table
  layout/divisor, 32 variable ranges, 256-entry backup/restore capacity, a
  13-byte copy, `for`/`while`/sentinel spellings, signed ranges, global/comma
  steps, live postincrement results, and all six signed byte relations over
  65,536 operand pairs. Negative cases exercise aliasing, overlap, volatile
  accesses, changing bounds/predicates, counter-dependent starts and dependent
  loops. Host and target results agree in optimized and fallback modes.

`make all smoke` and a full `make check` were run with the hardware-thread
worker limit (20). The full run retained all 200,873 arithmetic cases and
finished every queued job. Integration failures were repaired with focused
reruns, retaining unaffected passes as required by the project workflow.
Further loop/array/structure coverage and 16 compiler parts passed. The final
entry-only cursor fix was checked by rerunning the two affected frame workers
and the complete unroll setup, four NTSC/PAL ownership workers and collector.
The final structured-byte check passed again. All observed failures were
resolved; retained passing results keep their original compiler hashes.

Evidence is retained in:

- `build/check/20261110T170901.681474Z/`: initial full verification and all logs.
- `build/flicker-integration-final/`: address/loop repairs, semantic checks and
  the DP-counter benchmark investigation.
- `build/check/flicker-final-affected/`: affected suites, all eight DP-counter
  ownership workers and collector, and retained passing frame workers.
- `build/flicker-final-compiler-parts/`: the 16 focused compiler parts.
- `build/flicker-final-resume/`: final frame workers, unroll setup/ownership/
  collection and final structured-byte results.
- `build/flicker-opt-verified/`: final FastROM, allocation/build evidence and
  all seven successful title checks. The unchanged host fixture also passes
  2,048 variable-pool round trips and sticky probe/recovery checks.
- `build/flicker-verified-audit/`: source snapshots, selected assembly, disabled
  controls, probes, frozen ROM/symbols, generated Lua and executed scan counts.
- `build/flicker-verified-comparison/`: two raw timing runs per ROM, frozen
  inputs, source/compiler/emulator hashes and comparison JSON/Markdown.

The original baseline evidence remains in
`build/flicker-codegen-20261111-complete/`.

## Reproduction

From the compiler checkout, build an isolated normal Dragon FastROM and audit
it without writing to Dragon's source checkout:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
python -B D:/dev/dragon/tools/build_zicc.py --compiler-root C:/bin/zicc --build-dir C:/bin/zicc/build/flicker-repro --output C:/bin/zicc/build/flicker-repro/dragon.sfc
python tests/check-compiler.py --part integer-lowering
python tests/check-compiler.py --part structured-byte-loops
```

Each audit/comparison output must be a fresh directory. The local baseline
audit and frozen ROM are required for a historical timing comparison. The
comparison script checks source hashes (including generated initialization),
mapping, ROM identity and repeated correctness results before reporting timings.
