# Aggregate results and destination loads

After a statement such as `a = b;` copies a struct, the program has finished
with the address of the result. zicc skips the final address load for a fixed
copy and skips a push and pop (PHA/PLA) for an indirect near copy. For far and
volatile copies it skips only the final loads into the result registers. This
also applies to assignments used as the step in a `for` loop. A chain such as
`a = b = c`, or a field read from the assignment result, still gets that result.
The copies keep their operand evaluations, padding and volatile byte-access order.

A near aggregate source whose address can be loaded directly into X leaves
the evaluated destination in A, avoiding another PHA/PLA pair. More complex
sources retain the invocation-owned destination save across calls and nested
assignments. Y remains saved across every transfer. The existing inline/loop/MVN
selection policy and runtime helpers are unchanged.

Scalar assignments can evaluate a pure source first, then load the destination
base into X without changing A. This removes the PHX/PLX pair from eligible
field-to-field and indirect assignments. The proof follows the actual X-load
paths: near word homes, fixed global addresses, and small Y-relative addresses.
Stack-relative homes, general address arithmetic, far destinations, calls,
side effects and volatile expressions retain their previous paths. Compound
assignments retain their existing handling. No memory-value forwarding or
cross-call alias assumptions are introduced.

For example, the assignment `next->value = current->value` now uses:

```asm
    ldx a:$0001,y           ; current
    lda a:$0006,x
    ldx a:$0003,y           ; next
    sta a:$0006,x
```

Dhrystone's discarded 40-byte record assignment now uses:

```asm
    ldx a:$0001,y
    lda a:$0000,x           ; Ptr_Val_Par->Ptr_Comp
    ldx a:.loword(_Ptr_Glob)
    phy
    tay
    lda #$0027
    mvn #$7E, #$7E
    ply
```

The old copy sequence additionally used two PHA/PLA pairs and a TAX. Interrupts
still preserve the architectural registers and selectively saved scratch; the
optimization introduces no new shared state.

## HiROM measurements

The baseline includes staged HiROM allocation and binary embedding. Both builds use stage-1 HiROM allocation,
DBR $7E and 16-bit near pointers. Dhrystone's two C translation units remain
separate without LTO. These are normal optimized complete-benchmark results,
not opaque-input kernel-throughput measurements.

Each PAL profile measures 3,000 iterations from the first clock return to the
second clock entry, including ordinary interrupt overhead. Two successful
repetitions per mode agree exactly. SlowROM uses the same linked image with
MEMSEL disabled and the header/checksum updated.

| Mode | Merged baseline master clocks | After | Fewer clocks |
|---|---:|---:|---:|
| FastROM | 87,667,400 | 86,477,844 | 1.36% |
| SlowROM | 101,830,572 | 100,560,360 | 1.25% |

| Executed function, inclusive master clocks | FastROM before | After | SlowROM before | After |
|---|---:|---:|---:|---:|
| Proc_1, 3,000 calls | 20,166,280 | 18,978,740 | 23,009,400 | 21,742,464 |
| Proc_3, 3,000 calls | 3,400,060 | 3,208,620 | 3,876,082 | 3,672,096 |

Inclusive function totals overlap with their callees. Ordinary code shrinks
from 8,457 to 8,442 bytes; application code shrinks from 3,126 to 3,111 bytes.
Constants remain 3,975 bytes and the DATA load image remains two bytes. ROM
capacity remains 65,536 bytes in both modes.

| Console report | NTSC ticks / Dhrystones per second | PAL ticks / Dhrystones per second |
|---|---:|---:|
| FastROM baseline | 246 / 731 | 206 / 728 |
| FastROM after | 242 / 743 | 203 / 738 |
| SlowROM baseline | 286 / 629 | 240 / 625 |
| SlowROM after | 282 / 638 | 237 / 632 |

Console reports are quantized to physical frames. Execution assertions verify
all procedure/function counts and inputs, loop counts, hardware arithmetic,
array/global writes, record contents, and 3,000 each of the 31-byte literal and
40-byte record copies. Final output and all 57,344 visible screen pixels pass
in NTSC and PAL for both speeds. These checks establish that the workload
continues to execute.

## Verification and evidence

`tests/check-aggregate-copy.py` covers discarded statements and loop steps,
consumed/chained results, padding, unions, recursive frames and side-effecting
operands, plus all four handlers and interrupted foreground copies. The scalar
suite adds signed-byte, pointer and narrowed-long field sources, self-aliasing,
and a call which changes the destination pointer. NTSC/PAL hardware NMI/IRQ
coverage and BRK/COP injection before every scheduled-function instruction
check register, status, stack and arithmetic-scratch preservation. The focused
scalar suite also passes using the saved merged-baseline compiler.

Raw assembly, allocation manifests, source/compiler/runtime/ROM hashes, repeat
profiles, assertions, console output, and screenshots are retained under
`build/aggregate-scheduling-trial/`; `comparison.json` contains the per-function
results. The first candidate FastROM profiling attempt timed out; independent
successful repetitions 2 and 3 provide the reported measurements, and the
failed attempt's log is retained.

Final `make check CHECK_OUTPUT=build/aggregate-scheduling-trial/full-check-final`
passes all 27 suites / 76 jobs with the hardware-thread default of 20 workers
in 582.10 seconds, retaining all 50 arithmetic batches / 200,873 cases. The
summary compiler hash matches `final-build/manifest.json` and the current binary.
