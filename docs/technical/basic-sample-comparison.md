# Basic sample comparison

The original VBCC integer example took 202 clocks because the compiler worked out the answer before the SNES ran it. Its `main` only compares a constant and returns. In `integer_operations_runtime`, both compilers build the same caller and `samples/integer_kernels.c` separately with LTO off. The emulator checks that all twelve functions run once each. The times include the calls and the memory speed of each ROM. Application size includes both C files.

MesenCE 2.2.1 timed each program from the first instruction of `main` through its return (`RTL`). This skips startup and the later exit and stream cleanup. Every run returned zero and restored the stack. Two fresh runs per ROM gave identical times, measured in SNES master clocks at 21.477272 MHz.

Both compilers read the same source files. zicc used its integer runtime in FastROM bank $80. Stock VBCC from `C:/snesdev/vbcc65816_r2` used `-O3 -msfp4`, its libraries and its startup code in SlowROM bank $00. These samples use only integer math. VBCC computed more answers at build time and inlined more calls. The tables include the effects of those choices and of the different memory speeds.

The original zicc integer example now does two divisions, one signed and one unsigned. It used to do four. zicc can share the quotient and remainder in one function when the inputs stay the same and every path to the second use passes through the first division. Separate runtime functions still divide independently. The flag `--no-divmod-reuse` turns this optimization off.

| Runtime inspection | Evidence |
| --- | --- |
| Original VBCC main | No divide, remainder, multiply or mix_words call |
| Runtime VBCC main | Twelve externally compiled kernel calls, each verified by execution hooks |
| zicc integer multiply | S-CPU $4202/$4203 byte partial products |
| zicc divisor magnitude 1..255 | S-CPU $4204..$4206; quotient and remainder read together |
| zicc larger divisor, including $1234 | Software restoring division |

| Sample | zicc clocks | VBCC clocks | zicc / VBCC time | zicc us | VBCC us |
| --- | ---: | ---: | ---: | ---: | ---: |
| insertion_sort | 30,024 | 35,430 | 0.85x | 1397.94 | 1649.65 |
| string_processing | 13,122 | 25,152 | 0.52x | 610.97 | 1171.10 |
| integer_operations | 26,350 | 202 | 130.45x | 1226.88 | 9.41 |
| function_calls | 104,004 | 146,150 | 0.71x | 4842.51 | 6804.87 |
| integer_operations_runtime | 45,398 | 77,748 | 0.58x | 2113.77 | 3620.01 |

A ratio above 1 means zicc takes longer. The ROM speed difference remains part of this comparison; timings have not been scaled to pretend the memory timings match.

| Sample | zicc application code | VBCC application code | zicc all code | VBCC all code | zicc non-asset ROM | VBCC non-asset ROM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| insertion_sort | 403 | 729 | 499 | 1,192 | 563 | 1,268 |
| string_processing | 408 | 854 | 504 | 1,317 | 607 | 1,430 |
| integer_operations | 519 | 89 | 1,795 | 552 | 1,859 | 628 |
| function_calls | 344 | 550 | 1,620 | 1,137 | 1,684 | 1,213 |
| integer_operations_runtime | 625 | 607 | 1,901 | 1,340 | 1,965 | 1,416 |

Sizes are bytes. Application code is the input translation unit, including uncalled emitted functions. All code also includes linked runtime helpers, startup and interrupt stubs. Non-asset ROM further includes strings/tables, header/vectors, constructors and initialized-data images. Unused ROM fill and font assets are excluded. zicc links integer helpers plus the identical DP workspace, without the unrelated float wrappers/engine. Integer helpers are linked only when requested by the generated imports; when used, the helper object still includes its unused members. The stock VBCC startup can pull additional library support.

## ROMs and debug symbols

zicc ROMs are build/sample-check/NAME.sfc with matching .dbg, .sym, .mlb, .map, .labels and emitted .s files. VBCC ROMs are build/sample-check/vbcc/NAME.sfc with .sym, .mlb, .map and .s; the release toolchain does not produce ca65 .dbg files. MLB labels are suitable for Mesen. zicc DBG stepping currently refers to generated assembly.

## Nested calls

For combine(factorial(3), fibonacci(6), factorial(4), fibonacci(5)), the current zicc sequence is:

```asm
ldx #5
jsr .loword(_fibonacci)
pha                         ; fourth argument
ldx #4
jsr .loword(_factorial)
pha                         ; third argument
ldx #6
jsr .loword(_fibonacci)
pha                         ; save second argument while evaluating the first
ldx #3
jsr .loword(_factorial)
tax                         ; first argument into X
pla                         ; restore second argument into A
jsr .loword(_combine)
plx
plx                         ; discard third/fourth arguments, preserving A
```

This compiler currently evaluates these arguments right to left; C itself does not promise this argument evaluation order. Every nested call finishes before the outer call. Saved arguments and caller locals live on the stack, not in caller-clobbered arithmetic scratch. Functions with locals save Y and use a separate Y-based stack frame, so recursive invocations have independent locals. A/X are caller-clobbered, Y/D/DBR are preserved. Word returns use A; 32-bit returns use A low/X high. Stack cleanup preserves the return value.

## Reproduction

The comparison runner has been retired. Historical build commands, source/compiler/library/ROM hashes, two-run measurements, Lua scripts, logs and per-function profiler records were recorded in `build/sample-check/`. The per-function CSV is `build/sample-check/comparison-functions.csv`. Its inclusive totals overlap for recursive and nested calls. The profiler reset just before the startup call to main, so function inclusive values can include the call instruction while the summary interval begins at main entry.

## Application functions

These are exact emitted C-function section sizes. Zero calls means no separate call was observed, even if an out-of-line body remains in ROM. Main is measured by entry/return hooks. The profiler reset clears its already-created main frame; main exclusive time in the CSV is the measured elapsed interval minus descendant self times. Recursive inclusive times overlap.


### insertion_sort

| Function | zicc bytes | VBCC bytes | zicc calls | VBCC calls | zicc inclusive clocks | VBCC inclusive clocks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `insertion_sort` | 170 | 194 | 4 | 0 | 28,004 | 0 |
| `main` | 233 | 535 | 1 | 1 | 30,024 | 35,430 |

### string_processing

| Function | zicc bytes | VBCC bytes | zicc calls | VBCC calls | zicc inclusive clocks | VBCC inclusive clocks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `copy_text` | 30 | 54 | 3 | 0 | 2,402 | 0 |
| `main` | 296 | 644 | 1 | 1 | 13,122 | 25,152 |
| `reverse_text` | 47 | 82 | 4 | 0 | 3,896 | 0 |
| `text_equal` | 35 | 74 | 4 | 0 | 3,880 | 0 |

### integer_operations

| Function | zicc bytes | VBCC bytes | zicc calls | VBCC calls | zicc inclusive clocks | VBCC inclusive clocks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `main` | 476 | 24 | 1 | 1 | 26,350 | 202 |
| `mix_words` | 43 | 65 | 1 | 0 | 2,058 | 0 |

### function_calls

| Function | zicc bytes | VBCC bytes | zicc calls | VBCC calls | zicc inclusive clocks | VBCC inclusive clocks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `add_scaled` | 74 | 61 | 1 | 0 | 2,332 | 0 |
| `combine` | 27 | 42 | 1 | 0 | 406 | 0 |
| `factorial` | 43 | 87 | 13 | 6 | 30,698 | 15,024 |
| `fibonacci` | 52 | 137 | 217 | 108 | 488,732 | 381,136 |
| `main` | 148 | 223 | 1 | 1 | 104,004 | 146,150 |

### integer_operations_runtime

| Function | zicc bytes | VBCC bytes | zicc calls | VBCC calls | zicc inclusive clocks | VBCC inclusive clocks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `long_add` | 13 | 17 | 1 | 1 | 262 | 382 |
| `long_and` | 12 | 16 | 1 | 1 | 250 | 328 |
| `long_mul` | 20 | 24 | 1 | 1 | 2,942 | 3,798 |
| `long_shr` | 16 | 30 | 1 | 1 | 574 | 2,250 |
| `main` | 422 | 338 | 1 | 1 | 45,398 | 77,748 |
| `mix_words` | 43 | 65 | 1 | 1 | 2,058 | 1,802 |
| `signed_add` | 6 | 8 | 1 | 1 | 108 | 200 |
| `signed_div` | 20 | 24 | 1 | 1 | 2,602 | 17,092 |
| `signed_mod` | 20 | 24 | 1 | 1 | 2,938 | 17,092 |
| `unsigned_div` | 20 | 24 | 1 | 1 | 14,840 | 15,314 |
| `unsigned_mod` | 20 | 24 | 1 | 1 | 14,976 | 15,524 |
| `word_add` | 6 | 8 | 1 | 1 | 108 | 160 |
| `word_sub` | 7 | 5 | 1 | 1 | 120 | 110 |
