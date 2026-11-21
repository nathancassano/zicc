# Guarded scalar-update leaf selection

A game can try to remove two items from an inventory and reject the change if
the new quantity would be negative. zicc recognizes a function that takes a
near struct pointer and a signed 16-bit adjustment, adds the adjustment to a
signed field, and holds the result in a private temporary. A negative result
returns 0. Otherwise the function stores the new value in the field and returns
1. `src/guarded_updates.inc` checks this pattern before reserving stack space.
Either addition order, nested fields, `p->field` and `(*p).field` work.
Function, parameter and field names do not affect the choice.

The strict statement grammar, parameter/local types, identical base/offset,
reference counts and private symbol checks exclude calls, escapes, other writes
and extra live state. Only signed-word-preserving casts are peeled. Other forms
retain the ordinary emitter, with no AST or symbol-layout mutation on rejection.
This is a narrow whole-function plan rather than a general register allocator.

The incoming pointer remains in X and the adjustment begins in A. Commuting the
pure addition allows `ADC displacement,X` to produce the next value in A. Its
16-bit N flag directly supplies the sign test; V is irrelevant to that test.
The successful branch stores A before replacing it with the return value.
Failure returns zero without writing. Y, D, DBR and register widths are unchanged;
no arithmetic scratch, parameter homes, temporary spill or frame is needed.

The inventory example emits 17 bytes:

```asm
_adjust_quantity:
    clc
    adc a:$0002,x
    bmi cg_inventory_kernels_5
    sta a:$0002,x
    lda #$0001
    rts
cg_inventory_kernels_5 = *
    lda #$0000
    rts
```

## Matched measurement

The baseline predates guarded-update selection. Identical separately
compiled inventory driver/kernel sources enforce all three inventory calls,
both adjustment calls and all four product inputs/results. Each compiler has two
independent agreeing Mesen runs, with main result zero and balanced stack/ABI.
The integer runtime source and object hashes are identical between both builds.

| Metric | Before | Guarded leaf |
| --- | ---: | ---: |
| adjust_quantity code bytes | 70 | 17 |
| Allocated function frame bytes | 6 | 0 |
| Saved Y bytes | 2 | 0 |
| Adjustment calls, FastROM master clocks | 1,472 | 330 |
| Adjustment calls, SlowROM master clocks | 1,706 | 336 |
| Main, FastROM master clocks | 15,066 | 13,884 |
| Main, SlowROM master clocks | 17,900 | 16,530 |
| Application code bytes | 359 | 306 |
| All linked code bytes | 1,836 | 1,783 |
| Used non-asset ROM bytes | 1,924 | 1,871 |

The function loses 53 bytes (75.71%) and eight bytes of callee stack use,
excluding the unchanged near-call return address. Two adjustment calls take
77.58% less profiled time in FastROM. Whole-program FastROM time falls 7.85%.
Main spans entry through return, excluding startup/exit cleanup; per-function
profiles include call-boundary overhead and can redistribute memory-stall time.
These are master clocks, not CPU-cycle estimates. ROM file size stays 32 KiB.

For context, the unchanged stock VBCC SlowROM runtime benchmark takes 26,012
master clocks and its two adjustments take 1,106. The new zicc SlowROM build
matches that ROM speed and workload; each compiler retains its native ABI.

## Tests and evidence

The existing scalar-homes suite adds fourteen guarded-update cases: four
accepted layouts/forms and ten fallback patterns. They check zero and signed-word
boundaries, positive/negative changes, unchanged failed updates, adjacent-field
canaries, either operand order and nested field offsets. Existing target behavior
when 16-bit addition wraps is also compared with the host's explicit short cast;
these cases do not claim portable signed-overflow semantics. Unsigned fields or
parameters, narrower casts, changed destinations, alternate guards/returns,
calls, escaped temporaries, extra locals and subtraction retain the fallback.
The suite runs 19 MSVC/Mesen programs in total and retains its optional baseline
compiler comparison. Successful shapes must have no frame/scratch and must
branch before their only field store.

Evidence is in `build/guarded-update-trial/`: saved baseline compiler,
baseline/candidate assembly/maps/ROMs, source/compiler/runtime hashes, build
commands/logs, repeated profiles, comparison script/report and full-check logs.
The first two 20-worker checks had integer-hardware emulator timeouts, each with
26/27 suites passing. That suite's instructions match the baseline byte for byte
after excluding source-path comments, and its focused recheck passed in 17.39 s.
Its wall-clock allowance was increased from 30 to 60 seconds for the loaded
hardware-thread queue; cases, hardware operation counts, emulated timing checks
and assertions are unchanged. Both timeout runs and the focused recheck are
retained alongside the final full check.

Final `make check CHECK_OUTPUT=build/guarded-update-trial/full-check-final`
passed 27/27 suites and 76/76 jobs with the actual hardware default of 20 workers
in 52.69 seconds. All 200,873 arithmetic cases remain covered. The normal runtime
comparison was refreshed after verification and agrees with the isolated trial.
