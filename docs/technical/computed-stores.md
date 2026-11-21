# Computed temporaries and scalar stores

A calculation such as `t = a + b` can go straight into the next statement that uses `t`. The compiler can skip storing `t` when no one else can read it and moving the calculation preserves its inputs.

The private-value pass forwards a computed word temporary only when it has one
definition and one use, its operands are immutable unescaped private values or
constants, and the next executable statement consumes it. Declaration blocks
are transparent. Supported calculations are basic word arithmetic, bitwise
operations, unary sign/complement and casts. Conversions remain in the tree,
including character truncation and extension. Calls, intervening statements,
mutable or global operands, escaped temporaries, multiple uses and loop
consumers retain their original homes. Copies keep the existing broader rules.

The word expression planner now also lowers a complete plain scalar store
through an immutable near-pointer parameter. The pointer may occupy any of the
eight public argument positions. Numeric inputs stay in their incoming X/A or
stack locations; arithmetic scratch is transient. A pointer received in X stays
there while the calculation runs. A pointer received in A is saved on the
invocation stack. A stacked pointer is fetched after computing the result,
with a temporary push protecting that result. No Y frame is allocated. The
function may fall through or explicitly return zero/void; other return values
use ordinary scalar-leaf lowering. There is no inlining or ABI change.

More general scalar leaves accept up to eight word/character/near-pointer
parameters and near indirect reads/stores, including conditional stores. They
spill only referenced incoming register arguments to invocation-owned stack
homes when X is needed for addresses. Stack arguments remain in place; all
temporary pushes are included in their offsets. Calls, wide/far values,
volatile accesses, parameter mutation/escape, loops, members and unsupported
expressions keep ordinary lowering.

The X-preservation proof for plain indirect stores now accepts recursively
composed word addition, subtraction, bitwise operations, unary sign/complement
and casts whose inputs also preserve X. These selected operations cannot call
helpers or change X. Indirect loads, calls, wide/far conversions and unsupported
expressions retain the pointer save. This applies to framed functions too.

No persistent scratch homes are introduced. The existing interrupt prologue
preserves registers/status and selectively preserves written arithmetic
workspace; live parameter/result spills belong to the interrupted invocation.

## Validation

`tests/check-scalar-values.py` compares the same C workload with the saved
compiler and validates NTSC and PAL. It covers pointer arguments in X, A and
the first/last stack positions; computed and narrowed values; conditional
stores; aliased reads/writes; calls; mutation; multiple uses; loops and global
snapshots. It checks that the framed arithmetic store loses its redundant X
save and that a store whose RHS dereferences a pointer retains preservation.
Real IRQ/NMI delivery must occur inside both comparison and computed-store
leaves. Separate assembly instrumentation inserts BRK and COP before every
instruction in both leaves, checking all registers, status, stack and all
sixteen workspace words at interrupt return. Hardware and software checks run
in both regions. The original ABI/frame/expression suites remain enabled.

## Dhrystone

Three thousand iterations, PAL, normal interrupts included. Both complete
profiles repeat identically in independent emulator processes. Sources and
all linked runtime hashes match the pre-change baseline.

| Measurement | Before | After |
|---|---:|---:|
| FastROM total master clocks | 101,612,020 | 97,164,940 |
| SlowROM total master clocks | 118,154,040 | 112,987,016 |
| Proc_7 FastROM master clocks/call | 797.51 | 325.60 |
| Proc_7 SlowROM master clocks/call | 921.12 | 370.92 |
| Proc_7 instructions | 32 | 13 |
| Proc_7 bytes | 60 | 22 |

Total clock reductions are 4.38% FastROM and 4.37% SlowROM. Proc_7 still executes
9,000 calls. Proc_2 also loses a redundant X push/pop pair. Total CODE shrinks
40 bytes; the padded ROM remains 32 KiB. All call, loop, record/array update,
block move and hardware arithmetic assertions match the baseline.

Printed throughput changes from 631 to 661 Dhrystones/sec on NTSC and from
627 to 655 on PAL. Updated reports are 272 ticks at 60 Hz (4,533 ms) and 229
ticks at 50 Hz (4,580 ms), repeated identically with final-screen validation.
These are normal optimized Dhrystone builds in separate translation units,
not an opaque-driver kernel-throughput experiment. The retained VBCC release
SlowROM build remains 87,294,056 total clocks and 358.56 clocks per Proc_7 call;
its pointer ABI, packed record layout, inlining and runtime scope differ.

Evidence, assembly, repeated profiles, hashes and native screenshots/reports
are under `build/computed-store-trial/`; the baseline is in
`build/scalar-propagation-trial/` and the release VBCC reference in
`build/dhrystone-flow/vbcc/`.

`make check CHECK_OUTPUT=build/computed-store-trial/full-check` passed all
27 suites / 76 jobs with the hardware-thread default of 20 workers, including
all 200,873 arithmetic cases. The six affected preflight suites also passed.
