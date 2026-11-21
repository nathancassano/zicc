# All samples after compiler optimization

## Final Priority 4 regression check

All 40 sample ROMs contained exactly the same bytes as before. The earlier
build included variadic argument support. The rebuild added calling rules
for structs and unions, bit-fields, and memory allocation routines written
in assembly. The paired hashes are in
`build/priority4-final-perf/rom-hashes.json`.

| Workload | Matched result |
| --- | --- |
| Dhrystone FastROM | 60,280,446 master clocks over 3,000 verified iterations |
| BouncingSprites FastROM | 70,582,714 busy master clocks over 600 frames, with the same final state hash |
| Dragon FastROM quick route | Matching busy clocks, lag and OAM in every phase |

PI and Whetstone were rebuilt and checked by ROM identity. Their long timing
runs were skipped. The rebuilt ROMs and fresh timing evidence are in
`build/priority4-final-perf/`.

## Priority 4 rebuild and regression check

The variadic-support build was compared against the Priority 3 builds. All 40 ROM
images matched byte for byte, including the ordinary sample matrix,
Dhrystone, PI, Whetstone, BouncingSprites and Dragon. The hash pairs are in
`build/priority4-perf/rom-hashes.json`.

| Workload | Measured result |
| --- | --- |
| Dhrystone FastROM | 60,280,446 master clocks over 3,000 verified iterations, equal to Priority 3 |
| BouncingSprites FastROM | 70,582,714 busy master clocks over 600 frames, with matching final state |
| Dragon FastROM quick route | Matching busy clocks, lag and OAM in every phase |

PI and Whetstone were rebuilt and compared by ROM identity. Their long
timing workloads were skipped. Fresh timings and Dragon's asset-bank check
are retained with the rebuilt ROMs in `build/priority4-perf/`.

## Follow-up on Dhrystone address reuse

The fix clears empty statements after dead-store elimination,
allowing address reuse to span the surviving stores. Matched pre-Priority-2
and current builds both took 63,286,378 FastROM master clocks. The fix reduced
that to 60,280,446 over 3,000 verified iterations, a 4.75% improvement.
`Proc_8` shrank from 189 to 117 bytes. The older benchmark below measured
61,005,636 master clocks.

The literal pass reorder increased Dragon quick-route busy time by up to
1.74%. The committed cleanup produced byte-identical Dragon and BouncingSprites
FastROMs against their matched baselines. BouncingSprites also matched the
final state hash and 70,582,714 busy master clocks over 600 frames.

Evidence is retained in `build/dhry-priority2-audit/`,
`build/optimizer-order-trial/`, and `build/optimizer-order-cleanup/`.
All 27 suites passed in `build/check/20261109T095939.231047Z/`.

## Original comparison

Compiler SHA-256 `e520302e031adf011d15233dc5697830101cac762c5288e6b8339f4a844b6547`.

The eight original examples and their eight separate-TU runtime forms, Dhrystone, PI, Whetstone and BouncingSprites were rebuilt. zicc FastROM/SlowROM and vbcc65816_r2 use fresh builds. All emulator runs are headless, unthrottled and in separate processes; independent measurements were launched concurrently. Times below are emulated target time, not host wall time. The compiler/runtime source was frozen throughout.

## Baselines and comparison boundaries

The two saved baselines predate the **arithmetic and PI optimizations** and the **homebrew code generation changes**, respectively. Old values come from their preserved two-run captures; raw ROM hashes, source equivalence after newline normalization, emulator DLL and repeated timings were verified. They were not silently recompiled with the new compiler. `baseline-validation.json` records all 51 case checks.

All **51 original/runtime/Dhrystone ROMs are byte-identical to the pre-homebrew baseline**, including stock VBCC. All three portable PI ROMs also match that baseline byte for byte. Thus their timings and sizes have not regressed during the homebrew codegen work. Improvements relative to the pre-arithmetic baseline below include the earlier arithmetic changes and must not be attributed solely to the four most recent milestones.

Whetstone had no valid previous full-run timing. It is recorded as a new baseline, not a zero-time comparison. BouncingSprites historical zicc values include the entry-point/typedef compatibility fixes needed to compile it; staged kernel inputs and expected states match.

## Original programs: master clocks

These allow legitimate constant folding and inlining. They are whole-program results. In particular, the 202-clock original VBCC integer example folds away its arithmetic and is not arithmetic throughput. Minimal is 1,000 idle iterations; prompt stops at the first print/flush; calc ends after its result print. Startup is excluded.

| Program | Early Fast → now | Early Slow → now | VBCC Slow now |
| --- | ---: | ---: | ---: |
| minimal | 18,560 → 18,560 | 22,680 → 22,680 | 22,640 |
| prompt | 368,222 → 368,222 | 370,212 → 370,212 | 19,634 |
| calc | 503,868 → 503,868 | 528,718 → 528,718 | 1,502,818 |
| insertion_sort | 14,386 → 14,386 | 16,844 → 16,844 | 35,430 |
| string_processing | 12,088 → 12,088 | 14,454 → 14,454 | 25,152 |
| integer_operations | 1,866 → 1,502 | 2,116 → 1,728 | 202 |
| function_calls | 78,084 → 78,084 | 89,608 → 89,608 | 146,150 |
| structures_and_tables | 13,412 → 13,412 | 16,012 → 16,012 | 7,652 |
| dhrystone | 61,042,722 → 61,005,636 | 71,227,870 → 71,184,596 | 87,305,174 |

Dhrystone performs 3,000 checked Proc_8/Func_2 iterations. Current FastROM/SlowROM/VBCC rates are 1,056.16 / 905.14 / 738.01 Dhrystones/s. Native pointer/call ABIs and linked runtime scope differ.

## Matched separate-TU workloads: master clocks

Identical drivers and opaque kernels are compiled separately without LTO. Required calls, inputs, results and observable operations are asserted. Original and runtime results are kept separate. These eight rows are unchanged from both historical snapshots.

| Program | zicc Fast | zicc Slow | VBCC Slow |
| --- | ---: | ---: | ---: |
| minimal | 18,560 | 22,680 | 22,640 |
| prompt | 368,240 | 370,228 | 19,666 |
| calc | 504,406 | 529,282 | 1,506,030 |
| insertion_sort | 14,386 | 16,844 | 37,040 |
| string_processing | 14,796 | 17,224 | 28,988 |
| integer_operations | 35,798 | 41,218 | 77,748 |
| function_calls | 79,602 | 91,368 | 153,910 |
| structures_and_tables | 14,180 | 16,832 | 26,012 |

## Code sizes for original/runtime programs

Application / all linked code, in bytes. zicc code sizes are equal between its two ROM speeds. Arrows compare the pre-arithmetic baseline with the final build. The final sizes also match the pre-homebrew baseline. ROM padding and font assets are not code.

| Program / mode | zicc app before → now | zicc linked before → now | VBCC app / linked now |
| --- | ---: | ---: | ---: |
| minimal/original | 2 → 2 | 120 → 120 | 3 / 466 |
| minimal/runtime | 9 → 9 | 127 → 127 | 11 / 474 |
| prompt/original | 19 → 19 | 1,938 → 1,938 | 23 / 2,038 |
| prompt/runtime | 23 → 23 | 1,942 → 1,942 | 27 / 2,042 |
| calc/original | 573 → 573 | 10,919 → 11,039 | 2,184 / 12,912 |
| calc/runtime | 502 → 502 | 10,848 → 10,968 | 679 / 11,407 |
| insertion_sort/original | 322 → 322 | 2,205 → 2,205 | 729 / 1,192 |
| insertion_sort/runtime | 322 → 322 | 2,205 → 2,205 | 437 / 900 |
| string_processing/original | 418 → 418 | 2,301 → 2,301 | 854 / 1,317 |
| string_processing/runtime | 425 → 425 | 2,308 → 2,308 | 499 / 962 |
| integer_operations/original | 183 → 141 | 3,523 → 3,601 | 89 / 552 |
| integer_operations/runtime | 611 → 611 | 3,951 → 4,071 | 607 / 1,340 |
| function_calls/original | 291 → 291 | 3,631 → 3,751 | 550 / 1,137 |
| function_calls/runtime | 259 → 259 | 3,599 → 3,719 | 438 / 1,025 |
| structures_and_tables/original | 534 → 534 | 3,874 → 3,994 | 501 / 1,088 |
| structures_and_tables/runtime | 365 → 365 | 3,705 → 3,825 | 405 / 992 |
| dhrystone/original | 2,778 → 2,769 | 8,228 → 8,339 | 3,065 / 13,178 |

## PI

The portable driver/kernel/console sources are unchanged and separately compiled without LTO. Both repeats verify all 897 output characters and 2,411,135 array updates against the host results. The supplied original ROM is replayed byte for byte as an additional reference.

| Build | Early compute seconds → now | Current display seconds | Current app / linked B |
| --- | ---: | ---: | ---: |
| original | 788.323039 → 788.323039 | 788.432538 | 1,169 / not separated |
| zicc-fast | 687.593452 → 352.214256 | 352.500459 | 513 / 5808 |
| zicc-slow | 795.101243 → 409.804882 | 410.088952 | 513 / 5808 |
| vbcc-slow | 764.175486 → 764.175486 | 764.305605 | 1,155 / 3579 |

## BouncingSprites

Average busy work across 600 logical updates, excluding startup and VBlank waits. Every update checks all positions, velocities, OAM, gradient and phase against independently calculated values. Repeated CPU/master clocks and final pixels agree. zicc now completes 600 logical updates in 600 physical frames; VBCC still uses 1,200 physical frames.

| Build | Early clocks/update | Before homebrew work | Current clocks/update | Current CPU cycles/update | Current app / linked B |
| --- | ---: | ---: | ---: | ---: | ---: |
| zicc-fast | 430,994.45 | 418,465.04 | 164,417.99 | 23,728.35 | 4,659 / 8,119 |
| zicc-slow | 510,386.01 | 494,350.67 | 196,725.78 | 23,728.35 | 4,659 / 8,119 |
| vbcc-slow | 397,479.03 | 397,479.03 | 397,479.03 | 48,257.17 | 6,898 / 7,422 |

Relative to pre-homebrew master, FastROM busy clocks fall **60.71%** and SlowROM **60.21%**; linked code falls **9,945 → 8,119 bytes**. Relative to the earliest valid port, the clock reductions are **61.85% / 61.46%**. The stock VBCC result is unchanged. FastROM/SlowROM are different bus speeds, so only equal-speed comparisons isolate that part of the target difference.

## First complete Whetstone runs

All eight original kernels ran at **xtra=1, x100=100**, not the earlier reduced x100=1 test. Every kernel entry and result section is required. Existing-instruction execution probes prove 12,000 / 1,400 / 34,500 / 21,000 / 3,199 / 89,900 / 61,600 / 9,300 iterations (header probes may include one exit test). Inlined work is counted at loop backedges, not assumed absent from missing calls. Two runs per configuration agree exactly, including all section times and result bits; independent iteration-validation replays reproduce the timed intervals.

These are **whole-program application benchmarks with execution checks**, not a matched arithmetic/helper throughput claim. The zicc target uses IEEE binary32; stock VBCC uses MSFP4. Math approximations are the same upstream C algorithms on both compilers. zicc library mode uses different, range-reduced math algorithms and has different iterative numerical results; its speed gain must not be described as instruction selection alone. No Whetstone compiler baseline timing existed before this work.

Compute time sums each test entry through its pout entry. It excludes formatting and frame waits inside pout and the summary UI; it includes test setup and timing-call overhead. Whole time runs from whetstones entry through its return, including eight result displays and table headers. All seconds use 21,477,272 master clocks/s.

| Math mode / build | Compute master clocks | Busy CPU cycles | Compute seconds | Whole seconds | App / linked B |
| --- | ---: | ---: | ---: | ---: | ---: |
| approximate/zicc-fast | 20,682,765,980 | 2,982,634,726 | 963.007126 | 963.662960 | 14,372 / 19,861 |
| approximate/zicc-slow | 23,798,640,540 | 2,984,840,910 | 1108.084888 | 1108.790623 | 14,372 / 19,861 |
| library/zicc-fast | 14,901,305,106 | 2,166,645,815 | 693.817404 | 694.489584 | 12,640 / 22,473 |
| library/zicc-slow | 17,279,397,488 | 2,168,329,308 | 804.543402 | 805.240534 | 12,640 / 22,473 |
| approximate/vbcc-slow | 21,168,450,804 | 2,687,807,419 | 985.621023 | 986.325748 | 16,879 / 19,797 |

### Whetstone numerical interpretation

zicc approximation-mode results match the strict binary32 full-run host reference bit for bit in all eight sections. Float representation and accumulated rounding differ under VBCC/MSFP4: N1 is -1.123319745 versus -1.124750137; N8 is 0.751429260 versus 0.750083447. Integer/array sections N3/N4/N7 agree exactly (1, 12, 3). This is not a claim that both floating runtimes produce identical numerical work at every intermediate step.

Library N5 is 0.499111474 versus the host libm result 0.499092996 after 3,199 iterative updates. Library N8 is 0.751099586 versus 0.751106262 after 9,300 updates. Independent math-function tests previously bounded their observed error at two ULP per tested call; that is not a two-ULP bound on these long recurrences. The crude approximation N5 instead produces 0.785174787. Algorithm/accuracy differences are material. All result bits and host outputs are retained in comparison.json.

### VBCC NMI correction and completion boundary

The unmodified imported VBCC ROM failed during N1. Instruction tracing shows the MSFP4 runtime can be interrupted with X=8. The generated native NMI wrapper executes REP #$20, then uses 16-bit PEI saves but byte-sized PLX/DP-store restores; RTI therefore consumes a corrupted return stack. The accepted platform adaptation changed **exactly one ROM byte**, REP #$20 → REP #$30, at offset 19,467. Application object bytes, kernels, VBCC compiler, stock runtime libraries, linker mapping and math algorithms were unchanged.

The VBCC run completes and returns from all eight benchmark sections, but its subsequent untimed summary formatter does not reach TEST COMPLETE. The accepted profiler uses `--benchmark-only` and stops after benchmark return; it does not report that untimed summary as passing. zicc completes the original summary UI as well. The failed stock run, diagnostic traces, rejected RAM-relocation experiment and untimed-summary attempts remain separate and are not included in accepted timings.

## Evidence and historical reproduction

`build/post-optimization-20261108/comparison.json` collects the current results and both historical baselines; `baseline-validation.json` verifies source/ROM identity. `samples/` retains 51 builds and 102 measurements; `pi/` retains eight runs including the supplied-ROM reference; `bouncingsprites/` retains six 600-update runs. Whetstone folders retain both full repeats, source/assembly/maps/ROMs, per-section values/cycles, iteration probes, scripts/logs and screenshots. Original baseline directories remain untouched.

```text
make all smoke
python tools/build-homebrew-samples.py --output build/NEW/library --port-zicc --whetstone-ui imported --whetstone-math library --sample whetstone --kind zicc-fast --kind zicc-slow --support build/import-demos/support
python tools/profile-whetstone.py --build-output build/NEW/library --output build/NEW/whetstone --worker zicc-fast --repeat 1
```

These commands use the archived Whetstone source and tools with the
historical compiler checkout. The profiler ran in a fresh process for each
repeat and both zicc ROM kinds using unthrottled MesenCE. The pinned imported
source bytes were restored from Git after checkout newline conversion, and each
manifest hash was verified before homebrew compilation. The integrated compiler
had already passed 27/27 suites.
