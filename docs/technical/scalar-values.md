# Private scalar values and frames

A local variable that only copies another value may need no stack space. When the compiler proves that the original value stays the same, it can use that value everywhere the copy would have been read.

The subsequent [computed-store extension](computed-stores.md) also forwards
single-use word computations and supports stack arguments and near indirect
stores without a Y frame. The measurements below retain the first-stage
comparison; that extension documents the updated Dhrystone results.

`src/scalar_values.inc` propagates a dominating prefix of plain local copies
and constant initializers. Copies may include casts, including K&R default
argument promotion followed by a conversion back to the declared character
type. Each destination must have exactly one write and no address escape.
Object sources must be private, immutable throughout the function, unescaped
and nonvolatile. Global loads, mutable sources, non-prefix definitions and
other expressions keep their existing lowering. Replacements extend through
branches and loops because the prefix dominates them and the source cannot
change. Removed homes are compacted before cursor and frame planning.

Character values already extended to their declared signedness need no second
identical conversion. Equality of two equally signed character values, including
their ordinary signed-int promotions, compares the low bytes directly. This
selection accepts only object/constant sources through word/character casts;
mixed signedness, volatile accesses and other expressions retain word lowering.
It restores A16 before branching, preserving the comparison's flags.

General scalar leaves can use ordinary expressions, conditionals, returns and
plain global stores without allocating a Y frame. The region must have no live
local homes, calls, indirect accesses, loops, helpers, volatile accesses or
parameter writes/escapes. It accepts up to two word/character parameters, keeps
the first in X, and spills the second to the invocation's stack only if used.
Every return removes that spill. Existing arithmetic and loop selectors keep
priority. Unsupported functions retain the ordinary ABI and frame lowering.

There are no persistent direct-page parameter homes. Interrupts preserve the
live X/A/status state through the existing prologue and epilogue, while the
second argument belongs to the interrupted invocation's stack. Temporary pushes
are included in stack-relative comparison offsets. Recursive/calling functions
retain their normal private homes.

`tests/check-scalar-values.py` is part of `make check`. It covers every byte
value, high-byte aliases, both comparison paths and the global store, signed
extension and mixed signedness, word-to-byte-to-long conversions, arithmetic
and boolean branches, source mutation, escaped addresses, recursion, stack
arguments, loop and branch fallbacks, and volatile snapshots. NTSC and PAL runs
require actual IRQ/NMI delivery inside the leaf and verify registers, status,
stack and all arithmetic workspace words at interrupt return. Instrumented
assembly additionally inserts BRK and COP before every instruction in the
comparison leaf, including its byte-mode comparison and both returns.

For a baseline comparison:

```text
python tests/check-scalar-values.py --baseline <saved-zicc.exe>
make check
```

The baseline runs the same C semantic and hardware-interrupt workload. Software
trap instrumentation is a separate optimized-assembly check, not a throughput
measurement. Results, ROM hashes and emulator logs are retained under
`build/scalar-value-check/`.

## Dhrystone comparison

For 3,000 runs on PAL, with normal interrupts included, repeated profiles gave
identical master-clock totals:

| Build | Before | After | Reduction |
|---|---:|---:|---:|
| zicc FastROM | 110,593,642 | 101,612,020 | 8.12% |
| zicc SlowROM | 128,643,580 | 118,154,040 | 8.15% |

The displayed FastROM reports changed from 580 to 631 Dhrystones/sec on NTSC
and from 576 to 627 on PAL. Frame-clock quantization affects those printed
integer rates; master-clock measurements above provide the precise comparison.
`Func_1` fell from 106 to 31 bytes and from 1,100.37 to 212.25 master clocks per
FastROM call (1,285.46 to 243.23 for SlowROM). It still executes 9,000 calls.
`Func_3` fell from 28 to 14 bytes and `Proc_5` from 26 to 23; the total CODE
segment shrank 92 bytes. The padded ROM remains 32,768 bytes.

Source hashes, linked runtime hashes, function/loop counts, array and global
write counts, record contents, block moves and hardware arithmetic operation
counts match the retained baseline. Both Dhrystone translation units remain
separate, without LTO. These measurements compare normal optimized Dhrystone
builds, not an opaque-driver arithmetic-throughput experiment. The earlier VBCC
SlowROM build remains 87,294,056 master clocks; its inlining, ABI and runtime
differ from zicc.

Raw repeated profiles, assembly, compiler/runtime/source hashes and native
NTSC/PAL console/screenshots are retained in `build/scalar-propagation-trial/`.
The baseline is retained in `build/dhrystone-flow/`.

Final verification: `make check
CHECK_OUTPUT=build/scalar-propagation-trial/full-check-verified` passed all
27 suites / 76 jobs with the hardware-thread default of 20 workers, preserving
all 200,873 arithmetic cases. The complete frame suite also passed separately.
NTSC/PAL console reports repeated identically in fresh emulator processes.
