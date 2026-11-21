# Complete non-Dhrystone sample comparison

The VBCC build did the arithmetic in the original integer example at compile time. The runtime version calls all twelve arithmetic functions on the SNES. Use the runtime rows to compare the time spent doing that work. Each row shows two fresh runs of the original single-file program or its split version, using zicc FastROM, zicc SlowROM and stock VBCC SlowROM.

For programs that finish, timing starts when `main` begins and stops when it returns. Three programs have different stopping points. Minimal runs its empty loop 1,000 times. Prompt prints once and finishes the screen update. The calculator runs from its first `printf` through the return from the `printf` that shows the result of `(12 + 3) * 4 / 2`.

Both compilers build the runtime caller and its functions from identical, separate C files with link-time optimization (LTO) off. The emulator checks the calls made by the caller and their results, including parser call counts for the calculator. Each recursive function can still optimize its own internal calls. In the original versions, the compiler can inline functions or compute answers at build time. The report records how many calls actually ran.

## Master clocks

| Sample | Original zicc Fast | Original zicc Slow | Original VBCC Slow | Runtime zicc Fast | Runtime zicc Slow | Runtime VBCC Slow |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| minimal | 18,560 | 22,680 | 22,640 | 18,560 | 22,680 | 22,640 |
| prompt | 374,568 | 374,680 | 19,634 | 374,648 | 374,756 | 19,666 |
| calc | 586,872 | 622,192 | 1,501,200 | 586,872 | 622,192 | 1,504,414 |
| insertion_sort | 30,024 | 35,148 | 35,430 | 30,024 | 35,148 | 37,040 |
| string_processing | 13,122 | 15,520 | 25,152 | 13,122 | 15,520 | 28,988 |
| integer_operations | 26,350 | 30,454 | 202 | 45,398 | 52,198 | 77,748 |
| function_calls | 104,004 | 119,730 | 146,150 | 104,004 | 119,730 | 153,910 |
| structures_and_tables | 13,884 | 16,530 | 7,652 | 13,884 | 16,530 | 26,012 |

## Application code bytes

| Sample | Original zicc Fast | Original zicc Slow | Original VBCC Slow | Runtime zicc Fast | Runtime zicc Slow | Runtime VBCC Slow |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| minimal | 3 | 3 | 3 | 13 | 13 | 11 |
| prompt | 15 | 15 | 23 | 25 | 25 | 27 |
| calc | 514 | 514 | 2,145 | 514 | 514 | 660 |
| insertion_sort | 403 | 403 | 729 | 403 | 403 | 437 |
| string_processing | 408 | 408 | 854 | 408 | 408 | 499 |
| integer_operations | 519 | 519 | 89 | 625 | 625 | 607 |
| function_calls | 344 | 344 | 550 | 344 | 344 | 438 |
| structures_and_tables | 306 | 306 | 501 | 306 | 306 | 405 |

## All linked code bytes

| Sample | Original zicc Fast | Original zicc Slow | Original VBCC Slow | Runtime zicc Fast | Runtime zicc Slow | Runtime VBCC Slow |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| minimal | 99 | 99 | 466 | 109 | 109 | 474 |
| prompt | 1,913 | 1,913 | 2,038 | 1,923 | 1,923 | 2,042 |
| calc | 12,541 | 12,541 | 12,873 | 12,541 | 12,541 | 11,388 |
| insertion_sort | 499 | 499 | 1,192 | 499 | 499 | 900 |
| string_processing | 504 | 504 | 1,317 | 504 | 504 | 962 |
| integer_operations | 1,996 | 1,996 | 552 | 2,102 | 2,102 | 1,340 |
| function_calls | 1,821 | 1,821 | 1,137 | 1,821 | 1,821 | 1,025 |
| structures_and_tables | 1,783 | 1,783 | 1,088 | 1,783 | 1,783 | 992 |

## Used non-asset ROM bytes

| Sample | Original zicc Fast | Original zicc Slow | Original VBCC Slow | Runtime zicc Fast | Runtime zicc Slow | Runtime VBCC Slow |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| minimal | 163 | 163 | 542 | 173 | 173 | 550 |
| prompt | 1,980 | 1,980 | 2,204 | 1,990 | 1,990 | 2,208 |
| calc | 13,021 | 13,021 | 13,568 | 13,021 | 13,021 | 12,083 |
| insertion_sort | 563 | 563 | 1,268 | 563 | 563 | 976 |
| string_processing | 607 | 607 | 1,430 | 607 | 607 | 1,077 |
| integer_operations | 2,060 | 2,060 | 628 | 2,166 | 2,166 | 1,416 |
| function_calls | 1,885 | 1,885 | 1,213 | 1,885 | 1,885 | 1,101 |
| structures_and_tables | 1,871 | 1,871 | 1,188 | 1,871 | 1,871 | 1,092 |

## Interpretation and verification

All 48 builds and 96 final measurement jobs passed. Ten finite Windows/MSVC reference programs also returned zero. Each pair agrees on elapsed clocks, call counts, hardware operation counts and ROM hash. Source/header hashes are identical across compilers within each mode; reports also check the executed ROM and harness hashes. Five first-attempt emulator timeouts passed in fresh processes; both attempt logs and the exact recovery history are retained. Folded original VBCC integer/inventory ROMs were also rejected when deliberately presented as runtime workloads.

Original VBCC integer_operations executes no hardware products and takes 202 clocks; the runtime version calls all twelve opaque kernels. Original VBCC inventory executes one product; the runtime version executes four and both adjustment calls. Inlining can make original application code larger even while removing call overhead: the calculator application shrinks from 2,145 to 660 bytes when split, while its time changes only slightly.

Function-call assertions distinguish a call frame from a loop backedge at the same entry address, and distinguish direct driver calls from recursive kernel calls. Both compilers must enter the three requested factorial/fibonacci computations with matching arguments/results, but legal recursion unrolling inside a kernel remains allowed. Calculator parser entries are checked at 14 skip, 4 number, 3 multiply-expression, 2 add-expression and 5 primary-expression calls in runtime mode.

Native pointer/call ABIs and libraries remain different. zicc calculator uses IEEE binary32; stock VBCC uses MSFP4. Both produce the same checked text. The prompt row includes each console library's flush behavior: zicc waits for VBlank and uploads its tilemap, so this is not an isolated code-generation comparison or a claim of equivalent display pipelines. The idle loop includes normal refresh stalls and is not a finite workload. Non-asset ROM excludes font/palette and unused fill; linked code retains each toolchain's runtime selection granularity.

The unmodified stock VC driver collided on temporary files during concurrent compilation. Its compile/assemble steps are serialized and receive private TEMP/TMP directories; zicc builds and independent emulator jobs use the bounded hardware-thread queue (20 workers on this machine). Emulator timeouts can retry once in a fresh process, with both attempt logs retained; assertion failures are never retried.

The comparison runner has been retired. Historical commands, source/compiler/runtime/library hashes, generated split sources, build logs, ROMs, assembly/maps/symbols, execution assertions, two independent process measurements and profiles were recorded in `build/all-sample-comparison/`. The integer and inventory runtime sources were paired with their original examples. The comparison excluded Dhrystone.
