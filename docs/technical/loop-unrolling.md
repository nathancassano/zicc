# Cost-based affine loop unrolling

Unrolling lets one trip around a loop do several iterations' work before
checking the counter again. It trades extra instructions in ROM for fewer
checks at runtime. The planner in `src/loop_unroll.inc` estimates the cost
from the types, address step, counter, value being stored and number of
iterations. It works across function names and array sizes.

The initial supported region is one affine element assignment in an ascending
unit-step word-index `for` loop. Values may be literals, scalar homes or simple
numeric casts. Byte, word, long and floating-point bit copies are supported.
Calls, conditional exits, negative address strides, unsupported value expressions
and other loop forms retain their existing lowering. Whole multidimensional
nests are not flattened: the innermost eligible region is selected independently.

## Cost policy

Candidates include the current rolled form, factors 2/4/8/16, and the entire
constant span when it is at most 32 iterations. The model charges value loads,
stores, visible index updates, pointer advances, countdowns, width switches,
split/remainder handling and borrowing overhead. Costs are estimated SNES master
clocks for FastROM instructions and WRAM data, excluding common ABI/affine setup.
They are not cycle-exact predictions.

Runtime spans use a 32-iteration planning estimate. Partial candidates need at
least a five-percent estimated runtime saving. The score adds two clocks per
estimated code byte and compares that score against the rolled candidate.
Expanded-region estimates are capped at 128 bytes. The verifier also records
actual function sizes and checks growth for the fixtures. Scalar bodies with
more than four nested casts retain ordinary lowering.

A known short span emits fixed-displacement stores and removes its counter,
branches and pointer updates. It does not borrow $00. Private, non-escaped
invariant values are loaded once; global or escaped values are reloaded at each
logical assignment. Index-valued expressions retain per-element index updates.
Visible final indices and function cursors are recovered/synchronized at exit.

Runtime candidates first retain the original entry guard. After borrowing $00,
counts smaller than the group size go directly to a scalar path. Other counts
split into a power-of-two group count and remainder. The remainder occupies one
temporary stack word while $00 holds the group count. Groups issue ordered
stores at fixed offsets, advance X once and decrement the group counter. The
scalar tail writes exactly the remaining elements. Tail values can stay in A
when proven invariant and the pointer advance preserves A.

Each partial region restores its incoming $00 word locally. The grouped path
uses four stack bytes for the saved word and remainder; wide-value staging
temporarily saves X as well. Byte store regions restore A16 before word counter
operations or exit. Wide staging uses the existing arithmetic workspace and
selective handler preservation. The runtime, linker and register ABI are unchanged.
`--no-loop-unroll` disables expansion; shared address arithmetic optimizations
still apply. See [address setup](loop-address-setup.md) for the later setup work.
Disabling register loops,
strength reduction or DP counters also prevents this selector from running.

## Verification and measurements

`tests/check-loop-unroll.py` runs the same semantics fixture with the selector
enabled and disabled and checks an independent MSVC reference. At the original
unrolling change, disabled assembly matched the saved compiler byte for byte;
later shared instruction selection intentionally changes that output. Historical
assembly equality is no longer a condition of the current semantic checks.
Coverage includes every word
and byte remainder at counts 0-65, dynamic columns at counts 0-80, wide/float
copies, group counts exceeding 255, full spans 0/1/2/3/5/8/32, the 33-iteration
partial boundary, negative/nonzero starts, unsigned indices near 65535, visible
indices, global reloads and conservative fallbacks. Actual function sizes and
source/compiler/runtime/ROM hashes are retained.

Separate opaque assignment kernels and drivers assert arguments, call counts,
write counts, complete array contents and final indices. Three emulator runs
reproduce every recorded sample. Real NTSC/PAL interrupts exercise byte and wide
unrolled stores in handlers with all four M/X entry widths, while checking the
caller counter, registers, stack and arithmetic-workspace sentinels. The new
checks run sequentially in the existing strength suite and shared queue.

Complete-call master clocks, including setup and return:

| Traversal | Previous DP-counter version | Unrolled |
|---|---:|---:|
| Across row | 2876 | 1998 |
| Down column | 1910 | 1086-1126 |
| Nested rows | 6438-6478 | 3764 |
| Nested columns | 9096-9136 | 5256-5296 |

For the opaque runtime row kernel, selected samples are:

| Elements | Previous | Unrolled/grouped |
|---:|---:|---:|
| 0 | 620 | 592 |
| 1 | 1514 | 1556 |
| 2 | 1686 | 1688 |
| 3 | 1898 | 1820 |
| 15 | 3962 | 3484 |
| 16 | 4174 | 2450 |
| 17 | 4346 | 2610 |
| 32 | 7006 | 3252 |
| 33 | 7218 | 3412 |
| 64 | 12710 | 4936 |
| 65 | 12882 | 5096 |

Runtime trip counts are unknown during selection, so the one-time dispatch can
regress tiny calls; the one-element sample costs 42 extra clocks. Constant short
spans avoid that dispatch through full unrolling. Refresh-phase variation is
retained in the raw samples. These are complete kernel timings, not per-store
throughput claims.

Evidence: `build/loop-unroll-check/results.json`, `assembly.md`, separate C and
assembly, maps/debug labels, ROMs, Lua execution assertions and raw logs. The
pre-change executable and input manifest are in `build/loop-unroll-change/`.
The older DP-counter benchmark explicitly disables unrolling to isolate its
original optimization and preserve its historical comparison.

Final `make check` passed 27/27 suites / 76 jobs in 283.09 seconds with the
hardware-thread default of 20 workers and all 200,873 arithmetic cases. Logs:
`build/check/20261106T145221.059361Z/`. The new checks run inside the existing
strength job; no queue or coverage changes were made.

Linked function sizes for those same opaque kernels are 119 to 100 bytes (row),
115 to 83 (column), 163 to 144 (nested rows) and 159 to 127 (nested columns).
The runtime row kernel grows from 112 to 198 bytes; its larger grouped body is
part of the time/size tradeoff represented by the selector.
