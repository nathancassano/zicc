# zicc optimization results against VBCC

Of the 684 originally slow cases, 589 ran faster after the changes, 94 tied
their original times, and one took 24 extra master clocks. This compares zicc
with its own starting point. The tables also compare each build with VBCC.
The VBCC builds use slower ROM and their own libraries and calling rules.

## Batch 1

Ten optimizations from the GCC torture and Csmith slowdown inventory. Each before/after pair isolates one change on top of the preceding fixes. The working-tree baseline included the existing Csmith compiler changes. Clocks are Mesen master clocks from entry to return or successful exit of `main`. zicc ran in FastROM and both VBCC builds ran in SlowROM with their native ABIs and libraries. Every displayed timing was repeated from the same ROM. GCC sources matched within each displayed pair. The Csmith pointer variants have different source hashes across lanes and matching checksums. The stock VBCC Csmith comparisons below failed to compile.

Code sizes are assembled application and total linked code bytes, excluding data and ROM padding. The VBCC linked count covers its map text sections. The gap is zicc after minus the comparison lane.

| Fix | Optimization |
| ---: | --- |
| 1 | Move whole words for constant 64-bit shifts |
| 2 | Prove comparisons from quotient ranges |
| 3 | Compare wide integers with zero directly |
| 4 | Compare two fixed wide operands in place |
| 5 | Write wide literal limbs directly to the operand slot |
| 6 | Compare wide integers with immediate limbs |
| 7 | Extract the surviving words of a narrowed right shift |
| 8 | Push fixed or literal wide arguments directly |
| 9 | Lower unsigned wide division by a shifted power of two |
| 10 | Use word multipliers for zero-extended 16×16 and 16×32 products |

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `930921-1.c` | 175,473,792 → 157,939,592 | -17,534,200 (-9.99%) | 228 / 5,269 → 163 / 4,944 | 76,357,526 · +81,582,066 (+106.84%) | 686 / 2,477 | BUILD 930921-1-compile | - |
| 2 | `divcmp-3.c` | 2,665,162 → 58,936 | -2,606,226 (-97.79%) | 814 / 5,264 → 88 / 472 | 1,350,106 · -1,291,170 (-95.63%) | 999 / 1,901 | 1,485,434 · -1,426,498 (-96.03%) | 1,015 / 1,713 |
| 3 | `950612-1.c` | 209,906 → 142,210 | -67,696 (-32.25%) | 1,135 / 3,372 → 934 / 3,171 | 65,144 · +77,066 (+118.30%) | 919 / 1,798 | BUILD 950612-1-compile | - |
| 3 | `950704-1.c` | 55,980 → 21,734 | -34,246 (-61.18%) | 1,416 / 3,653 → 862 / 3,043 | 126 · +21,608 (+17149.21%) | 270 / 1,131 | BUILD 950704-1-compile | - |
| 3 | `tstdi-1.c` | 87,118 → 30,908 | -56,210 (-64.52%) | 2,627 / 4,864 → 1,997 / 4,178 | 2,646 · +28,262 (+1068.10%) | 643 / 1,522 | BUILD link | - |
| 4 | `cmpdi-1.c` | 1,501,496 → 1,307,128 | -194,368 (-12.95%) | 1,806 / 3,987 → 1,634 / 3,815 | 383,346 · +923,782 (+240.98%) | 1,148 / 2,027 | BUILD cmpdi-1-compile | - |
| 5 | `930921-1.c` | 157,939,592 → 150,583,872 | -7,355,720 (-4.66%) | 163 / 4,944 → 120 / 4,901 | 76,357,526 · +74,226,346 (+97.21%) | 686 / 2,477 | BUILD 930921-1-compile | - |
| 5 | `950704-1.c` | 21,734 → 20,578 | -1,156 (-5.32%) | 862 / 3,043 → 712 / 2,893 | 126 · +20,452 (+16231.75%) | 270 / 1,131 | BUILD 950704-1-compile | - |
| 5 | `divconst-3.c` | 26,218 → 24,468 | -1,750 (-6.67%) | 339 / 3,568 → 201 / 3,430 | 1,092 · +23,376 (+2140.66%) | 167 / 1,725 | BUILD link | - |
| 5 | `pr46019.c` | 115,744 → 115,258 | -486 (-0.42%) | 300 / 3,789 → 282 / 3,771 | 68 · +115,190 (+169397.06%) | 4 / 865 | 68 · +115,190 (+169397.06%) | 4 / 467 |
| 6 | `divconst-3.c` | 24,468 → 23,456 | -1,012 (-4.14%) | 201 / 3,430 → 193 / 3,366 | 1,092 · +22,364 (+2047.99%) | 167 / 1,725 | BUILD link | - |
| 6 | `multdi-1.c` | 15,414 → 14,704 | -710 (-4.61%) | 202 / 2,770 → 182 / 2,694 | 252 · +14,452 (+5734.92%) | 142 / 1,892 | BUILD link | - |
| 6 | `csmith-expression-and-pointer-modes/ptr2/no-const-pointers/seed-123` | 10,590,940 → 10,277,936 | -313,004 (-2.96%) | 22,293 / 31,259 → 22,196 / 31,162 | 3,234,500 · +7,043,436 (+217.76%) | 5,879 / 32,242 | BUILD case-compile | - |
| 6 | `csmith-expression-and-pointer-modes/ptr2/no-volatile-aggregate-fields/seed-123` | 6,124,366 → 4,399,102 | -1,725,264 (-28.17%) | 18,373 / 27,339 → 18,202 / 27,168 | 1,655,394 · +2,743,708 (+165.74%) | 3,349 / 29,495 | BUILD case-compile | - |
| 6 | `csmith-remaining-profiles-unmodified/ptr2/no-byte-types/seed-123` | 104,460,630 → 98,094,758 | -6,365,872 (-6.09%) | 15,346 / 24,312 → 15,241 / 24,207 | 48,789,298 · +49,305,460 (+101.06%) | 4,147 / 30,672 | BUILD case-compile | - |
| 7 | `930921-1.c` | 150,583,872 → 148,853,112 | -1,730,760 (-1.15%) | 120 / 4,901 → 108 / 4,889 | 76,357,526 · +72,495,586 (+94.94%) | 686 / 2,477 | BUILD 930921-1-compile | - |
| 8 | `cmpdi-1.c` | 1,307,128 → 1,011,768 | -295,360 (-22.60%) | 1,634 / 3,815 → 1,314 / 3,495 | 383,346 · +628,422 (+163.93%) | 1,148 / 2,027 | BUILD cmpdi-1-compile | - |
| 8 | `divconst-3.c` | 23,456 → 22,908 | -548 (-2.34%) | 193 / 3,366 → 159 / 3,332 | 1,092 · +21,816 (+1997.80%) | 167 / 1,725 | BUILD link | - |
| 8 | `tstdi-1.c` | 29,032 → 20,836 | -8,196 (-28.23%) | 1,691 / 3,872 → 1,277 / 1,675 | 2,646 · +18,190 (+687.45%) | 643 / 1,522 | BUILD link | - |
| 9 | `pr46019.c` | 115,258 → 42,990 | -72,268 (-62.70%) | 282 / 3,771 → 303 / 2,800 | 68 · +42,922 (+63120.59%) | 4 / 865 | 68 · +42,922 (+63120.59%) | 4 / 467 |
| 10 | `930921-1.c` | 148,853,112 → 47,492,992 | -101,360,120 (-68.09%) | 108 / 4,889 → 148 / 4,598 | 76,357,526 · -28,864,534 (-37.80%) | 686 / 2,477 | BUILD 930921-1-compile | - |

The `930921-1.c` loop evaluates the reciprocal multiply and validates it against division for 10,000 inputs. Modified VBCC inlines and unrolls the loop. The zicc changes remove the shift helper and replace the full 64-bit multiply with two word products. The `divcmp-3.c` improvement comes from eliminating quotient computations with provable bounds. Modified and stock VBCC still emit a divide in the loop. Both VBCC lanes fold `pr46019.c` to a successful return. The clock counts for these cases describe the original whole programs.

Execution hooks counted 10,000 reciprocal multiply and division operations in the baseline and modified VBCC, and 20,000 word products and 10,000 divisions after fix 10.

Each `build/slower-fNN-*` directory retains source/compiler and ROM hashes, generated assembly, link maps, Mesen logs and the comparison CSV.

### Inventory replay after batch 1

All 300 listed GCC cases passed, with 63 faster, 236 tied and one slower than the inventory zicc run. All 384 listed Csmith cases reproduced their checksums, with 368 faster and 16 tied. Four GCC cases and two Csmith cases closed every previously recorded VBCC gap for that case. The replay records are in `build/slower-b1-g/results.jsonl` and `build/slower-b1-c2/results.jsonl`. The 54-clock increase in `pr42006.c` came from losing stack-relative frame conversion after a range proof made an arm unreachable. Fix 12 below restores the conversion.

## Batch 2

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 11 | `ieee/20041213-1.c` | 162,474 → 3,280 | -159,194 (-97.98%) | 100 / 3,461 → 100 / 6,652 | 2,374 · +906 (+38.16%) | 53 / 3,008 | 2,374 · +906 (+38.16%) | 53 / 2,610 |
| 12 | `pr42006.c` | 2,068 → 1,874 | -194 (-9.38%) | 141 / 539 → 127 / 525 | 1,940 · -66 (-3.40%) | 99 / 978 | 2,032 · -158 (-7.78%) | 106 / 587 |
| 13 | `pr59387.c` | 113,800 → 8,536 | -105,264 (-92.50%) | 64 / 448 → 58 / 442 | 13,104 · -4,568 (-34.86%) | 63 / 924 | 13,370 · -4,834 (-36.16%) | 64 / 527 |
| 14 | `20040409-2.c` | 20,856 → 19,952 | -904 (-4.33%) | 553 / 2,734 → 505 / 2,686 | 68 · +19,884 (+29,241.18%) | 423 / 1,302 | 68 · +19,884 (+29,241.18%) | 423 / 904 |
| 15 | `csmith-expression-and-pointer-modes/ptr2/no-const-pointers/seed-123` | 10,158,890 → 9,693,786 | -465,104 (-4.58%) | 22,153 / 31,119 → 22,119 / 31,085 | 3,234,500 · +6,459,286 (+199.70%) | 5,879 / 32,242 | BUILD case-compile | - |
| 15 | `csmith-expression-and-pointer-modes/ptr2/no-volatile-aggregate-fields/seed-123` | 4,393,790 → 3,927,742 | -466,048 (-10.61%) | 18,170 / 27,136 → 18,136 / 27,102 | 1,655,394 · +2,272,348 (+137.27%) | 3,349 / 29,495 | BUILD case-compile | - |
| 15 | `csmith-remaining-profiles-unmodified/ptr2/no-byte-types/seed-123` | 98,084,742 → 97,619,638 | -465,104 (-0.47%) | 15,157 / 24,123 → 15,123 / 24,089 | 48,789,298 · +48,830,340 (+100.08%) | 4,147 / 30,672 | BUILD case-compile | - |
| 16 | `20020226-1.c` | 113,182 → 109,670 | -3,512 (-3.10%) | 3,808 / 8,574 → 3,552 / 8,318 | 67,768 · +41,902 (+61.83%) | 2,790 / 3,669 | BUILD link | - |
| 16 | `20020508-2.c` | 121,662 → 118,190 | -3,472 (-2.85%) | 4,167 / 8,933 → 3,911 / 8,677 | 71,772 · +46,418 (+64.67%) | 3,007 / 3,886 | BUILD link | - |
| 16 | `pr46019.c` | 42,990 → 39,774 | -3,216 (-7.48%) | 303 / 2,800 → 266 / 2,763 | 68 · +39,706 (+58,391.18%) | 4 / 865 | 68 · +39,706 (+58,391.18%) | 4 / 467 |
| 17 | `memset-2.c` | 2,463,856 → 2,369,008 | -94,848 (-3.85%) | 2,834 / 5,049 → 2,890 / 5,105 | 2,366,380 · +2,628 (+0.11%) | 17,351 / 18,325 | 2,344,956 · +24,052 (+1.03%) | 17,643 / 18,153 |
| 18 | `csmith-expression-and-pointer-modes/ptr2/no-const-pointers/seed-123` | 9,682,378 → 9,315,582 | -366,796 (-3.79%) | 22,095 / 31,061 → 21,599 / 30,565 | 3,234,500 · +6,081,082 (+188.01%) | 5,879 / 32,242 | BUILD case-compile | - |
| 18 | `csmith-expression-and-pointer-modes/ptr2/no-volatile-aggregate-fields/seed-123` | 3,920,110 → 3,676,270 | -243,840 (-6.22%) | 18,112 / 27,078 → 17,616 / 26,582 | 1,655,394 · +2,020,876 (+122.08%) | 3,349 / 29,495 | BUILD case-compile | - |
| 18 | `csmith-remaining-profiles-unmodified/ptr2/no-byte-types/seed-123` | 97,614,102 → 97,435,838 | -178,264 (-0.18%) | 15,099 / 24,065 → 14,603 / 23,569 | 48,789,298 · +48,646,540 (+99.71%) | 4,147 / 30,672 | BUILD case-compile | - |
| 19 | `20040409-1.c` | 9,940 → 9,652 | -288 (-2.90%) | 300 / 2,481 → 292 / 2,473 | 68 · +9,584 (+14,094.12%) | 187 / 1,066 | 68 · +9,584 (+14,094.12%) | 187 / 668 |
| 19 | `20040409-1w.c` | 5,124 → 4,836 | -288 (-5.62%) | 156 / 2,337 → 148 / 2,329 | 68 · +4,768 (+7,011.76%) | 107 / 986 | 68 · +4,768 (+7,011.76%) | 107 / 588 |
| 19 | `20040409-2.c` | 19,952 → 18,472 | -1,480 (-7.42%) | 505 / 2,686 → 457 / 2,638 | 68 · +18,404 (+27,064.71%) | 423 / 1,302 | 68 · +18,404 (+27,064.71%) | 423 / 904 |
| 19 | `20040409-2w.c` | 11,168 → 9,688 | -1,480 (-13.25%) | 293 / 2,474 → 237 / 2,418 | 68 · +9,620 (+14,147.06%) | 233 / 1,112 | 68 · +9,620 (+14,147.06%) | 233 / 714 |
| 19 | `20040409-3.c` | 10,844 → 10,516 | -328 (-3.02%) | 348 / 2,529 → 340 / 2,521 | 68 · +10,448 (+15,364.71%) | 231 / 1,110 | 68 · +10,448 (+15,364.71%) | 231 / 712 |
| 19 | `20040409-3w.c` | 5,596 → 5,268 | -328 (-5.86%) | 180 / 2,361 → 172 / 2,353 | 68 · +5,200 (+7,647.06%) | 129 / 1,008 | 68 · +5,200 (+7,647.06%) | 129 / 610 |
| 20 | `20040409-3.c` | 10,516 → 9,652 | -864 (-8.22%) | 340 / 2,521 → 292 / 2,473 | 68 · +9,584 (+14,094.12%) | 231 / 1,110 | 68 · +9,584 (+14,094.12%) | 231 / 712 |
| 20 | `20040409-3w.c` | 5,268 → 4,836 | -432 (-8.20%) | 172 / 2,353 → 148 / 2,329 | 68 · +4,768 (+7,011.76%) | 129 / 1,008 | 68 · +4,768 (+7,011.76%) | 129 / 610 |

Fix 11 gives the six elementary functions their unsuffixed symbols in the default binary32 ABI. A prototype written without `<math.h>` now links to the binary32 implementation, including through a function pointer. The benchmark confirms that `foo` runs once. Both VBCC builds return zero from the source's `0.0 / 0.0` expression, while zicc passes a NaN to `sqrt`. These are whole-program clocks. The binary32 math object accounts for the linked-code increase. The binary32 entry points pass the new explicit-prototype check in near and banked ROMs.

Fix 12 retries stack-frame conversion when the existing unreachable-code pass can remove the frame references that blocked it. The stack-frame part catches the previously missed conversion and verifies both modes against Mesen and MSVC. Repeated measurements are under `build/slower-f11-after` and `build/slower-f12-after`, using the batch 1 replay as the baseline.

Fix 13 folds a fixed-trip loop that repeatedly updates a separate nonvolatile byte or word, keeping the final induction value. The byte update also avoids linking the arithmetic workspace. Fix 14 combines adjacent constant bit masks of the same operation and width. Both VBCC lanes fold the benchmark checks away. The known-values part covers wrapping byte updates, volatile accesses and bit masks across width changes.

Fix 15 reuses the carry after shifting a 32-bit value right by one to select an XOR mask. The original Csmith checksums match and the change applies to the conditional shift used by the CRC table generator. Fix 16 stages only the low word of 64-bit shift counts, while retaining evaluation of count expressions and volatile loads. The wide codegen part checks the resulting shift setup and both normal and banked ROM paths.

Fix 17 inlines short near `memset` calls when the length is known, with byte or word stores according to the fill value and size. The same optimization leaves `memset-3.c` at 2,347,858 clocks and 1,430 application bytes because its lengths are variable. Fix 18 extracts surviving bytes or words from narrowed wide shifts and skips a mask that preserves all destination bits. Its Csmith measurements include the original checksum work.

Fix 19 replaces addition or subtraction of the high bit with XOR at the same integer width. Fix 20 merges a bitwise complement into a constant XOR mask. The `20040409` cases exercise these patterns while both VBCC builds fold the checks out of `main`. Per-fix ROMs and assembly are in `build/slower-fNN-*`.

The instruction profiler counts executed instructions for each linked code region and checks the timed run and any recorded checksum. In `build/slower-profile-01`, the batch 1 `no-byte-types/seed-123` run spent 2,800,940 instructions in `func_7` compared with 1,116,360 for modified VBCC. The CRC table generator across the two other recorded profiles used 68,105 instructions compared with 33,285 for modified VBCC. These counts identified the conditional-shift pattern fixed in this batch and the remaining cost in the generated test functions.

### Inventory replay after batch 2

All 300 GCC cases passed and all 384 Csmith cases reproduced their checksums. Relative to the inventory zicc run, 74 GCC cases improved, 226 tied, and all 384 Csmith cases improved. Six GCC cases and 342 Csmith cases closed every recorded slower pair for their case. Compared with batch 1, `950512-1.c` gained 608 clocks and `20100209-1.c` gained 388 clocks. Both remain faster than their inventory zicc runs.

The replay records are in `build/slower-b2-g/results.jsonl` and `build/slower-b2-c/results.jsonl`. The 920 pairwise comparisons are in `build/slower-b2-pairs.csv`.

## Batch 3

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21 | `csmith-remaining-profiles-unmodified/ptr2/no-byte-types/seed-123` | 97,435,838 → 94,828,830 | -2,607,008 (-2.68%) | 14,603 / 23,569 → 14,510 / 23,476 | 48,789,298 · +46,039,532 (+94.36%) | 4,147 / 30,672 | BUILD case-compile | - |
| 22 | `cmpdi-1.c` | 1,011,768 → 995,120 | -16,648 (-1.65%) | 1,314 / 3,495 → 1,282 / 3,463 | 383,346 · +611,774 (+159.59%) | 1,148 / 2,027 | BUILD case-compile | - |
| 23 | `20020226-1.c` | 109,670 → 61,006 | -48,664 (-44.37%) | 3,552 / 8,318 → 2,328 / 7,038 | 67,768 · -6,762 (-9.98%) | 2,790 / 3,669 | BUILD link | - |
| 23 | `20020508-2.c` | 118,190 → 86,510 | -31,680 (-26.80%) | 3,911 / 8,677 → 3,187 / 7,953 | 71,772 · +14,738 (+20.53%) | 3,007 / 3,886 | BUILD link | - |
| 23 | `950512-1.c` | 8,844 → 5,082 | -3,762 (-42.54%) | 391 / 2,888 → 251 / 2,692 | 86 · +4,996 (+5,809.30%) | 162 / 1,023 | BUILD link | - |
| 24 | `950612-1.c` | 142,210 → 136,330 | -5,880 (-4.13%) | 934 / 3,171 → 915 / 3,152 | 65,144 · +71,186 (+109.27%) | 919 / 1,798 | BUILD case-compile | - |
| 25 | `950612-1.c` | 136,330 → 131,690 | -4,640 (-3.40%) | 915 / 3,152 → 883 / 3,120 | 65,144 · +66,546 (+102.15%) | 919 / 1,798 | BUILD case-compile | - |
| 26 | `20020226-1.c` | 61,006 → 45,654 | -15,352 (-25.16%) | 2,328 / 7,038 → 1,996 / 6,706 | 67,768 · -22,114 (-32.63%) | 2,790 / 3,669 | BUILD link | - |
| 26 | `20020508-2.c` | 86,510 → 70,854 | -15,656 (-18.10%) | 3,187 / 7,953 → 2,921 / 7,687 | 71,772 · -918 (-1.28%) | 3,007 / 3,886 | BUILD link | - |
| 26 | `20020508-3.c`, `pr40386.c` | 99,262 → 83,566 | -15,696 (-15.81%) | 3,639 / 8,405 → 3,373 / 8,139 | 71,888 · +11,678 (+16.24%) | 3,007 / 3,886 | BUILD link | - |
| 27 | `990127-2.c` | 43,828 → 21,864 | -21,964 (-50.11%) | 207 / 2,388 → 142 / 2,323 | 86 · +21,778 (+25,323.26%) | 101 / 3,056 | 86 · +21,778 (+25,323.26%) | 95 / 2,652 |
| 27 | `991019-1.c` | 112,630 → 57,690 | -54,940 (-48.78%) | 176 / 2,357 → 145 / 2,326 | 46,434 · +11,256 (+24.24%) | 504 / 3,459 | 44,414 · +13,276 (+29.89%) | 462 / 3,019 |
| 28 | `921029-1.c` | 52,750 → 41,702 | -11,048 (-20.94%) | 926 / 3,107 → 857 / 3,038 | 13,830 · +27,872 (+201.53%) | 1,303 / 2,182 | BUILD link | - |
| 29 | `921029-1.c` | 41,702 → 35,982 | -5,720 (-13.72%) | 857 / 3,038 → 823 / 3,004 | 13,830 · +22,152 (+160.17%) | 1,303 / 2,182 | BUILD link | - |
| 30 | `921029-1.c` | 35,982 → 30,242 | -5,740 (-15.95%) | 823 / 3,004 → 783 / 2,964 | 13,830 · +16,412 (+118.67%) | 1,303 / 2,182 | BUILD link | - |

Fix 21 increments and compares only the low word of a private 64-bit induction variable when constant bounds prove that its upper words stay zero. The Csmith checksum matches. Fix 22 transfers the four words directly for discarded assignments between distinct nonvolatile objects, including a dynamic index into a known near array. Fix 23 uses the initializer evaluator's integer arithmetic rules to fold literal 64-bit operators, removing the corresponding work from each program. Modified VBCC folds the checks in `950512-1.c` out of `main`.

Fix 24 reads representation-preserving signedness casts from the original 64-bit storage. Fix 25 computes negation and complement directly from fixed storage into the result slot. Fix 26 merges complementary constant shifts of the same 64-bit object into a word permutation and a short rotate loop. Arithmetic right shifts retain their sign fill.

Fix 27 folds finite literal arithmetic in binary32, whose runtime uses fixed round-to-nearest, ties-to-even. The binary64 path retains its runtime rounding mode and exception behavior. Both VBCC builds eliminate the calculation and check from `main` in `990127-2.c`. The zicc change folds the literal calculation while keeping the calculation that uses the function arguments.

Fix 28 updates only affected words of a nonvolatile fixed 64-bit object when applying a constant mask. Fix 29 moves words in the fixed object when shifting in place by whole words. Fix 30 widens a narrow integer directly into the destination. Together they cut `921029-1.c` by 22,508 clocks (42.67%) and 143 application bytes, and retain the observable global writes.

Repeated timing evidence is in `build/slower-f21-after`, `build/slower-f22-copy`, and `build/slower-f23-after` through `build/slower-f30-after`. Focused checks covered signed shifts, rotations, masks, near and banked ROMs, static initializers, and both floating-point ABI modes.

`20010925-1.c` declares `memcpy` with a near source pointer. In the original zicc image the source went in A and the count was the only stack argument, while the runtime read a far source and a count from the stack. The test checks the function's return code and leaves the destination unchecked. Fix 54 resolves the prototype mismatch. The original timing is invalid for copy throughput.

### Inventory replay after batch 3

All 300 GCC cases passed and all 384 Csmith cases reproduced their checksums. Relative to the inventory zicc run, 79 GCC cases improved, 221 tied, and all 384 Csmith cases improved. Twelve GCC cases and 342 Csmith cases closed every recorded VBCC gap for their case. Compared with batch 2, four Csmith cases gained 9,838–10,056 clocks (0.55–0.69%). The two affected seeds each ran 426 extra instructions in the console runtime, while their hottest generated functions retained the same instruction counts. The per-ROM profiles are in `build/slower-profile-b3-regressions`.

The replay records are in `build/slower-b3-g/results.jsonl` and `build/slower-b3-c/results.jsonl`. The summary tool verifies case coverage, source identities across replays, and Csmith checksums, then saves all 920 comparisons.


## Batch 4

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 31 | `cmpdi-1.c` | 995,120 → 475,600 | -519,520 (-52.21%) | 1,282 / 3,463 → 1,232 / 3,413 | 383,346 · +92,254 (+24.07%) | 1,148 / 2,027 | BUILD case-compile | - |
| 32 | `20001031-1.c` | 2,874 → 2,686 | -188 (-6.54%) | 253 / 2,434 → 243 / 2,424 | 722 · +1,964 (+272.02%) | 128 / 1,007 | BUILD link | - |
| 32 | `20001112-1.c` | 3,376 → 3,206 | -170 (-5.04%) | 186 / 2,698 → 179 / 2,691 | 86 · +3,120 (+3,627.91%) | 11 / 872 | 86 · +3,120 (+3,627.91%) | 11 / 474 |
| 32 | `20020508-2.c` | 70,854 → 68,486 | -2,368 (-3.34%) | 2,921 / 7,687 → 2,777 / 7,543 | 71,772 · -3,286 (-4.58%) | 3,007 / 3,886 | BUILD link | - |
| 32 | `20020508-3.c`, `pr40386.c` | 83,566 → 77,934 | -5,632 (-6.74%) | 3,373 / 8,139 → 3,021 / 7,787 | 71,888 · +6,046 (+8.41%) | 3,007 / 3,886 | BUILD link | - |
| 32 | `20060127-1.c` | 1,436 → 1,026 | -410 (-28.55%) | 102 / 2,283 → 71 / 2,252 | 300 · +726 (+242.00%) | 48 / 927 | BUILD case-compile | - |
| 32 | `921202-2.c` | 2,442 → 2,134 | -308 (-12.61%) | 154 / 2,595 → 132 / 2,573 | 156 · +1,978 (+1,267.95%) | 56 / 935 | BUILD case-compile | - |
| 32 | `950512-1.c` | 5,082 → 4,742 | -340 (-6.69%) | 251 / 2,692 → 244 / 2,685 | 86 · +4,656 (+5,413.95%) | 162 / 1,023 | BUILD link | - |
| 32 | `longlong.c` | 7,606 → 6,990 | -616 (-8.10%) | 499 / 2,940 → 455 / 2,896 | 5,550 · +1,440 (+25.95%) | 773 / 1,652 | BUILD case-compile | - |
| 33 | `950704-1.c` | 16,934 → 15,102 | -1,832 (-10.82%) | 530 / 2,711 → 514 / 2,695 | 126 · +14,976 (+11,885.71%) | 270 / 1,131 | BUILD case-compile | - |
| 34 | `20060127-1.c` | 1,026 → 626 | -400 (-38.99%) | 71 / 2,252 → 45 / 443 | 300 · +326 (+108.67%) | 48 / 927 | BUILD case-compile | - |
| 35 | `cmpdi-1.c` | 475,600 → 380,880 | -94,720 (-19.92%) | 1,232 / 3,413 → 1,352 / 3,533 | 383,346 · -2,466 (-0.64%) | 1,148 / 2,027 | BUILD case-compile | - |
| 36 | `no-volatile-aggregate-fields/seed-123` | 3,676,006 → 2,813,754 | -862,252 (-23.46%) | 16,926 / 25,892 → 16,757 / 25,723 | 1,655,394 · +1,158,360 (+69.97%) | 3,349 / 29,495 | BUILD case-compile | - |
| 36 | `no-byte-types/seed-123` | 94,824,006 → 94,325,998 | -498,008 (-0.53%) | 13,818 / 22,784 → 13,792 / 22,758 | 48,789,298 · +45,536,700 (+93.33%) | 4,147 / 30,672 | BUILD case-compile | - |
| 36 | `no-local-addresses/seed-17`, `no-signed-char-index/seed-17` | 1,184,004 → 1,145,176 | -38,828 (-3.28%) | 9,238 / 18,204 → 9,177 / 18,143 | 1,274,300 · -129,124 (-10.13%) | 1,707 / 27,853 | BUILD case-compile | - |
| 37 | `no-byte-types/seed-123` | 94,325,998 → 93,571,230 | -754,768 (-0.80%) | 13,792 / 22,758 → 13,714 / 22,680 | 48,789,298 · +44,781,932 (+91.79%) | 4,147 / 30,672 | BUILD case-compile | - |
| 37 | `no-local-addresses/seed-17`, `no-signed-char-index/seed-17` | 1,145,176 → 1,144,092 | -1,084 (-0.09%) | 9,177 / 18,143 → 9,069 / 18,035 | 1,274,300 · -130,208 (-10.22%) | 1,707 / 27,853 | BUILD case-compile | - |
| 38 | `950612-1.c` | 131,690 → 78,650 | -53,040 (-40.28%) | 883 / 3,120 → 627 / 2,808 | 65,144 · +13,506 (+20.73%) | 919 / 1,798 | BUILD case-compile | - |
| 39 | `no-byte-types/seed-123` | 93,546,452 → 86,310,574 | -7,235,878 (-7.74%) | 13,659 / 22,625 → 13,362 / 22,328 | 48,789,298 · +37,521,276 (+76.90%) | 4,147 / 30,672 | BUILD case-compile | - |
| 39 | `no-volatile-aggregate-fields/seed-123` | 2,813,754 → 2,786,294 | -27,460 (-0.98%) | 16,721 / 25,687 → 16,314 / 25,280 | 1,655,394 · +1,130,900 (+68.32%) | 3,349 / 29,495 | BUILD case-compile | - |
| 39 | `mutable-constant-markers/seed-123`, `no-uniformity-constraint/seed-123` | 1,756,334 → 1,718,144 | -38,190 (-2.17%) | 17,074 / 26,040 → 16,622 / 25,588 | 1,832,668 · -114,524 (-6.25%) | 4,624 / 31,053 | BUILD case-compile | - |
| 40 | `no-byte-types/seed-123` | 86,310,574 → 83,349,044 | -2,961,530 (-3.43%) | 13,362 / 22,328 → 13,226 / 22,192 | 48,789,298 · +34,559,746 (+70.83%) | 4,147 / 30,672 | BUILD case-compile | - |
| 40 | `no-volatile-aggregate-fields/seed-123` | 2,786,294 → 2,772,374 | -13,920 (-0.50%) | 16,314 / 25,280 → 16,252 / 25,218 | 1,655,394 · +1,116,980 (+67.48%) | 3,349 / 29,495 | BUILD case-compile | - |
| 40 | `mutable-constant-markers/seed-123`, `no-uniformity-constraint/seed-123` | 1,718,144 → 1,716,770 | -1,374 (-0.08%) | 16,622 / 25,588 → 16,548 / 25,514 | 1,832,668 · -115,898 (-6.32%) | 4,624 / 31,053 | BUILD case-compile | - |

The Csmith rows use `ptr2` cases from `csmith-expression-and-pointer-modes`, with `no-byte-types` from `csmith-remaining-profiles-unmodified`. Every reported Csmith timing reproduced the baseline checksum. `build/slower-f31-complete`, `build/slower-f32-after` through `build/slower-f37-after`, `build/slower-f38-mixed-after`, and `build/slower-f39-after` through `build/slower-f40-after` hold the ROMs, assembly and repeated run logs.

Fix 31 substitutes comparisons between two 64-bit parameters from simple same-unit helpers, honoring explicit `noinline` and keeping volatile arguments on the call path. The `cmpdi-1.c` result table still validates every comparison. Fix 35 then compares the high words first and stops as soon as they differ, with signed ordering on the highest word and unsigned ordering below. Modified VBCC also inlines the comparison helpers and executes the checks.

Fix 32 uses an immediate operand for each affected word of a wide arithmetic or bitwise operation. Fix 33 reads both fixed operands directly. Fix 34 tests a constant mask without constructing a wide temporary and can skip linking arithmetic scratch. Fix 38 compares a wide result directly with the words of a narrower fixed operand and its sign or zero extension.

Fix 36 updates fixed nonvolatile wide storage directly and stops carrying or borrowing once the discarded result is settled. Fixes 37 and 39 discard constant writes and stack slots for unread automatic arrays, first for fixed offsets and then for side-effect-free indexed accesses. Fix 40 replaces finite empty loops with the final counter value. In the timed `no-byte-types` Csmith case, the outer `func_7` loop had initialized several unread arrays in its inner loops. Its workload still computes the original checksum after eliminating those writes.

### Inventory replay after batch 4

All 300 GCC cases passed and all 384 Csmith cases reproduced their checksums. Relative to the original inventory, 83 GCC cases and all 384 Csmith cases are faster. Fourteen GCC cases and 346 Csmith cases closed all of their recorded VBCC gaps. The two pointer profiles of `no-globals/seed-17` gained 10,070 clocks (0.92%) from batch 3. The affected ROM executes 426 more console instructions and twelve fewer instructions in its hottest generated function. See `build/slower-profile-b4-regressions`.

The replay records are in `build/slower-b4-g/results.jsonl` and `build/slower-b4-c/results.jsonl`, with all 920 comparisons in `build/slower-b4-pairs-verified.csv`. The profile runner checks the archived zicc ROM hashes and repeats the timing and checksum assertions for each remaining comparison. It matched all 880 ROMs covering the 324 cases with gaps after batch 4. Across the batch 3 evidence, it ran 893 ROMs for 330 cases. In 122 GCC cases the fastest VBCC ROM executed at most four profiled instructions, and in another 72 it executed at most twenty. These cases primarily measure how much work each compiler removes from the whole program. The other 94 GCC cases and all 42 Csmith cases spent more than twenty instructions in the fastest VBCC run.


## Batch 5

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 41 | `conversion.c` | 92,754 → 80,478 | -12,276 (-13.24%) | 1,861 / 4,429 → 1,807 / 4,375 | 8,530 · +71,948 (+843.47%) | 842 / 3,885 | 8,530 · +71,948 (+843.47%) | 808 / 3,365 |
| 42 | `conversion.c` | 80,478 → 80,396 | -82 (-0.10%) | 1,807 / 4,375 → 1,794 / 4,362 | 8,530 · +71,866 (+842.51%) | 842 / 3,885 | 8,530 · +71,866 (+842.51%) | 808 / 3,365 |
| 43 | `conversion.c` | 80,396 → 64,902 | -15,494 (-19.27%) | 1,794 / 4,362 → 1,346 / 3,914 | 8,530 · +56,372 (+660.87%) | 842 / 3,885 | 8,530 · +56,372 (+660.87%) | 808 / 3,365 |
| 43 | `cvt-1.c` | 31,986 → 30,442 | -1,544 (-4.83%) | 310 / 2,878 → 279 / 2,847 | 4,340 · +26,102 (+601.43%) | 197 / 3,370 | FAIL abort | - |
| 44 | `conversion.c` | 64,902 → 50,942 | -13,960 (-21.51%) | 1,346 / 3,914 → 922 / 3,490 | 8,530 · +42,412 (+497.21%) | 842 / 3,885 | 8,530 · +42,412 (+497.21%) | 808 / 3,365 |
| 44 | `cvt-1.c` | 30,442 → 30,544 | +102 (+0.34%) | 279 / 2,847 → 283 / 2,851 | 4,340 · +26,204 (+603.78%) | 197 / 3,370 | FAIL abort | - |
| 45 | `cvt-1.c` | 30,544 → 28,276 | -2,268 (-7.43%) | 283 / 2,851 → 259 / 2,827 | 4,340 · +23,936 (+551.52%) | 197 / 3,370 | FAIL abort | - |
| 45 | `conversion.c` | 50,942 → 50,828 | -114 (-0.22%) | 922 / 3,490 → 914 / 3,482 | 8,530 · +42,298 (+495.87%) | 842 / 3,885 | 8,530 · +42,298 (+495.87%) | 808 / 3,365 |
| 45 | `ieee/compare-fp-2.c` | 392 → 60 | -332 (-84.69%) | 99 / 2,667 → 69 / 2,623 | 68 · -8 (-11.76%) | 109 / 3,134 | 68 · -8 (-11.76%) | 103 / 2,642 |
| 46 | `conversion.c` | 50,828 → 50,444 | -384 (-0.76%) | 914 / 3,482 → 887 / 3,455 | 8,530 · +41,914 (+491.37%) | 842 / 3,885 | 8,530 · +41,914 (+491.37%) | 808 / 3,365 |
| 47 | `ieee/pr29302-1.c` | 6,828 → 1,036 | -5,792 (-84.83%) | 103 / 2,671 → 48 / 2,229 | 138 · +898 (+650.72%) | 16 / 895 | 138 · +898 (+650.72%) | 16 / 497 |
| 48 | `ieee/pr29302-1.c` | 1,036 → 60 | -976 (-94.21%) | 48 / 2,229 → 4 / 388 | 138 · -78 (-56.52%) | 16 / 895 | 138 · -78 (-56.52%) | 16 / 497 |
| 48 | `conversion.c` | 50,444 → 49,926 | -518 (-1.03%) | 887 / 3,455 → 836 / 3,404 | 8,530 · +41,396 (+485.30%) | 842 / 3,885 | 8,530 · +41,396 (+485.30%) | 808 / 3,365 |
| 49 | `990127-2.c` | 21,864 → 58 | -21,806 (-99.73%) | 142 / 2,323 → 121 / 2,302 | 86 · -28 (-32.56%) | 101 / 3,056 | 86 · -28 (-32.56%) | 95 / 2,652 |
| 49 | `ieee/unsafe-fp-assoc.c` | 6,214 → 5,896 | -318 (-5.12%) | 107 / 2,288 → 158 / 2,339 | 68 · +5,828 (+8,570.59%) | 64 / 3,001 | 68 · +5,828 (+8,570.59%) | 62 / 2,601 |
| 50 | `ieee/unsafe-fp-assoc.c` | 5,896 → 60 | -5,836 (-98.98%) | 158 / 2,339 → 61 / 2,228 | 68 · -8 (-11.76%) | 64 / 3,001 | 68 · -8 (-11.76%) | 62 / 2,601 |

Fix 41 folds integer-to-binary32 casts exposed by propagation. Fix 42 folds binary32 comparisons and refolds arithmetic after propagation. Fix 43 tracks exact binary32 literals in private scalars, and fix 44 removes private binary32 stores whose values are dead. Fix 45 applies the existing in-range binary32-to-integer conversion before later optimizations run. Fix 46 folds unary sign and truth operations, including negative zero.

Fix 47 folds runtime divisions of nonzero finite binary32 literals by zero to the appropriate signed infinity. Static initializers retain their existing diagnostics. Fix 48 folds comparisons of infinity and NaN literals using IEEE ordering. The binary64 paths retain their runtime environment and exception behavior.

Fix 49 raises the normal inlining budget for loop-free functions called with all-literal numeric arguments and bounded local storage. The initial experiment also applied the budget to functions with loops. Restricting it to loop-free functions restored the batch 4 timings for `20100805-1.c`, `990527-1.c`, and `920731-1.c`. Fix 50 substitutes initialized nonvolatile static binary32 constants on value reads. In `990127-2.c`, `pr29302-1.c`, and `unsafe-fp-assoc.c`, the final timings describe whole programs that eliminate the original arithmetic and checks. The `build/slower-f41-after` through `build/slower-f50-after` directories and `build/slower-f49-loop-retake` retain the timing and size evidence.

### Inventory replay after batch 5

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 4, 48 GCC cases improved and 252 tied. All Csmith timings tied. Across the five batches, 128 GCC cases and all 384 Csmith cases are faster than the original inventory. Thirty-five GCC cases and 346 Csmith cases have closed all of their recorded VBCC gaps. The profiler reproduced the clocks and checksums from 818 ROMs covering the 303 remaining cases.

The replay records are in `build/slower-b5-final-g/results.jsonl` and `build/slower-b5-final-c/results.jsonl`. The 920 comparisons are in `build/slower-b5-final-pairs.csv`, and the region profiles are in `build/slower-b5-final-profiles/results.jsonl`.

## Batch 6

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 51 | `950512-1.c` | 4,742 → 1,348 | -3,394 (-71.57%) | 244 / 2,685 → 263 / 2,704 | 86 · +1,262 (+1,467.44%) | 162 / 1,023 | BUILD link | - |
| 52 | `950512-1.c` | 1,348 → 518 | -830 (-61.57%) | 263 / 2,704 → 170 / 2,611 | 86 · +432 (+502.33%) | 162 / 1,023 | BUILD link | - |
| 53 | `950512-1.c` | 518 → 58 | -460 (-88.80%) | 170 / 2,611 → 139 / 2,580 | 86 · -28 (-32.56%) | 162 / 1,023 | BUILD link | - |
| 54 | `20010925-1.c` | 70,310 (invalid copy) → 1,480 | -68,830 recorded (-97.90%) | 60 / 574 → 60 / 475 | 1,960 · -480 (-24.49%) | 83 / 1,010 | 2,000 · -520 (-26.00%) | 81 / 610 |
| 55 | `memset-3.c` | 2,347,858 → 2,344,588 | -3,270 (-0.14%) | 1,430 / 3,645 → 1,400 / 3,615 | 2,287,660 · +56,928 (+2.49%) | 7,791 / 8,765 | 2,292,824 · +51,764 (+2.26%) | 8,012 / 8,522 |
| 56 | `memset-3.c` | 2,344,588 → 2,282,826 | -61,762 (-2.63%) | 1,400 / 3,615 → 1,034 / 3,249 | 2,287,660 · -4,834 (-0.21%) | 7,791 / 8,765 | 2,292,824 · -9,998 (-0.44%) | 8,012 / 8,522 |
| 57 | `pr19005.c` | 578,422 → 573,294 | -5,128 (-0.89%) | 202 / 2,383 → 196 / 2,377 | 477,474 · +95,820 (+20.07%) | 492 / 1,371 | 518,418 · +54,876 (+10.59%) | 502 / 983 |
| 58 | `memset-2.c` | 2,369,008 → 2,279,800 | -89,208 (-3.77%) | 2,890 / 5,105 → 1,958 / 4,173 | 2,366,380 · -86,580 (-3.66%) | 17,351 / 18,325 | 2,344,956 · -65,156 (-2.78%) | 17,643 / 18,153 |
| 59 | `memset-2.c` | 2,279,800 → 2,275,936 | -3,864 (-0.17%) | 1,958 / 4,173 → 1,958 / 4,173 | 2,366,380 · -90,444 (-3.82%) | 17,351 / 18,325 | 2,344,956 · -69,020 (-2.94%) | 17,643 / 18,153 |
| 59 | `memset-3.c` | 2,282,826 → 2,274,002 | -8,824 (-0.39%) | 1,034 / 3,249 → 1,034 / 3,249 | 2,287,660 · -13,658 (-0.60%) | 7,791 / 8,765 | 2,292,824 · -18,822 (-0.82%) | 8,012 / 8,522 |
| 60 | `memset-2.c` | 2,275,936 → 2,254,756 | -21,180 (-0.93%) | 1,958 / 4,173 → 2,055 / 4,270 | 2,366,380 · -111,624 (-4.72%) | 17,351 / 18,325 | 2,344,956 · -90,200 (-3.85%) | 17,643 / 18,153 |

Fix 51 evaluates same-unit single-return wide integer helpers with literal arguments, honoring `noinline`. Fix 52 refolds the surrounding expressions after substitution. Fix 53 reclassifies callers where that removes all wide evaluation, making them eligible for the regular optimizer. Both zicc and modified VBCC remove the checked work in `950512-1.c`. Runtime binary32 folding now runs after parsing, preserving the prohibition on floating arithmetic inside integer constant expressions such as enum values.

Fix 54 supplies the target's `__SIZE_TYPE__` and maps the standard near-source `memcpy` prototype to a helper that takes its source in A. The public far-source entry retains its ABI and bank progression. Direct and function-pointer fixtures check the copied bytes and returned pointer. They exercise zero length and the allocation builder's four stages.

Fixes 55 and 56 propagate the `memset` result when its destination is a fixed near address, first for whole objects and member bases and then for constant offsets into member arrays. Fix 57 preserves known zero bits of stack words across direct calls when the function has no observable frame addresses. Fix 58 tracks destinations computed from private pointer or index values, invalidates the fact when they change, and simplifies comparisons against the same address expression. Fix 59 shortens the variable-length runtime's setup. Fix 60 uses up to eight direct byte stores for short fills with runtime values. The `memset` tests continue to check each filled byte and its neighbors. The `build/slower-f51-before` through `build/slower-f60-after` directories hold the ROMs and repeat measurements.

### Inventory replay after batch 6

All 300 GCC runs passed and all 384 Csmith checksums matched. Eleven GCC cases improved over batch 5, and the other 289 GCC and 384 Csmith timings tied. Forty-two GCC cases and 346 Csmith cases have closed every recorded VBCC gap for their case. The 296 remaining cases account for 801 ROMs in the profile pass, which reproduced their recorded clocks and checksums.

The replay records are in `build/slower-b6-final-g/results.jsonl` and `build/slower-b6-final-c/results.jsonl`. The 920 comparisons are in `build/slower-b6-final-pairs.csv`, and the profiles are in `build/slower-b6-final-profiles/results.jsonl`. Six cases outside the isolated fix measurements improved during the batch.

| Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC result | Stock code bytes app / linked |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `divconst-3.c` | 22,908 → 58 | -22,850 (-99.75%) | 159 / 3,332 → 55 / 3,228 | 1,092 · -1,034 (-94.69%) | 167 / 1,725 | BUILD link | - |
| `20050111-1.c` | 3,834 → 2,222 | -1,612 (-42.04%) | 215 / 2,396 → 159 / 2,340 | 1,250 · +972 (+77.76%) | 212 / 1,091 | BUILD case-compile | - |
| `multdi-1.c` | 14,704 → 700 | -14,004 (-95.24%) | 182 / 2,694 → 172 / 2,684 | 252 · +448 (+177.78%) | 142 / 1,892 | BUILD link | - |
| `20100209-1.c` | 2,036 → 60 | -1,976 (-97.05%) | 93 / 2,534 → 79 / 2,506 | 138 · -78 (-56.52%) | 100 / 979 | BUILD case-compile | - |
| `920604-1.c` | 2,268 → 188 | -2,080 (-91.71%) | 94 / 3,267 → 72 / 3,245 | 86 · +102 (+118.60%) | 82 / 1,622 | BUILD case-compile | - |
| `960402-1.c` | 1,028 → 58 | -970 (-94.36%) | 118 / 516 → 87 / 485 | 86 · -28 (-32.56%) | 98 / 959 | BUILD link | - |


## Batch 7

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 61 | `no-const-pointers/seed-123` | 8,825,358 → 8,824,558 | -800 (-0.01%) | 20,091 / 29,057 → 19,943 / 28,909 | 3,234,500 · +5,590,058 (+172.83%) | 5,879 / 32,242 | BUILD case-compile | - |
| 61 | `no-volatile-aggregate-fields/seed-123` | 2,772,374 → 2,761,914 | -10,460 (-0.38%) | 16,252 / 25,218 → 15,959 / 24,925 | 1,655,394 · +1,106,520 (+66.84%) | 3,349 / 29,495 | BUILD case-compile | - |
| 61 | `no-byte-types/seed-123` | 83,349,044 → 78,189,098 | -5,159,946 (-6.19%) | 13,226 / 22,192 → 13,053 / 22,019 | 48,789,298 · +29,399,800 (+60.26%) | 4,147 / 30,672 | BUILD case-compile | - |
| 62 | `no-byte-types/seed-123` | 78,189,098 → 29,107,090 | -49,082,008 (-62.77%) | 13,053 / 22,019 → 12,638 / 21,604 | 48,789,298 · -19,682,208 (-40.34%) | 4,147 / 30,672 | BUILD case-compile | - |
| 63 | `no-const-pointers/seed-123` | 8,824,558 → 8,824,558 | +0 (+0.00%) | 19,943 / 28,909 → 19,934 / 28,900 | 3,234,500 · +5,590,058 (+172.83%) | 5,879 / 32,242 | BUILD case-compile | - |
| 63 | `no-byte-types/seed-123` | 29,107,090 → 28,863,726 | -243,364 (-0.84%) | 12,638 / 21,604 → 12,581 / 21,547 | 48,789,298 · -19,925,572 (-40.84%) | 4,147 / 30,672 | BUILD case-compile | - |
| 64 | `no-volatile-aggregate-fields/seed-123` | 2,761,914 → 2,743,694 | -18,220 (-0.66%) | 15,959 / 24,925 → 15,867 / 24,833 | 1,655,394 · +1,088,300 (+65.74%) | 3,349 / 29,495 | BUILD case-compile | - |
| 65 | `no-const-pointers/seed-123` | 8,824,558 → 8,822,346 | -2,212 (-0.03%) | 19,934 / 28,900 → 19,819 / 28,785 | 3,234,500 · +5,587,846 (+172.76%) | 5,879 / 32,242 | BUILD case-compile | - |
| 65 | `no-volatile-aggregate-fields/seed-123` | 2,743,694 → 2,741,982 | -1,712 (-0.06%) | 15,867 / 24,833 → 15,775 / 24,741 | 1,655,394 · +1,086,588 (+65.64%) | 3,349 / 29,495 | BUILD case-compile | - |
| 65 | `no-byte-types/seed-123` | 28,863,726 → 27,144,464 | -1,719,262 (-5.96%) | 12,581 / 21,547 → 12,555 / 21,521 | 48,789,298 · -21,644,834 (-44.36%) | 4,147 / 30,672 | BUILD case-compile | - |
| 66 | `no-const-pointers/seed-123` | 8,822,346 → 8,805,278 | -17,068 (-0.19%) | 19,819 / 28,785 → 19,765 / 28,731 | 3,234,500 · +5,570,778 (+172.23%) | 5,879 / 32,242 | BUILD case-compile | - |
| 66 | `no-volatile-aggregate-fields/seed-123` | 2,741,982 → 2,731,040 | -10,942 (-0.40%) | 15,775 / 24,741 → 15,664 / 24,630 | 1,655,394 · +1,075,646 (+64.98%) | 3,349 / 29,495 | BUILD case-compile | - |
| 66 | `no-byte-types/seed-123` | 27,144,464 → 25,045,584 | -2,098,880 (-7.73%) | 12,555 / 21,521 → 12,516 / 21,482 | 48,789,298 · -23,743,714 (-48.67%) | 4,147 / 30,672 | BUILD case-compile | - |
| 67 | `no-const-pointers/seed-123` | 8,805,278 → 8,759,510 | -45,768 (-0.52%) | 19,765 / 28,731 → 19,733 / 28,699 | 3,234,500 · +5,525,010 (+170.81%) | 5,879 / 32,242 | BUILD case-compile | - |
| 67 | `no-volatile-aggregate-fields/seed-123` | 2,731,040 → 2,731,040 | +0 (+0.00%) | 15,664 / 24,630 → 15,652 / 24,618 | 1,655,394 · +1,075,646 (+64.98%) | 3,349 / 29,495 | BUILD case-compile | - |
| 67 | `no-byte-types/seed-123` | 25,045,584 → 25,045,584 | +0 (+0.00%) | 12,516 / 21,482 → 12,496 / 21,462 | 48,789,298 · -23,743,714 (-48.67%) | 4,147 / 30,672 | BUILD case-compile | - |
| 68 | `950511-1.c` | 27,118 → 25,918 | -1,200 (-4.43%) | 242 / 2,754 → 170 / 2,682 | 86 · +25,832 (+30037.21%) | 11 / 872 | 86 · +25,832 (+30037.21%) | 11 / 474 |
| 68 | `no-const-pointers/seed-123` | 8,759,510 → 8,665,502 | -94,008 (-1.07%) | 19,733 / 28,699 → 19,252 / 28,218 | 3,234,500 · +5,431,002 (+167.91%) | 5,879 / 32,242 | BUILD case-compile | - |
| 68 | `no-volatile-aggregate-fields/seed-123` | 2,731,040 → 2,707,204 | -23,836 (-0.87%) | 15,652 / 24,618 → 15,261 / 24,227 | 1,655,394 · +1,051,810 (+63.54%) | 3,349 / 29,495 | BUILD case-compile | - |
| 68 | `no-byte-types/seed-123` | 25,045,584 → 23,206,340 | -1,839,244 (-7.34%) | 12,496 / 21,462 → 12,395 / 21,361 | 48,789,298 · -25,582,958 (-52.44%) | 4,147 / 30,672 | BUILD case-compile | - |
| 69 | `pr42721.c` | 3,890 → 3,718 | -172 (-4.42%) | 240 / 3,413 → 226 / 3,399 | 4,700 · -982 (-20.89%) | 125 / 1,683 | BUILD pr42721-compile | - |
| 69 | `pr46019.c` | 39,774 → 38,598 | -1,176 (-2.96%) | 266 / 2,763 → 257 / 2,754 | 68 · +38,530 (+56661.76%) | 4 / 865 | 68 · +38,530 (+56661.76%) | 4 / 467 |
| 69 | `no-volatile-aggregate-fields/seed-123` | 2,707,204 → 2,707,204 | +0 (+0.00%) | 15,261 / 24,227 → 15,228 / 24,194 | 1,655,394 · +1,051,810 (+63.54%) | 3,349 / 29,495 | BUILD case-compile | - |
| 69 | `no-byte-types/seed-123` | 23,206,340 → 23,202,610 | -3,730 (-0.02%) | 12,395 / 21,361 → 12,208 / 21,174 | 48,789,298 · -25,586,688 (-52.44%) | 4,147 / 30,672 | BUILD case-compile | - |
| 70 | `950511-1.c` | 25,918 → 58 | -25,860 (-99.78%) | 170 / 2,682 → 10 / 408 | 86 · -28 (-32.56%) | 11 / 872 | 86 · -28 (-32.56%) | 11 / 474 |
| 70 | `no-const-pointers/seed-123` | 8,665,502 → 8,591,550 | -73,952 (-0.85%) | 19,252 / 28,218 → 18,971 / 27,937 | 3,234,500 · +5,357,050 (+165.62%) | 5,879 / 32,242 | BUILD case-compile | - |
| 70 | `no-volatile-aggregate-fields/seed-123` | 2,707,204 → 2,674,238 | -32,966 (-1.22%) | 15,228 / 24,194 → 14,809 / 23,775 | 1,655,394 · +1,018,844 (+61.55%) | 3,349 / 29,495 | BUILD case-compile | - |
| 70 | `no-byte-types/seed-123` | 23,202,610 → 17,781,226 | -5,421,384 (-23.37%) | 12,208 / 21,174 → 11,798 / 20,764 | 48,789,298 · -31,008,072 (-63.56%) | 4,147 / 30,672 | BUILD case-compile | - |

The Csmith rows use the pinned `ptr2` cases. The checksum for `no-byte-types/seed-123` is `a1138204` throughout. The large change in work comes from deleting an unread scalar and the otherwise pure integer computations feeding it. New separate-unit cases keep observable argument effects and check that the dead stores and pure calls disappear.

Fix 61 removes automatic 32-bit integer homes that are written and never read, preserving observable RHS evaluation. Fix 62 proves that simple same-unit single-return integer functions have no observable work when neither their result nor argument values are needed. Fix 63 extends this proof to standalone discarded calls and Fix 64 applies dead-store removal to 64-bit integer homes. Fix 65 removes finite nestable loops over unobserved private counters when the body is empty. Fix 66 retains the final store when the counter is observed and covers 32-bit counters. Fix 67 eliminates a discarded call with one effectful argument and evaluates that argument once.

Fix 68 enables structured value forwarding in functions with wide operations while preserving expressions with nested updates. Fix 69 tracks all 64 bits of a private integer literal, compares both limbs at joins, and branches directly on integer literals. Fix 70 forwards the old value in a private plain assignment before forgetting it, removes dead pointer homes, and reruns propagation when their addresses become unescaped. When wide evaluation is eliminated, the ordinary optimizer can handle the function. In `950511-1.c` this removes the multiply and check, making its timing a whole-program comparison. A timeout in one run of the byte-identical modified VBCC ROM was checked using the recorded passing ROM with the same hash.

The `build/slower-f61-first` through `build/slower-f67-first` directories hold the first seven isolated runs. Fixes 68 and 69 use `build/slower-f68-verified-{g,c}` and `build/slower-f69-verified-{g,c}`. Fix 70 uses the finalized GCC replay and `build/slower-b7-c-sequencing-only`. These retain the assembly, size evidence, and repeated measurements.

### Inventory replay after batch 7

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 6, 17 GCC cases improved and 283 tied. In Csmith, 366 improved, eight tied, and ten slowed by 0.65–0.88%. The largest slowdown was 9,476 master clocks in the two pointer variants of `no-post-increment/seed-42`. Forty-eight GCC cases and 366 Csmith cases have closed every recorded VBCC gap for their case, leaving 270 cases.

The replay records are in `build/slower-b7-verified-g/results.jsonl` and `build/slower-b7-verified-c/results.jsonl`. The 920 comparisons are in `build/slower-b7-verified-pairs.csv`. All 744 ROM profiles for the remaining cases matched the recorded clocks and checksums in `build/slower-b7-verified-profiles/results.jsonl`.


## Batch 8

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 71 | `pr46019.c` | 38,598 → 60 | -38,538 (-99.84%) | 257 / 2,754 → 4 / 388 | 68 · -8 (-11.76%) | 4 / 865 | 68 · -8 (-11.76%) | 4 / 467 |
| 72 | `20000503-1.c` | 306 → 58 | -248 (-81.05%) | 50 / 448 → 26 / 424 | 86 · -28 (-32.56%) | 35 / 896 | 86 · -28 (-32.56%) | 45 / 508 |
| 72 | `20000511-1.c` | 5,820 → 5,522 | -298 (-5.12%) | 288 / 686 → 281 / 679 | 3,892 · +1,630 (+41.88%) | 261 / 1,357 | 3,932 · +1,590 (+40.44%) | 261 / 959 |
| 72 | `20000715-1.c` | 3,664 → 3,422 | -242 (-6.60%) | 414 / 812 → 393 / 791 | 190 · +3,232 (+1701.05%) | 137 / 1,016 | 190 · +3,232 (+1701.05%) | 137 / 618 |
| 72 | `20040309-1.c` | 566 → 60 | -506 (-89.40%) | 80 / 478 → 20 / 404 | 114 · -54 (-47.37%) | 45 / 924 | 114 · -54 (-47.37%) | 48 / 529 |
| 72 | `20040319-1.c` | 138 → 58 | -80 (-57.97%) | 29 / 427 → 22 / 420 | 86 · -28 (-32.56%) | 43 / 904 | 86 · -28 (-32.56%) | 58 / 521 |
| 72 | `20040820-1.c` | 138 → 58 | -80 (-57.97%) | 92 / 2,273 → 85 / 2,266 | 86 · -28 (-32.56%) | 61 / 940 | 86 · -28 (-32.56%) | 61 / 542 |
| 72 | `20040831-1.c` | 342 → 292 | -50 (-14.62%) | 41 / 439 → 27 / 425 | 86 · +206 (+239.53%) | 11 / 872 | 86 · +206 (+239.53%) | 11 / 474 |
| 72 | `20080506-1.c` | 334 → 60 | -274 (-82.04%) | 40 / 438 → 4 / 388 | 184 · -124 (-67.39%) | 25 / 904 | 184 · -124 (-67.39%) | 25 / 506 |
| 72 | `941025-1.c` | 342 → 58 | -284 (-83.04%) | 82 / 480 → 51 / 449 | 86 · -28 (-32.56%) | 61 / 922 | 86 · -28 (-32.56%) | 59 / 522 |
| 72 | `941031-1.c` | 722 → 58 | -664 (-91.97%) | 175 / 2,356 → 107 / 2,288 | 86 · -28 (-32.56%) | 64 / 925 | 86 · -28 (-32.56%) | 64 / 527 |
| 72 | `990106-1.c` | 374 → 306 | -68 (-18.18%) | 50 / 448 → 45 / 443 | 86 · +220 (+255.81%) | 27 / 888 | 86 · +220 (+255.81%) | 27 / 490 |
| 72 | `enum-3.c` | 388 → 376 | -12 (-3.09%) | 44 / 442 → 43 / 441 | 286 · +90 (+31.47%) | 26 / 887 | 326 · +50 (+15.34%) | 26 / 489 |
| 72 | `pr15262.c` | 1,826 → 192 | -1,634 (-89.49%) | 256 / 2,437 → 162 / 2,329 | 410 · -218 (-53.17%) | 86 / 947 | 410 · -218 (-53.17%) | 86 / 549 |
| 72 | `pr29695-1.c` | 60 → 60 | +0 (+0.00%) | 168 / 2,335 → 107 / 2,274 | 68 · -8 (-11.76%) | 74 / 935 | 68 · -8 (-11.76%) | 42 / 505 |
| 72 | `pr37125.c` | 738 → 60 | -678 (-91.87%) | 67 / 4,517 → 42 / 4,492 | 68 · -8 (-11.76%) | 41 / 1,137 | 68 · -8 (-11.76%) | 41 / 805 |
| 72 | `pr49186.c` | 856 → 60 | -796 (-92.99%) | 86 / 2,267 → 4 / 388 | 138 · -78 (-56.52%) | 16 / 895 | 138 · -78 (-56.52%) | 16 / 497 |
| 73 | `no-const-pointers/seed-123` | 8,591,550 → 8,578,180 | -13,370 (-0.16%) | 18,971 / 27,937 → 18,951 / 27,917 | 3,234,500 · +5,343,680 (+165.21%) | 5,879 / 32,242 | BUILD case-compile | - |
| 74 | `conversion.c` | 49,926 → 44,198 | -5,728 (-11.47%) | 836 / 3,404 → 721 / 3,289 | 8,530 · +35,668 (+418.15%) | 842 / 3,885 | 8,530 · +35,668 (+418.15%) | 808 / 3,365 |
| 74 | `cvt-1.c` | 28,276 → 28,278 | +2 (+0.01%) | 259 / 2,827 → 249 / 2,817 | 4,340 · +23,938 (+551.57%) | 197 / 3,370 | FAIL abort | - |
| 75 | `conversion.c` | 44,198 → 218 | -43,980 (-99.51%) | 721 / 3,289 → 441 / 3,009 | 8,530 · -8,312 (-97.44%) | 842 / 3,885 | 8,530 · -8,312 (-97.44%) | 808 / 3,365 |
| 76 | `conversion.c` | 218 → 58 | -160 (-73.39%) | 441 / 3,009 → 435 / 3,003 | 8,530 · -8,472 (-99.32%) | 842 / 3,885 | 8,530 · -8,472 (-99.32%) | 808 / 3,365 |
| 77 | `cvt-1.c` | 28,278 → 58 | -28,220 (-99.79%) | 249 / 2,817 → 158 / 2,726 | 4,340 · -4,282 (-98.66%) | 197 / 3,370 | FAIL abort | - |
| 77 | `990923-1.c` | 124 → 58 | -66 (-53.23%) | 63 / 461 → 48 / 446 | 314 · -256 (-81.53%) | 78 / 957 | 314 · -256 (-81.53%) | 80 / 561 |
| 78 | `20001108-1.c` | 22,338 → 58 | -22,280 (-99.74%) | 599 / 3,111 → 480 / 2,992 | 1,170 · -1,112 (-95.04%) | 413 / 2,181 | BUILD 20001108-1-compile | - |
| 79 | `951204-1.c` | 16,498 → 7,276 | -9,222 (-55.90%) | 69 / 467 → 45 / 443 | 86 · +7,190 (+8360.47%) | 24 / 885 | 86 · +7,190 (+8360.47%) | 24 / 487 |
| 80 | `951204-1.c` | 7,276 → 58 | -7,218 (-99.20%) | 45 / 443 → 21 / 419 | 86 · -28 (-32.56%) | 24 / 885 | 86 · -28 (-32.56%) | 24 / 487 |


Fix 71 extends the short-trip proof to eight iterations when a single guard is provably false on every trip. Fix 72 selects the reachable arm of a literal conditional, including high-word-only integer conditions and binary32 negative zero. Fix 73 simplifies a logical expression when its literal left operand makes the right operand unreachable. The Csmith row uses the pinned `ptr2` profile.

Fix 74 evaluates word, long and binary32 scalar regions with literal arguments. Fix 75 uses the same evaluator across declaration blocks and reconsiders a call after lowering its arguments to literals. It substitutes the result when the evaluation reaches a literal without observable effects. Fix 76 removes discarded calls to same-unit void functions whose bodies are empty after optimization and preserves effects in argument evaluation.

Fix 77 evaluates local guards and selected returns during literal-call evaluation. It can select a call that reduces entirely to a literal even when ordinary expansion would exceed the inliner budget. The initial replay of `990923-1.c` folded only the call whose guard was false and exposed an extra frame store. Folding both selected returns brought it from the batch 7 baseline of 124 clocks to 58. Fix 78 uses the scalar region for literal calls with private 64-bit assignments. Fix 79 recovers direct local accesses through qualification-only near pointer casts while preserving volatile accesses. Fix 80 collapses loops that become empty after inlining and dead-store elimination.

The sub-100-clock results reflect whole-program elimination of the corresponding arithmetic, calls or checks. Separate-unit regressions exercise live guards, effectful arguments, high-word-only conditions, qualifier casts and a loop whose check fails on a later trip. The `build/slower-f71-after` through `build/slower-f80-after` records retain the before/after ROMs, assembly and repeated timings. Fix 72 uses `build/slower-f72-before` and `build/slower-f72-sweep-g`.

### Inventory replay after batch 8

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 7, 39 GCC and 368 Csmith cases improved. The other 261 GCC and 16 Csmith cases tied. Sixty-nine GCC cases and 366 Csmith cases have closed every recorded VBCC gap for their case. The remaining 249 cases are 231 GCC and 18 Csmith.

The replay records are in `build/slower-b8-final-g/results.jsonl` and `build/slower-b8-final-c/results.jsonl`. The 920 comparisons are in `build/slower-b8-final-pairs.csv`. All 687 ROM profiles for the remaining cases matched their recorded clocks and checksums in `build/slower-b8-final-profiles/results.jsonl`.


## Batch 9

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 81 | `20040409-2.c` | 14,764 → 60 | -14,704 (-99.59%) | 428 / 2,609 → 320 / 2,501 | 68 · -8 (-11.76%) | 423 / 1,302 | 68 · -8 (-11.76%) | 423 / 904 |
| 82 | `930622-2.c` | 17,562 → 9,854 | -7,708 (-43.89%) | 156 / 3,302 → 109 / 3,255 | 1,818 · +8,036 (+442.02%) | 163 / 4,545 | BUILD link | - |
| 83 | `930622-2.c` | 9,854 → 58 | -9,796 (-99.41%) | 109 / 3,255 → 64 / 3,210 | 1,818 · -1,760 (-96.81%) | 163 / 4,545 | BUILD link | - |
| 84 | `20010118-1.c` | 13,148 → 13,024 | -124 (-0.94%) | 308 / 2,876 → 304 / 2,872 | 1,202 · +11,822 (+983.53%) | 162 / 1,041 | 1,242 · +11,782 (+948.63%) | 163 / 644 |
| 85 | `20010118-1.c` | 13,024 → 460 | -12,564 (-96.47%) | 304 / 2,872 → 109 / 2,290 | 1,202 · -742 (-61.73%) | 162 / 1,041 | 1,242 · -782 (-62.96%) | 163 / 644 |
| 86 | `960311-3.c` | 11,162 → 7,126 | -4,036 (-36.16%) | 630 / 2,811 → 440 / 2,621 | 150 · +6,976 (+4650.67%) | 106 / 967 | 150 · +6,976 (+4650.67%) | 106 / 569 |
| 87 | `960311-3.c` | 7,126 → 4,256 | -2,870 (-40.28%) | 440 / 2,621 → 237 / 2,418 | 150 · +4,106 (+2737.33%) | 106 / 967 | 150 · +4,106 (+2737.33%) | 106 / 569 |
| 88 | `991016-1.c` | 24,394 → 18,492 | -5,902 (-24.19%) | 607 / 2,788 → 535 / 2,716 | 10,246 · +8,246 (+80.48%) | 838 / 1,717 | BUILD link | - |
| 89 | `991016-1.c` | 18,492 → 9,508 | -8,984 (-48.58%) | 535 / 2,716 → 410 / 2,591 | 10,246 · -738 (-7.20%) | 838 / 1,717 | BUILD link | - |
| 90 | `960311-3.c` | 4,256 → 3,508 | -748 (-17.58%) | 237 / 2,418 → 223 / 621 | 150 · +3,358 (+2238.67%) | 106 / 967 | 150 · +3,358 (+2238.67%) | 106 / 569 |


Fix 81 discards a void call when literal arguments let the scalar evaluator prove that every executed statement is effect-free. Fixes 82 and 83 fold exact integer/binary32 conversions in each direction, including signed minimum and both binary32 zeros. Nonintegral or out-of-range binary32-to-wide conversions and inexact wide-to-binary32 conversions keep their runtime paths. The binary64 runtime test checks the inexact conversion in all four rounding modes. The final 58-clock measurement for `930622-2.c` reflects whole-program elimination of the two conversion checks.

Fix 84 folds subtraction or XOR of two reads of the same nonvolatile integer object. Fix 85 discards a provably zero binary32 multiply/divide chain where the result is converted back to integer. This requires an exact word-to-binary32 operand conversion and preserves operations with observable effects. This removes the floating-point calculation within `20010118-1.c`. Fix 86 selects one memory word for 32-bit conditions masked to that word. Fix 87 folds a private integer compound shift when its incoming value and shift count are both known.

Fixes 88 and 89 emit an in-place carry chain for a discarded compound addition that doubles the same nonvolatile near-pointer target. Fix 88 handles words and 32-bit values. Fix 89 adds 64-bit values. Fix 90 shifts a fixed 32-bit home by one bit without staging it in the arithmetic scratch area. The separate-unit test checks the high and low mask words, signed and unsigned shifts, and carry propagation across each indirect word.

The `build/slower-f81-after` through `build/slower-f90-after` records preserve the matching assembly, ROMs, and repeated timings. Fixes 85 and 86 use `build/slower-f85-zero-after` and `build/slower-f86-real-after`. These rows measure the complete execution of each test's `main`. For `991016-1.c`, entry hooks confirmed three calls to `doit` in each zicc build. Modified VBCC inlined the three paths and unrolled their updates in `main`.

### Inventory replay after batch 9

All 300 GCC runs passed. Compared with batch 8, 19 improved and 281 tied. All 384 Csmith checksums and timings matched batch 8. Eighty-three GCC cases and 366 Csmith cases have closed every recorded VBCC gap for their case. The remaining 235 cases are 217 GCC and 18 Csmith.

The first replay exposed two rejected scalar-region probes that reached the literal folder with partially copied expressions. The evaluator now abandons those probes before folding. The replay also caught a slowdown in `cvt-1.c` from changing the existing binary32 conversion of narrower integer literals. The existing conversion now applies again, restoring the 58-clock result.

The final GCC and Csmith records are in `build/slower-b9-verified-g/results.jsonl` and `build/slower-b9-verified-c/results.jsonl`. The 920 comparisons are in `build/slower-b9-verified-pairs.csv`. All 648 ROM profiles for the remaining cases matched the recorded clocks and checksums in `build/slower-b9-verified-profiles/results.jsonl`.


## Batch 10

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 91 | `no-const-pointers/seed-123` | 8,588,426 → 8,395,800 | -192,626 (-2.24%) | 18,948 / 27,914 → 18,944 / 27,910 | 3,234,500 · +5,161,300 (+159.57%) | 5,879 / 32,242 | BUILD case-compile | - |
| 91 | `no-volatile-aggregate-fields/seed-123` | 2,674,158 → 2,491,766 | -182,392 (-6.82%) | 14,806 / 23,772 → 14,802 / 23,768 | 1,655,394 · +836,372 (+50.52%) | 3,349 / 29,495 | BUILD case-compile | - |
| 91 | `no-byte-types/seed-123` | 17,781,146 → 17,599,658 | -181,488 (-1.02%) | 11,795 / 20,761 → 11,791 / 20,757 | 48,789,298 · -31,189,640 (-63.93%) | 4,147 / 30,672 | BUILD case-compile | - |
| 92 | `no-const-pointers/seed-123` | 8,395,800 → 8,241,490 | -154,310 (-1.84%) | 18,944 / 27,910 → 18,941 / 27,907 | 3,234,500 · +5,006,990 (+154.80%) | 5,879 / 32,242 | BUILD case-compile | - |
| 92 | `no-volatile-aggregate-fields/seed-123` | 2,491,766 → 2,327,222 | -164,544 (-6.60%) | 14,802 / 23,768 → 14,799 / 23,765 | 1,655,394 · +671,828 (+40.58%) | 3,349 / 29,495 | BUILD case-compile | - |
| 92 | `no-byte-types/seed-123` | 17,599,658 → 17,434,170 | -165,488 (-0.94%) | 11,791 / 20,757 → 11,788 / 20,754 | 48,789,298 · -31,355,128 (-64.27%) | 4,147 / 30,672 | BUILD case-compile | - |
| 93 | `no-const-pointers/seed-123` | 8,241,490 → 8,202,016 | -39,474 (-0.48%) | 18,941 / 27,907 → 18,927 / 27,893 | 3,234,500 · +4,967,516 (+153.58%) | 5,879 / 32,242 | BUILD case-compile | - |
| 93 | `no-volatile-aggregate-fields/seed-123` | 2,327,222 → 2,308,358 | -18,864 (-0.81%) | 14,799 / 23,765 → 14,785 / 23,751 | 1,655,394 · +652,964 (+39.44%) | 3,349 / 29,495 | BUILD case-compile | - |
| 93 | `no-byte-types/seed-123` | 17,434,170 → 17,420,458 | -13,712 (-0.08%) | 11,788 / 20,754 → 11,774 / 20,740 | 48,789,298 · -31,368,840 (-64.29%) | 4,147 / 30,672 | BUILD case-compile | - |
| 94 | `no-const-pointers/seed-123` | 8,202,016 → 8,160,648 | -41,368 (-0.50%) | 18,927 / 27,893 → 18,905 / 27,871 | 3,234,500 · +4,926,148 (+152.30%) | 5,879 / 32,242 | BUILD case-compile | - |
| 94 | `no-volatile-aggregate-fields/seed-123` | 2,308,358 → 2,280,806 | -27,552 (-1.19%) | 14,785 / 23,751 → 14,763 / 23,729 | 1,655,394 · +625,412 (+37.78%) | 3,349 / 29,495 | BUILD case-compile | - |
| 94 | `no-byte-types/seed-123` | 17,420,458 → 17,400,402 | -20,056 (-0.12%) | 11,774 / 20,740 → 11,752 / 20,718 | 48,789,298 · -31,388,896 (-64.34%) | 4,147 / 30,672 | BUILD case-compile | - |
| 95 | `no-const-pointers/seed-123` | 8,160,648 → 8,158,496 | -2,152 (-0.03%) | 18,905 / 27,871 → 18,896 / 27,862 | 3,234,500 · +4,923,996 (+152.23%) | 5,879 / 32,242 | BUILD case-compile | - |
| 95 | `no-volatile-aggregate-fields/seed-123` | 2,280,806 → 2,279,318 | -1,488 (-0.07%) | 14,763 / 23,729 → 14,754 / 23,720 | 1,655,394 · +623,924 (+37.69%) | 3,349 / 29,495 | BUILD case-compile | - |
| 95 | `no-byte-types/seed-123` | 17,400,402 → 17,399,378 | -1,024 (-0.01%) | 11,752 / 20,718 → 11,743 / 20,709 | 48,789,298 · -31,389,920 (-64.34%) | 4,147 / 30,672 | BUILD case-compile | - |
| 96 | `no-const-pointers/seed-123` | 8,158,496 → 8,140,116 | -18,380 (-0.23%) | 18,896 / 27,862 → 18,888 / 27,854 | 3,234,500 · +4,905,616 (+151.67%) | 5,879 / 32,242 | BUILD case-compile | - |
| 96 | `no-volatile-aggregate-fields/seed-123` | 2,279,318 → 2,279,318 | +0 (+0.00%) | 14,754 / 23,720 → 14,746 / 23,712 | 1,655,394 · +623,924 (+37.69%) | 3,349 / 29,495 | BUILD case-compile | - |
| 96 | `no-byte-types/seed-123` | 17,399,378 → 17,398,618 | -760 (-0.00%) | 11,743 / 20,709 → 11,735 / 20,701 | 48,789,298 · -31,390,680 (-64.34%) | 4,147 / 30,672 | BUILD case-compile | - |
| 97 | `no-const-pointers/seed-123` | 8,140,116 → 7,910,646 | -229,470 (-2.82%) | 18,888 / 27,854 → 18,867 / 27,833 | 3,234,500 · +4,676,146 (+144.57%) | 5,879 / 32,242 | BUILD case-compile | - |
| 97 | `no-volatile-aggregate-fields/seed-123` | 2,279,318 → 2,279,318 | +0 (+0.00%) | 14,746 / 23,712 → 14,725 / 23,691 | 1,655,394 · +623,924 (+37.69%) | 3,349 / 29,495 | BUILD case-compile | - |
| 97 | `no-byte-types/seed-123` | 17,398,618 → 17,389,338 | -9,280 (-0.05%) | 11,735 / 20,701 → 11,714 / 20,680 | 48,789,298 · -31,399,960 (-64.36%) | 4,147 / 30,672 | BUILD case-compile | - |
| 98 | `no-const-pointers/seed-123` | 7,910,646 → 7,537,480 | -373,166 (-4.72%) | 18,867 / 27,833 → 18,862 / 27,828 | 3,234,500 · +4,302,980 (+133.03%) | 5,879 / 32,242 | BUILD case-compile | - |
| 98 | `no-volatile-aggregate-fields/seed-123` | 2,279,318 → 2,279,318 | +0 (+0.00%) | 14,725 / 23,691 → 14,720 / 23,686 | 1,655,394 · +623,924 (+37.69%) | 3,349 / 29,495 | BUILD case-compile | - |
| 98 | `no-byte-types/seed-123` | 17,389,338 → 17,387,258 | -2,080 (-0.01%) | 11,714 / 20,680 → 11,709 / 20,675 | 48,789,298 · -31,402,040 (-64.36%) | 4,147 / 30,672 | BUILD case-compile | - |
| 99 | `no-const-pointers/seed-123` | 7,537,480 → 7,537,480 | +0 (+0.00%) | 18,862 / 27,828 → 18,842 / 27,808 | 3,234,500 · +4,302,980 (+133.03%) | 5,879 / 32,242 | BUILD case-compile | - |
| 99 | `no-volatile-aggregate-fields/seed-123` | 2,279,318 → 2,279,318 | +0 (+0.00%) | 14,720 / 23,686 → 14,700 / 23,666 | 1,655,394 · +623,924 (+37.69%) | 3,349 / 29,495 | BUILD case-compile | - |
| 99 | `no-byte-types/seed-123` | 17,387,258 → 17,380,378 | -6,880 (-0.04%) | 11,709 / 20,675 → 11,689 / 20,655 | 48,789,298 · -31,408,920 (-64.38%) | 4,147 / 30,672 | BUILD case-compile | - |
| 100 | `no-const-pointers/seed-123` | 7,537,480 → 7,438,740 | -98,740 (-1.31%) | 18,842 / 27,808 → 18,809 / 27,775 | 3,234,500 · +4,204,240 (+129.98%) | 5,879 / 32,242 | BUILD case-compile | - |
| 100 | `no-volatile-aggregate-fields/seed-123` | 2,279,318 → 2,220,966 | -58,352 (-2.56%) | 14,700 / 23,666 → 14,667 / 23,633 | 1,655,394 · +565,572 (+34.17%) | 3,349 / 29,495 | BUILD case-compile | - |
| 100 | `no-byte-types/seed-123` | 17,380,378 → 17,337,922 | -42,456 (-0.24%) | 11,689 / 20,655 → 11,656 / 20,622 | 48,789,298 · -31,451,376 (-64.46%) | 4,147 / 30,672 | BUILD case-compile | - |


Fix 91 forms a one-bit right shift directly from the high and low words of a fixed home. Fix 92 keeps the shifted-out bit in carry across the stores and uses it to select each XOR word without a temporary save. Fix 93 removes a mask that covers all possible bits of an unsigned right shift. Fix 94 reads the surviving bytes of an eight-bit shift from a nonvolatile static 32-bit home and sign-extends the high byte for signed inputs. Fix 95 narrows an OR or XOR to a word when its result is masked to the low word.

Fix 96 compares an arbitrary signed long result against zero using its sign flag. Fix 97 computes just the high word of an integer bitwise expression for that test. Fix 98 can skip the second sign calculation of a side-effect-free AND or OR when the first sign decides the outcome. Fix 99 computes the low-word borrow for a projected subtraction without computing or storing the low result. Fix 100 combines a byte-aligned logical right shift with a near indexed operand as a direct word pair.

All three cases use the pinned `ptr2` sources. The generated C sources differ by toolchain in the VBCC rows, and their checksums match. The `build/slower-f91-after` through `build/slower-f100-after` runs retain the generated assembly, ROMs and repeated measurements. The known-values test covers selected cases with nonliteral inputs, including both signs, an indexed read and a borrow that crosses the low-word boundary.

### Inventory replay after batch 10

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 9, two GCC cases and all 384 Csmith cases improved. The other 298 GCC cases tied. Eighty-three GCC cases and 380 Csmith cases have closed every recorded VBCC gap for their case. The remaining 221 cases are 217 GCC and four Csmith. The four Csmith cases are the two pointer modes each of `no-const-pointers/seed-123` and `no-volatile-aggregate-fields/seed-123`.

The replay records are in `build/slower-b10-final-g/results.jsonl` and `build/slower-b10-final-c/results.jsonl`. The 920 comparisons are in `build/slower-b10-final-pairs.csv`. All 620 ROM profiles for the remaining cases matched the recorded clocks and checksums in `build/slower-b10-final-profiles/results.jsonl`.


## Batch 11

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 101 | `pr19005.c` | 573,294 → 497,686 | -75,608 (-13.19%) | 196 / 2,377 → 289 / 2,470 | 477,474 · +20,212 (+4.23%) | 492 / 1,371 | 518,418 · -20,732 (-4.00%) | 502 / 983 |
| 102 | `pr19005.c` | 497,686 → 472,086 | -25,600 (-5.14%) | 289 / 2,470 → 281 / 2,462 | 477,474 · -5,388 (-1.13%) | 492 / 1,371 | 518,418 · -46,332 (-8.94%) | 502 / 983 |
| 103 | `950612-1.c` | 78,650 → 66,052 | -12,598 (-16.02%) | 627 / 2,808 → 881 / 3,062 | 65,144 · +908 (+1.39%) | 919 / 1,798 | BUILD 950612-1-compile | - |
| 104 | `950612-1.c` | 66,052 → 62,832 | -3,220 (-4.87%) | 881 / 3,062 → 785 / 2,966 | 65,144 · -2,312 (-3.55%) | 919 / 1,798 | BUILD 950612-1-compile | - |
| 105 | `950612-1.c` | 62,832 → 53,732 | -9,100 (-14.48%) | 785 / 2,966 → 686 / 2,867 | 65,144 · -11,412 (-17.52%) | 919 / 1,798 | BUILD 950612-1-compile | - |
| 106 | `950612-1.c` | 53,732 → 47,902 | -5,830 (-10.85%) | 686 / 2,867 → 513 / 2,694 | 65,144 · -17,242 (-26.47%) | 919 / 1,798 | BUILD 950612-1-compile | - |
| 107 | `950612-1.c` | 47,902 → 37,022 | -10,880 (-22.71%) | 513 / 2,694 → 426 / 2,607 | 65,144 · -28,122 (-43.17%) | 919 / 1,798 | BUILD 950612-1-compile | - |
| 108 | `921029-1.c` | 30,242 → 27,330 | -2,912 (-9.63%) | 783 / 2,964 → 761 / 2,942 | 13,830 · +13,500 (+97.61%) | 1,303 / 2,182 | BUILD link | - |
| 109 | `921029-1.c` | 27,330 → 26,078 | -1,252 (-4.58%) | 761 / 2,942 → 751 / 2,932 | 13,830 · +12,248 (+88.56%) | 1,303 / 2,182 | BUILD link | - |
| 110 | `921029-1.c` | 26,078 → 21,494 | -4,584 (-17.58%) | 751 / 2,932 → 722 / 2,903 | 13,830 · +7,664 (+55.42%) | 1,303 / 2,182 | BUILD link | - |


Fix 101 allows the loop inliner to consider small void callees with calls confined to guarded arms. Its ordinary expansion and frame budgets still apply. Fix 102 compares a computed unsigned byte directly against an addressable byte. This avoids saving a full word before evaluating the comparison operand in `pr19005.c`.

Fix 103 substitutes small same-unit wide functions with one cheap integer argument and a pure return expression. Fix 104 forms the wide negation of a word from the low result and a shared upper fill. Fix 105 tests the sign of a widened word before extension. Fix 106 emits a word-sized magnitude when the wide conditional chooses between a widened word and its negation. Fix 107 compares that magnitude directly with another word. Its signed comparison operand still needs to be nonnegative. The regressions include the most-negative signed word and a negative comparison value with identical low bits.

Fixes 108 and 109 combine an adjacent widened store and a shift or mask on the same nonvolatile 64-bit home. Only the remaining half is written from the source. Fix 110 returns the value of an immediately preceding wide store without reading it back. The separate-unit test reads the high, low and combined stores after the function returns.

The `build/slower-f101-loop-after` and `build/slower-f102-after` through `build/slower-f110-after` records retain generated assembly, ROMs and repeated timings. Each row is the complete execution of `main`.

### Inventory replay after batch 11

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 10, five GCC cases improved, 295 tied, and all Csmith cases tied. Eighty-five GCC cases and 380 Csmith cases have closed every recorded VBCC gap for their case. The remaining 219 cases are 215 GCC and four Csmith.

The final magnitude comparison checks the signed value of narrow literals before selecting a word comparison. A focused regression checks that magnitude 32,768 compares unequal to the signed literal −32,768. The byte comparison now retains direct word comparisons when both values can use them, which restored the earlier timing in `pr37924.c` and four Csmith cases.

The replay records are in `build/slower-b11-verified-g/results.jsonl` and `build/slower-b11-verified-c/results.jsonl`. The 920 comparisons are in `build/slower-b11-verified-pairs.csv`. All 615 ROM profiles for the remaining cases matched the recorded clocks and checksums in `build/slower-b11-verified-profiles/results.jsonl`.


## Batch 12

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 111 | `960215-1.c` | 100,468 → 1,284 | -99,184 (-98.72%) | 585 / 2,766 → 130 / 528 | 77,542 · -76,258 (-98.34%) | 646 / 3,601 | 76,348 · -75,064 (-98.32%) | 610 / 3,167 |
| 112 | `pr78856.c` | 14,488 → 14,396 | -92 (-0.64%) | 156 / 2,337 → 149 / 2,330 | 904 · +13,492 (+1492.48%) | 88 / 949 | 944 · +13,452 (+1425.00%) | 88 / 551 |
| 113 | `991216-1.c` | 10,740 → 58 | -10,682 (-99.46%) | 1,015 / 1,413 → 712 / 1,110 | 86 · -28 (-32.56%) | 575 / 1,454 | BUILD 991216-1-compile | - |
| 114 | `pr37924.c` | 1,690 → 664 | -1,026 (-60.71%) | 255 / 653 → 116 / 500 | 1,544 · -880 (-56.99%) | 227 / 1,106 | 1,576 · -912 (-57.87%) | 231 / 712 |
| 115 | `20020510-1.c` | 4,684 → 442 | -4,242 (-90.56%) | 271 / 669 → 167 / 565 | 68 · +374 (+550.00%) | 142 / 1,021 | 68 · +374 (+550.00%) | 146 / 627 |
| 116 | `compare-1.c` | 7,192 → 60 | -7,132 (-99.17%) | 494 / 2,675 → 359 / 2,540 | 68 · -8 (-11.76%) | 357 / 1,236 | 68 · -8 (-11.76%) | 357 / 838 |
| 117 | `pr29798.c` | 11,676 → 60 | -11,616 (-99.49%) | 95 / 2,276 → 4 / 388 | 68 · -8 (-11.76%) | 4 / 865 | 68 · -8 (-11.76%) | 4 / 467 |
| 118 | `20011217-1.c` | 5,024 → 58 | -4,966 (-98.85%) | 95 / 2,276 → 10 / 408 | 86 · -28 (-32.56%) | 11 / 872 | 86 · -28 (-32.56%) | 11 / 474 |
| 119 | `20020510-1.c` | 442 → 60 | -382 (-86.43%) | 167 / 565 → 157 / 555 | 68 · -8 (-11.76%) | 142 / 1,021 | 68 · -8 (-11.76%) | 146 / 627 |
| 120 | `20020508-3.c` | 77,934 → 75,476 | -2,458 (-3.15%) | 3,021 / 7,787 → 2,817 / 7,583 | 71,888 · +3,588 (+4.99%) | 3,007 / 3,886 | BUILD link | - |
| 120 | `pr40386.c` | 77,934 → 75,476 | -2,458 (-3.15%) | 3,021 / 7,787 → 2,817 / 7,583 | 71,888 · +3,588 (+4.99%) | 3,007 / 3,886 | BUILD link | - |


Fix 111 propagates scalar initializers through the straight-line prefix of the startup-only `main` entry. It keeps the original stores and stops at operations that may invalidate the facts. Fix 112 removes a leading integer while loop when its first test is provably false. Fix 114 follows a known branch and continues until it reaches an operation that may change the known values. Fix 120 applies the same pass to wide functions and tracks both limbs of a 64-bit initializer.

Fix 113 uses the literal evaluator for discarded void calls with wide arguments. Fix 115 follows nested guards on the selected constant path. Fix 116 also evaluates a call when the caller discards a nonvoid result, including a call that reaches the end of its function body. Reachable effects keep the original call or the normal inlined path.

Fix 117 folds a binary32 compound assignment when both operands are known and its result is exact. The comparison suite caught an inexact addition in the first trial. The exactness check keeps that addition at runtime and leaves the measured division case byte-identical. Fix 118 substitutes the old literal for a private post-update in the entry prefix when the updated value is unread. Fix 119 evaluates a literal sum, difference or product modulo the width of its unsigned destination.

The sub-100-clock rows reflect whole-program elimination of the checks. The `build/slower-f111-after` through `build/slower-f120-after` records retain matching assembly, ROMs and repeated timings. The regressions check both the pure and observable paths, including a wide initializer, a call that changes an initialized object, and a live post-update.

### Inventory replay after batch 12

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 11, 41 GCC cases improved, 259 tied, and all Csmith cases tied. A total of 489 cases closed every recorded VBCC gap, with 191 GCC and four Csmith cases still slower in at least one comparison.

The final replay records and 920 comparisons are in `build/slower-b12-final-g/results.jsonl`, `build/slower-b12-final-c/results.jsonl`, and `build/slower-b12-final-pairs.csv`. All 545 profiles for the remaining cases matched the recorded clocks and checksums in `build/slower-b12-final-profiles/results.jsonl`.


## Batch 13

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 121 | `20100805-1.c` | 5,648 → 60 | -5,588 (-98.94%) | 66 / 2,247 → 49 / 2,216 | 68 · -8 (-11.76%) | 46 / 907 | 68 · -8 (-11.76%) | 47 / 510 |
| 122 | `991216-4.c` | 1,544 → 58 | -1,486 (-96.24%) | 74 / 2,255 → 10 / 408 | 86 · -28 (-32.56%) | 11 / 872 | 86 · -28 (-32.56%) | 11 / 474 |
| 123 | `961122-1.c` | 5,572 → 2,484 | -3,088 (-55.42%) | 442 / 2,623 → 242 / 2,423 | 294 · +2,190 (+744.90%) | 193 / 1,054 | BUILD link | - |
| 124 | `961122-1.c` | 2,484 → 2,200 | -284 (-11.43%) | 242 / 2,423 → 210 / 2,391 | 294 · +1,906 (+648.30%) | 193 / 1,054 | BUILD link | - |
| 125 | `pr35800.c` | 45,256 → 33,088 | -12,168 (-26.89%) | 406 / 2,587 → 436 / 2,617 | 28,858 · +4,230 (+14.66%) | 664 / 1,543 | 32,134 · +954 (+2.97%) | 703 / 1,184 |
| 126 | `pr35800.c` | 33,088 → 30,746 | -2,342 (-7.08%) | 436 / 2,617 → 422 / 2,603 | 28,858 · +1,888 (+6.54%) | 664 / 1,543 | 32,134 · -1,388 (-4.32%) | 703 / 1,184 |
| 127 | `950704-1.c` | 15,102 → 8,272 | -6,830 (-45.23%) | 514 / 2,695 → 441 / 2,622 | 126 · +8,146 (+6465.08%) | 270 / 1,131 | BUILD 950704-1-compile | - |
| 128 | `921029-1.c` | 21,494 → 18,642 | -2,852 (-13.27%) | 722 / 2,903 → 1,736 / 3,917 | 13,830 · +4,812 (+34.79%) | 1,303 / 2,182 | BUILD link | - |
| 129 | `921029-1.c` | 18,642 → 14,300 | -4,342 (-23.29%) | 1,736 / 3,917 → 1,295 / 3,476 | 13,830 · +470 (+3.40%) | 1,303 / 2,182 | BUILD link | - |
| 130 | `921029-1.c` | 14,300 → 5,996 | -8,304 (-58.07%) | 1,295 / 3,476 → 719 / 2,900 | 13,830 · -7,834 (-56.64%) | 1,303 / 2,182 | BUILD link | - |


Fix 121 evaluates bounded for loops in same-unit calls when every condition and private update stays literal. Fix 122 applies the proof to nested loops and while loops, sharing a single execution budget. The two sub-100-clock results remove the loops from the caller. The regressions run an effectful loop and a larger literal loop through the runtime path.

Fix 123 updates only the affected limbs when adding or subtracting a word-aligned shift in a discarded compound assignment to fixed storage. Fix 124 stages only the retained words of a narrower operand. The test checks signed widening, carry and borrow across the updated limbs, and an untouched low word.

Fix 125 uses a range check and direct balanced dispatch for 17 to 64 contiguous word cases. Fix 126 negates the case keys for a negated word switch and dispatches on its input. Across the zicc trials, execution hooks counted 36 calls to the switch function. Both VBCCs inline the dispatch, fold constant inputs and run 15 iterations of the two-way unrolled loop. The timings compare complete programs. The zicc source uses the inventory's explicit far pointer for the string address, while VBCC uses its default pointer representation.

Fix 127 keeps literal stores when evaluating a wide same-unit call. Fix 128 tracks the stored values through later operations and combines consecutive writes to the same nonvolatile object. Fix 129 folds a comparison of the known result while preserving the stores. Fix 130 emits a discarded fixed-home integer literal store directly, including stores inside comma expressions. The test reads all three globals from a separate translation unit after the specialized call.

The trial directories under `build/slower-f121-after` through `build/slower-f130-direct-after` retain the assembly, ROMs, repeated measurements and execution hooks. The reference zicc replay is `build/slower-b12-final-g`.

### Inventory replay after batch 13

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 12, 13 GCC and 146 Csmith cases improved, and the other 525 tied. A total of 493 cases closed every recorded VBCC gap. The remaining 191 cases are 187 GCC and four Csmith.

The working-tree replay and all 920 comparisons are in `build/slower-b13-final-g/results.jsonl`, `build/slower-b13-final-c/results.jsonl`, and `build/slower-b13-final-pairs.csv`. All 534 profiles for the remaining cases matched the recorded clocks and checksums in `build/slower-b13-final-profiles/results.jsonl`.


## Batch 14

The ptr2 and ptr4 variants produced the same clocks, application and linked code sizes, and checksums for each row. Stock VBCC failed to compile both generated programs.

| Fix | Csmith case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 131 | `no-const-pointers/seed-123` | 7,324,276 → 7,295,330 | -28,946 (-0.40%) | 18,761 / 27,727 → 18,492 / 27,458 | 3,234,500 · +4,060,830 (+125.55%) | 5,879 / 32,242 | BUILD case-compile | - |
| 132 | `no-const-pointers/seed-123` | 7,295,330 → 5,964,486 | -1,330,844 (-18.24%) | 18,492 / 27,458 → 18,186 / 27,152 | 3,234,500 · +2,729,986 (+84.40%) | 5,879 / 32,242 | BUILD case-compile | - |
| 133 | `no-const-pointers/seed-123` | 5,964,486 → 5,450,532 | -513,954 (-8.62%) | 18,186 / 27,152 → 18,156 / 27,122 | 3,234,500 · +2,216,032 (+68.51%) | 5,879 / 32,242 | BUILD case-compile | - |
| 134 | `no-const-pointers/seed-123` | 5,450,532 → 4,925,256 | -525,276 (-9.64%) | 18,156 / 27,122 → 18,122 / 27,088 | 3,234,500 · +1,690,756 (+52.27%) | 5,879 / 32,242 | BUILD case-compile | - |
| 135 | `no-const-pointers/seed-123` | 4,925,256 → 4,715,288 | -209,968 (-4.26%) | 18,122 / 27,088 → 18,082 / 27,048 | 3,234,500 · +1,480,788 (+45.78%) | 5,879 / 32,242 | BUILD case-compile | - |
| 136 | `no-const-pointers/seed-123` | 4,715,288 → 4,500,468 | -214,820 (-4.56%) | 18,082 / 27,048 → 17,853 / 26,819 | 3,234,500 · +1,265,968 (+39.14%) | 5,879 / 32,242 | BUILD case-compile | - |
| 137 | `no-const-pointers/seed-123` | 4,500,468 → 4,363,316 | -137,152 (-3.05%) | 17,853 / 26,819 → 17,292 / 26,258 | 3,234,500 · +1,128,816 (+34.90%) | 5,879 / 32,242 | BUILD case-compile | - |
| 137 | `no-volatile-aggregate-fields/seed-123` | 1,943,550 → 1,626,514 | -317,036 (-16.31%) | 14,184 / 23,150 → 14,085 / 23,051 | 1,655,394 · -28,880 (-1.74%) | 3,349 / 29,495 | BUILD case-compile | - |
| 138 | `no-volatile-aggregate-fields/seed-123` | 1,626,514 → 1,375,034 | -251,480 (-15.46%) | 14,085 / 23,051 → 14,026 / 22,992 | 1,655,394 · -280,360 (-16.94%) | 3,349 / 29,495 | BUILD case-compile | - |
| 139 | `no-volatile-aggregate-fields/seed-123` | 1,375,034 → 995,434 | -379,600 (-27.61%) | 14,026 / 22,992 → 14,009 / 22,975 | 1,655,394 · -659,960 (-39.87%) | 3,349 / 29,495 | BUILD case-compile | - |
| 140 | `no-const-pointers/seed-123` | 4,363,316 → 4,296,008 | -67,308 (-1.54%) | 17,292 / 26,258 → 16,758 / 25,724 | 3,234,500 · +1,061,508 (+32.82%) | 5,879 / 32,242 | BUILD case-compile | - |


In `no-const-pointers/seed-123`, per-instruction hooks mapped 139,491 of 167,955 instructions in `func_1` to the assignment in the inner loop. The bitwise expression supplies an all-ones operand to subtraction, then discards the comparison result. The assignment still has observable stores. The hooks and source-line mapping for the initial hotspot are in `build/slower-b14-csmith-hotspots3`.

Fix 131 folds absorbing bitwise constants in wide expressions, keeping side-effecting operands in a comma expression. Fix 132 emits just the effectful operand of a discarded bitwise result. Fix 133 specializes a wide call using the literal tail of one comma argument and evaluates that argument's effects before the specialized result. Fix 134 sequences a left operand's effects before comparing its literal tail with an effect-free input. Fix 135 compares at the narrow input width when the immediate matches the input's extension. Fixes 136 and 140 remove unused integer comparisons and retain both effectful operands when needed.

Fix 137 removes a for loop whose preceding literal initializer makes the first test false and retains the initializer. Fix 138 uses a low-word test and increment for bounded wide global induction when the body only writes other directly named integers. Fix 139 collapses repeated literal stores in that loop shape and writes the final counter value. The separate-unit regression checks carry out of the low word in the body result, the final counter, and volatile stores on both sides of a discarded expression.

The clocks compare complete programs. The trials retain the executed assembly, ROMs, matched checksums and repeated timings under `build/slower-f131-wide` through `build/slower-f140-trial`.

### Inventory replay after batch 14

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 13, four GCC and 228 Csmith cases improved, 444 cases tied, and eight Csmith cases rose by 4,212 to 9,842 clocks (0.38% to 0.91%). In those eight runs the profiled instruction count outside the console fell by 23 to 276. The console executed 426 more instructions. An instruction-address trace in a representative run shows that the changed timing let a pending console presentation run before `main` returned. The replay retains the full timings and the trace in `build/slower-b14-timing-regressions`.

A total of 495 cases closed every recorded VBCC gap. The remaining 189 cases are 187 GCC and the two pointer-width variants of `no-const-pointers/seed-123`. Both measured Csmith cases are byte-identical to their final trial ROMs. All 530 profiles for the remaining cases matched the recorded clocks and checksums. Evidence is in `build/slower-b14-final-g/results.jsonl`, `build/slower-b14-final-c/results.jsonl`, `build/slower-b14-final-pairs.csv`, and `build/slower-b14-final-profiles/results.jsonl`.


## Batch 15

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 141 | `no-const-pointers/seed-123` | 4,296,008 → 2,875,848 | -1,420,160 (-33.06%) | 16,758 / 25,724 → 16,397 / 25,363 | 3,234,500 · -358,652 (-11.09%) | 5,879 / 32,242 | BUILD case-compile | - |
| 142 | `20021120-1.c` | 674,180 → 672,564 | -1,616 (-0.24%) | 4,823 / 7,391 → 4,695 / 7,263 | 637,396 · +35,168 (+5.52%) | 4,831 / 7,786 | 626,578 · +45,986 (+7.34%) | 4,618 / 7,175 |
| 143 | `950607-2.c` | 22,602 → 21,000 | -1,602 (-7.09%) | 511 / 3,023 → 375 / 5,309 | 15,816 · +5,184 (+32.78%) | 863 / 2,631 | BUILD link | - |
| 143 | `950915-1.c` | 9,658 → 8,318 | -1,340 (-13.87%) | 119 / 2,631 → 51 / 4,985 | 8,116 · +202 (+2.49%) | 318 / 2,086 | BUILD 950915-1-compile | - |
| 144 | `950607-2.c` | 21,000 → 13,976 | -7,024 (-33.45%) | 375 / 5,309 → 375 / 5,331 | 15,816 · -1,840 (-11.63%) | 863 / 2,631 | BUILD link | - |
| 144 | `950915-1.c` | 8,318 → 4,940 | -3,378 (-40.61%) | 51 / 4,985 → 51 / 5,007 | 8,116 · -3,176 (-39.13%) | 318 / 2,086 | BUILD 950915-1-compile | - |
| 145 | `961213-1.c` | 30,120 → 24,790 | -5,330 (-17.70%) | 430 / 2,942 → 359 / 2,913 | 13,302 · +11,488 (+86.36%) | 707 / 2,475 | BUILD link | - |
| 146 | `961213-1.c` | 24,790 → 19,568 | -5,222 (-21.06%) | 359 / 2,913 → 298 / 2,852 | 13,302 · +6,266 (+47.11%) | 707 / 2,475 | BUILD link | - |
| 147 | `961213-1.c` | 19,568 → 19,282 | -286 (-1.46%) | 298 / 2,852 → 280 / 2,834 | 13,302 · +5,980 (+44.96%) | 707 / 2,475 | BUILD link | - |
| 148 | `961213-1.c` | 19,282 → 14,872 | -4,410 (-22.87%) | 280 / 2,834 → 280 / 2,876 | 13,302 · +1,570 (+11.80%) | 707 / 2,475 | BUILD link | - |
| 149 | `961213-1.c` | 14,872 → 14,562 | -310 (-2.08%) | 280 / 2,876 → 278 / 2,874 | 13,302 · +1,260 (+9.47%) | 707 / 2,475 | BUILD link | - |
| 150 | `961213-1.c` | 14,562 → 14,082 | -480 (-3.30%) | 278 / 2,874 → 274 / 2,870 | 13,302 · +780 (+5.86%) | 707 / 2,475 | BUILD link | - |


Fix 141 discards integer-to-integer conversions when their results are unused and emits the operand's effects. Both Csmith pointer-width variants matched the row and checksum `02ccc6a9`. Fix 142 copies fixed binary32 values word by word between an unescaped automatic home and static storage. The volatile case performs the original loads and stores.

Fix 143 uses signed 32-by-32 partial products for two narrowed operands with a wide result. Fix 144 skips partial products when a high word is zero. The signed-long routine uses the existing word multiply helper. Moving the new entry into its own library object keeps that helper out of ROMs that only use ordinary 64-bit multiplication. The split builds measured 13,940 clocks and 375 / 5,014 code bytes for `950607-2.c`, and 4,922 clocks and 51 / 4,690 bytes for `950915-1.c`.

Fix 145 passes a loaded signed or unsigned word factor directly to wide multiplication. Fix 146 adds an unsigned word to a wide result with carry propagation, avoiding the general second operand slot. Fix 147 writes literal limbs directly to a near indirect destination. Fix 148 handles zero and one-bit word factors with zeroing or shifts. Fix 149 loads the stable destination pointer after an effect-free right-hand side. Fix 150 tests the sign of a private invariant bound once for a zero-based signed word loop and compares it unsigned on the back edge. The separate-unit regression exercises the signed and unsigned word paths, carry, and signed bounds including zero and the most-negative word.

These are complete-program measurements. In `961213-1.c`, the zicc loop retains its dynamic factor and runtime multiplication, while modified VBCC can specialize code at the literal call site. The trial directories from `build/slower-f141-trial` through `build/slower-f150-after` retain generated assembly, ROMs and repeated timing evidence.

### Inventory replay after batch 15

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with batch 14, six GCC and 76 Csmith cases improved, and the other 602 tied. Both remaining Csmith cases and two GCC cases closed their recorded VBCC gaps. All 384 Csmith cases now close their gaps. The 185 remaining cases are GCC.

The interrupt scratch audit rejected the assembler repeat expression in the first full check. Spelling out the same four word stores passed the audit and kept the measured GCC ROMs byte-identical. The final replay records and all 920 comparisons are in `build/slower-b15-final-g/results.jsonl`, `build/slower-b15-final-c/results.jsonl`, and `build/slower-b15-final-pairs.csv`. All 522 profiles for the remaining cases matched the recorded clocks and checksums in `build/slower-b15-final-profiles/results.jsonl`.


## Batch 16

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 151 | `20011109-2.c` | 3,846 → 112 | -3,734 (-97.09%) | 152 / 2,333 → 24 / 422 | 86 · +26 (+30.23%) | 11 / 872 | 86 · +26 (+30.23%) | 11 / 474 |
| 152 | `20011109-2.c` | 112 → 58 | -54 (-48.21%) | 24 / 422 → 10 / 408 | 86 · -28 (-32.56%) | 11 / 872 | 86 · -28 (-32.56%) | 11 / 474 |
| 153 | `921218-1.c` | 344 → 58 | -286 (-83.14%) | 61 / 2,242 → 14 / 412 | 156 · -98 (-62.82%) | 27 / 906 | 156 · -98 (-62.82%) | 27 / 508 |
| 154 | `930111-1.c` | 1,120 → 58 | -1,062 (-94.82%) | 227 / 2,408 → 193 / 2,374 | 156 · -98 (-62.82%) | 126 / 1,005 | BUILD link | - |
| 154 | `20011109-1.c` | 782 → 58 | -724 (-92.58%) | 222 / 620 → 211 / 609 | 86 · -28 (-32.56%) | 239 / 1,118 | 86 · -28 (-32.56%) | 240 / 721 |
| 154 | `920909-1.c` | 360 → 58 | -302 (-83.89%) | 94 / 492 → 80 / 478 | 132 · -74 (-56.06%) | 84 / 963 | 132 · -74 (-56.06%) | 84 / 565 |
| 154 | `20010106-1.c` | 306 → 58 | -248 (-81.05%) | 106 / 504 → 92 / 490 | 132 · -74 (-56.06%) | 89 / 968 | 132 · -74 (-56.06%) | 89 / 570 |
| 154 | `pr35800.c` | 30,746 → 30,310 | -436 (-1.42%) | 422 / 2,603 → 394 / 2,575 | 28,858 · +1,452 (+5.03%) | 664 / 1,543 | 32,134 · -1,824 (-5.68%) | 703 / 1,184 |
| 155 | `pr35800.c` | 30,310 → 19,750 | -10,560 (-34.84%) | 394 / 2,575 → 136 / 2,317 | 28,858 · -9,108 (-31.56%) | 664 / 1,543 | 32,134 · -12,384 (-38.54%) | 703 / 1,184 |
| 156 | `20010329-1.c` | 2,392 → 58 | -2,334 (-97.58%) | 128 / 4,578 → 10 / 408 | 86 · -28 (-32.56%) | 11 / 872 | 86 · -28 (-32.56%) | 11 / 474 |
| 157 | `20030307-1.c` | 1,980 → 60 | -1,920 (-96.97%) | 133 / 531 → 28 / 412 | 138 · -78 (-56.52%) | 22 / 901 | BUILD 20030307-1-compile | - |
| 158 | `20001031-1.c` | 2,686 → 2,304 | -382 (-14.22%) | 243 / 2,424 → 222 / 2,403 | 722 · +1,582 (+219.11%) | 128 / 1,007 | BUILD link | - |
| 159 | `20001031-1.c` | 2,304 → 394 | -1,910 (-82.90%) | 222 / 2,403 → 144 / 2,325 | 722 · -328 (-45.43%) | 128 / 1,007 | BUILD link | - |
| 160 | `20001031-1.c` | 394 → 58 | -336 (-85.28%) | 144 / 2,325 → 113 / 2,294 | 722 · -664 (-91.97%) | 128 / 1,007 | BUILD link | - |

Fix 151 propagates unescaped far-pointer string literals and folds equality of
same-signedness bytes from identical strings at an unchanged, effect-free
index. Fix 152 removes the now-unused far-pointer homes. Fix 153 folds an
in-range literal string read, including embedded zero bytes and high-bit
characters. Fix 156 propagates literal pointer values and compares equal-width
addresses unsigned. The near and far representations retain their respective
widths.

Fix 154 evaluates a selected switch arm when a constant call argument proves
the case and the selected arm terminates directly. Fix 155 projects a returned
string byte into each case that assigns the private pointer, propagating the
last assignment across fallthrough. Dense word switches can use a result
table with up to 64 entries and preserve the ordinary continuation for an
unmatched key. Execution hooks counted 36 direct calls to
`stab_xcoff_builtin_type` before fix 154, and 34 after each of fixes 154 and
155. Fix 154 folded the two literal calls outside the switch range. Fix 155
kept all 34 remaining calls and lowered the selected return value.

Fix 157 substitutes the sole used argument into a pure conversion when all
unused arguments are effect-free. Fix 158 separates a literal assignment
from the arithmetic value passed to a callee. Fix 159 carries that effect
through an integer cast and drops pure tails when evaluating discarded
statements. Fix 160 applies the same call folding to the narrow-argument
case. The separate-unit regression verifies the retained values and an
observable unused argument. The isolated compiler also validates a
void-valued comma expression that retains a wide store.

zicc uses the pinned equivalent source with explicit `__far` qualifiers
for `20011109-2.c`, `20010329-1.c`, and `pr35800.c`. Both VBCC builds use the
upstream spelling. Every zicc before/after pair uses identical sources.
These are complete-program clocks, including the effects of compile-time
folding and the target ABI. The trial ROMs, assembly and repeated timings are
under `build/slower-f151-combined` through `build/slower-f160-after`, with the
reconstructed switch baselines in `build/slower-b16-pre154` and
`build/slower-b16-pre155`.

### Inventory replay after batch 16

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with
batch 15, 138 cases improved, 541 tied and five slowed. In `950426-1.c` the
frame shrank and two stack stores survived, with a net cost of 24 clocks
(0.93%). Four Csmith runs rose by 56 clocks each (0.0061% to 0.0069%) and
remain faster than their VBCC references. The assembly differences are in
`build/slower-b16-timing-deltas`.

A total of 514 cases closed all recorded VBCC gaps. The remaining 170 cases
are GCC. All 481 profiles for the open cases matched their recorded clocks
and checksums. The 920 comparisons are in `build/slower-b16-final-pairs.csv`,
with replay and profile records in `build/slower-b16-final-g`,
`build/slower-b16-final-c`, and `build/slower-b16-final-profiles`.


## Batch 17

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 161 | `pr78856.c` | 14,396 → 10,162 | -4,234 (-29.41%) | 149 / 2,330 → 121 / 2,302 | 904 · +9,258 (+1024.12%) | 88 / 949 | 944 · +9,218 (+976.48%) | 88 / 551 |
| 162 | `pr78856.c` | 10,162 → 7,570 | -2,592 (-25.51%) | 121 / 2,302 → 109 / 2,290 | 904 · +6,666 (+737.39%) | 88 / 949 | 944 · +6,626 (+701.91%) | 88 / 551 |
| 163 | `pr78856.c` | 7,570 → 2,078 | -5,492 (-72.55%) | 109 / 2,290 → 72 / 2,253 | 904 · +1,174 (+129.87%) | 88 / 949 | 944 · +1,134 (+120.13%) | 88 / 551 |
| 164 | `pr78856.c` | 2,078 → 1,460 | -618 (-29.74%) | 72 / 2,253 → 60 / 2,241 | 904 · +556 (+61.50%) | 88 / 949 | 944 · +516 (+54.66%) | 88 / 551 |
| 165 | `pr78856.c` | 1,460 → 564 | -896 (-61.37%) | 60 / 2,241 → 56 / 454 | 904 · -340 (-37.61%) | 88 / 949 | 944 · -380 (-40.25%) | 88 / 551 |
| 166 | `pr78856.c` | 564 → 258 | -306 (-54.26%) | 56 / 454 → 29 / 427 | 904 · -646 (-71.46%) | 88 / 949 | 944 · -686 (-72.67%) | 88 / 551 |
| 167 | `20000112-1.c` | 13,772 → 58 | -13,714 (-99.58%) | 185 / 3,965 → 10 / 408 | 6,732 · -6,674 (-99.14%) | 237 / 1,179 | 6,772 · -6,714 (-99.14%) | 237 / 781 |
| 168 | `960311-3.c` | 3,420 → 3,140 | -280 (-8.19%) | 204 / 602 → 160 / 558 | 150 · +2,990 (+1993.33%) | 106 / 967 | 150 · +2,990 (+1993.33%) | 106 / 569 |
| 169 | `20030404-1.c` | 3,330 → 60 | -3,270 (-98.20%) | 65 / 2,246 → 4 / 388 | 68 · -8 (-11.76%) | 4 / 865 | 68 · -8 (-11.76%) | 4 / 467 |
| 170 | `960311-1.c` | 4,026 → 2,552 | -1,474 (-36.61%) | 330 / 2,511 → 153 / 2,334 | 150 · +2,402 (+1601.33%) | 88 / 949 | 150 · +2,402 (+1601.33%) | 88 / 551 |

Fix 161 retains startup values through loops whose writes have known targets,
forgetting values that can change on the back edge. The compiler keeps the
function's suffix visible when it determines whether a loop counter remains
live. The regression checks the final counter of a loop expanded into fixed
array stores and the value computed using an unchanged global in a loop.

Fix 162 folds an absorbing right operand of a logical expression when
evaluating the left operand has no effects. Fix 163 collapses a nonempty
counted loop to one set of identical literal stores if none of its writes
can affect the predicates selecting those stores. Fix 164 expands short
indexed stores into fixed offsets when the code fits within the loop-control
budget. Fix 165 retries bounded expansion after nested loops simplify. Fix
166 removes earlier literal stores fully covered by later stores in the same
straight-line sequence. The regression checks the overlapping offset and a
read between stores.

Fix 167 folds a null check on `strchr` with known text and character, including
through a helper called with those literal arguments. The search stops at the
first zero byte and accepts a search for the terminator. zicc's pinned
`20000112-1.c` fixture explicitly qualifies the helper parameter as `__far`.
Both VBCC builds use the upstream spelling. zicc's before and after sources
are byte-identical.

Fix 168 carries a known startup integer through a direct update while
preserving the update instruction. Fix 169 replaces a bounded while loop with
its final counter when the rest of the body only changes private values that
are dead outside the loop. Fix 170 converts a known compound shift back to
the byte type before using the result. The narrower representation can
expose the next test of the byte's high bit.

The trial directories under `build/slower-f161-after` through
`build/slower-f170-after` retain the ROMs, assembly and repeated clocks.
`build/slower-b17-pre168` records the rebuilt startup-update baselines.
The final working-tree and isolated builds match the five published trial
ROMs at the end of their respective optimization chains.

### Inventory replay after batch 17

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared with
batch 16, 209 cases improved, 473 tied, and two took longer. Both pointer modes
of `no-const-pointers/seed-1` took 9,534 additional clocks (0.88%). Their
profiles showed 426 additional console instructions and 26 fewer
instructions outside the console. Both remain faster than their VBCC
reference. The four profiles are in `build/slower-b17-timing-regressions`.

A total of 517 cases closed all recorded VBCC gaps. The remaining 167 cases
are GCC. All 472 profiles for those cases matched. The 920 comparisons are in
`build/slower-b17-final-pairs.csv`, with replay and profile records in
`build/slower-b17-final-g`, `build/slower-b17-final-c`, and
`build/slower-b17-final-profiles`.


## Batch 18

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 171 | `20000224-1.c` | 28,042 → 9,850 | -18,192 (-64.87%) | 76 / 2,257 → 65 / 2,246 | 21,648 · -11,798 (-54.50%) | 151 / 1,030 | 23,862 · -14,012 (-58.72%) | 181 / 662 |
| 172 | `20000603-1.c` | 5,292 → 462 | -4,830 (-91.27%) | 132 / 2,313 → 100 / 2,267 | 452 · +10 (+2.21%) | 67 / 3,004 | 452 · +10 (+2.21%) | 65 / 2,604 |
| 173 | `20000603-1.c` | 462 → 60 | -402 (-87.01%) | 100 / 2,267 → 67 / 2,234 | 452 · -392 (-86.73%) | 67 / 3,004 | 452 · -392 (-86.73%) | 65 / 2,604 |
| 174 | `991019-1.c` | 57,690 → 1,010 | -56,680 (-98.25%) | 145 / 2,326 → 105 / 2,286 | 46,434 · -45,424 (-97.82%) | 504 / 3,459 | 44,414 · -43,404 (-97.73%) | 462 / 3,019 |
| 175 | `991019-1.c` | 1,010 → 58 | -952 (-94.26%) | 105 / 2,286 → 67 / 2,248 | 46,434 · -46,376 (-99.88%) | 504 / 3,459 | 44,414 · -44,356 (-99.87%) | 462 / 3,019 |
| 176 | `20100416-1.c` | 13,028 → 11,978 | -1,050 (-8.06%) | 232 / 2,413 → 214 / 2,395 | 8,022 · +3,956 (+49.31%) | 247 / 1,126 | BUILD 20100416-1-compile | - |
| 177 | `20021120-1.c` | 672,564 → 593,402 | -79,162 (-11.77%) | 4,695 / 7,263 → 4,695 / 7,291 | 637,396 · -43,994 (-6.90%) | 4,831 / 7,786 | 626,578 · -33,176 (-5.29%) | 4,618 / 7,175 |
| 178 | `20021120-1.c` | 593,402 → 557,670 | -35,732 (-6.02%) | 4,695 / 7,291 → 4,695 / 7,368 | 637,396 · -79,726 (-12.51%) | 4,831 / 7,786 | 626,578 · -68,908 (-11.00%) | 4,618 / 7,175 |
| 179 | `20000511-1.c` | 4,608 → 3,882 | -726 (-15.76%) | 269 / 667 → 161 / 559 | 3,892 · -10 (-0.26%) | 261 / 1,357 | 3,932 · -50 (-1.27%) | 261 / 959 |
| 180 | `20000511-1.c` | 3,882 → 58 | -3,824 (-98.51%) | 161 / 559 → 25 / 423 | 3,892 · -3,834 (-98.51%) | 261 / 1,357 | 3,932 · -3,874 (-98.52%) | 261 / 959 |

Fix 171 replaces a zero-based, unit-step counted increment of a distinct
word with one guarded addition of the runtime bound. It preserves an
observable final index. Fix 172 forwards a literal store to a matching
field or element load in the next effect-free expression. Fix 173 drops
fixed literal stores to a private aggregate that has no reads.

Fix 174 projects a constant call returning a single numeric field into
a field assignment when the call and the returned record have no other
effects. Fix 175 eliminates empty loops exposed during aggregate ABI
lowering. Fix 176 reduces invariant stores in a runtime-bounded loop to
one guarded copy of the writes and retains the final index.

Fix 177 doubles equal normal binary32 operands by incrementing the
exponent directly when the result stays finite. Fix 178 uses a 64-byte
table of high words for signed word-to-float magnitudes below 32. The
execution hooks for `20021120-1.c` counted one `_foo` call and 96 binary32
adds in each compiler lane, and 128 word-to-float conversions in each
zicc trial. This test uses the legacy binary32 ABI. The integer and
floating-point runtime checks also cover stage 4. The new NaN cases
reproduced a preexisting stage-4 return bug, corrected by discarding the
bank byte when the unpack helper uses a long call.

Fix 179 folds a known compound integer update while preserving the store
and separates that store from a surrounding assignment when its value is
known. Fix 180 also extracts the update from a direct call when all other
arguments are integer literals, then tries to fold the call with the
known argument. Identity compound operations can become reads during
refolding. The assignment rewrite checks that a store still exists.

All six cases use byte-identical test sources across the compiler lanes.
The `build/slower-f17*-*` and `build/slower-f180-effects` directories hold
the trial assembly, ROMs and timing repetitions. The hook evidence is in
the `batch18-workload` subdirectories of the floating-point trials.


### Inventory replay after batch 18

All 300 GCC runs passed and all 384 Csmith checksums matched. Compared
with batch 17, 47 cases improved, 634 tied, and three took longer.
`pr15262-2.c` took 116 more clocks and executed six extra binary32 engine
instructions on the equal-zero case. The two pointer modes of
`no-unary-plus/seed-123` produced identical ROMs and each took 10,124
more clocks (0.94%). Their profiles show 426 extra console instructions
and seven fewer instructions outside the console. Both Csmith cases
remain faster than their VBCC reference. The instruction counts are in
`build/slower-b18-timing-regressions`.

The isolated and working-tree builds produced identical ROMs for the
six measured cases. Each also matches its last trial in clocks and
application bytes. Four trials preceded the floating-point changes and
linked 28 fewer bytes than the final batch. The other two have identical
ROM hashes across all three builds.

A total of 529 cases closed every recorded VBCC gap. All 155 remaining
cases are GCC, and all 436 profiles for those cases matched. The 920
comparisons are in `build/slower-b18-final-pairs.csv`. Replay and profile
records are in `build/slower-b18-final-g`, `build/slower-b18-final-c`, and
`build/slower-b18-final-profiles`.


## Batch 19

| Fix | Case | zicc clocks before → after | Change | zicc code bytes app / linked before → after | Modified VBCC clocks and gap | Modified code bytes app / linked | Stock VBCC clocks and gap | Stock code bytes app / linked |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 181 | `20100416-1.c` | 11,978 → 11,068 | -910 (-7.60%) | 214 / 2,423 → 196 / 2,405 | 8,022 · +3,046 (+37.97%) | 247 / 1,126 | BUILD 20100416-1-compile | - |
| 182 | `20100416-1.c` | 11,068 → 9,908 | -1,160 (-10.48%) | 196 / 2,405 → 180 / 2,389 | 8,022 · +1,886 (+23.51%) | 247 / 1,126 | BUILD 20100416-1-compile | - |
| 183 | `pr15262-2.c` | 6,240 → 3,866 | -2,374 (-38.04%) | 132 / 2,341 → 132 / 2,356 | 3,068 · +798 (+26.01%) | 188 / 3,143 | 3,016 · +850 (+28.18%) | 185 / 2,742 |
| 184 | `pr22348.c` | 3,204 → 60 | -3,144 (-98.13%) | 43 / 441 → 19 / 417 | 68 · -8 (-11.76%) | 21 / 900 | 68 · -8 (-11.76%) | 21 / 502 |
| 185 | `930603-2.c` | 2,428 → 998 | -1,430 (-58.90%) | 115 / 2,339 → 79 / 2,303 | 388 · +610 (+157.22%) | 52 / 931 | 348 · +650 (+186.78%) | 44 / 525 |
| 186 | `930603-2.c` | 998 → 450 | -548 (-54.91%) | 79 / 2,303 → 52 / 450 | 388 · +62 (+15.98%) | 52 / 931 | 348 · +102 (+29.31%) | 44 / 525 |
| 187 | `20100416-1.c` | 9,908 → 8,494 | -1,414 (-14.27%) | 180 / 2,404 → 150 / 2,374 | 8,022 · +472 (+5.88%) | 247 / 1,126 | BUILD 20100416-1-compile | - |
| 188 | `loop-11.c` | 115,564 → 96,582 | -18,982 (-16.43%) | 87 / 485 → 74 / 472 | 110,154 · -13,572 (-12.32%) | 435 / 1,314 | 110,914 · -14,332 (-12.92%) | 444 / 925 |
| 189 | `930529-1.c` | 112,826 → 600 | -112,226 (-99.47%) | 657 / 5,150 → 38 / 4,531 | 105,434 · -104,834 (-99.43%) | 401 / 1,497 | 106,414 · -105,814 (-99.44%) | 414 / 1,112 |
| 190 | `20000910-2.c` | 5,900 → 3,938 | -1,962 (-33.25%) | 119 / 3,942 → 119 / 3,972 | 2,380 · +1,558 (+65.46%) | 93 / 1,035 | 2,248 · +1,690 (+75.18%) | 89 / 633 |

Fix 181 skips low words in fixed 64-bit comparisons when subtracting
them leaves carry unchanged. Fix 182 pushes near, nonvolatile wide
lvalues directly from their addressed words. The comparison and argument
tests cover both signednesses, boundary values and addresses with effects.

Fix 183 doubles matching binary32 subnormals in their encoded
significand, preserving signed zero and carrying into the first normal
exponent. Fix 184 computes the exit index of a positive-stride loop and
uses its range to prove when the body has no effects.

Fix 185 replaces an equality-filtered counted loop with one range test
and a possible execution of the selected iteration. It preserves a live
exit index and checks that the match value stays fixed. Fix 186 extends
short fixed-offset stores to guards that resolve at each copied index.
Fix 187 returns values directly from terminal stores to a private result
in a function using wide values.

Fix 188 avoids allocating a separate cursor for a direct indexed word
comparison with a byte or word stride. Hooks in both zicc trials and
both VBCC builds of `loop-11.c` recorded 398 array byte reads and 398
writes. Every final word matched its index. The hooks are preserved in
the `batch19-array-workload` subdirectories of the measured ROMs.

Fix 189 folds equality tests between a saved pure integer expression and
the same expression evaluated again. In `930529-1.c`, the before ROM
executed 3,072 instructions in the integer helper section. The after
ROM executes none there, while both VBCC builds execute 2,744 instructions
in their division section. These timings compare whole-program
optimization. Profiles are in `build/slower-b19-division-workload`.

Fix 190 gives forward `strchr` a smaller saved workspace and reads each
character once. The probes cover the terminator, truncation of the
search argument to a byte, and a pointer crossing a bank boundary.
The pinned zicc fixture for `20000910-2.c` qualifies its pointers
`__far`. Both VBCC lanes use the upstream spelling.


### Verification

The full `make check BINARY64=1` run reached 825 jobs and passed 818
before retakes. The initial terminal-store rewrite also ran in narrow
functions and folded away operands in two assembly probes. The final
rewrite uses the wide-function pipeline. Cursor pruning is limited to
indexed comparisons so a store loop can retain its cursor. The frame and
DP-home checks, comparisons, array codegen, all strength checks,
register loops, indexed direct-page checks, known values, indexed
operands and body codegen passed on retake. Three rounded-arithmetic
workers hit Mesen's Lua time limit under load. Those workers passed
serially against the original hashed fixtures and the collector passed
with all four reports.

The 300 GCC ROMs are byte-identical between the staged source scope and
the working tree. The start and final Csmith replays use the preexisting
working-tree compiler edits for Csmith. In the isolated source scope, 206
Csmith sources produced the same compiler errors with both batch 18 and
batch 19. The errors are recorded in
`build/slower-b19-isolated-baseline-errors.jsonl`.


### Inventory replay after batch 19

All 300 GCC runs passed and all 384 Csmith checksums matched. Relative to
batch 18, 11 GCC cases improved and the other 673 cases tied. Three more
GCC cases closed every recorded VBCC gap.

### Cumulative results from the original inventory

The zicc columns sum the archived runs for each original case once.
Clock counts cover `main` from entry to return or successful exit.
Application bytes and linked bytes count code and exclude data and ROM
padding. For the VBCC tables the arrow runs from the recorded VBCC lane
to final zicc. Lane totals cover the originally recorded pairs, with
zicc in FastROM and VBCC in SlowROM. The totals include whole-program
folding and any pointer-model differences recorded in the case data.

| Cases | Faster / tied / slower | zicc master clocks | Application code bytes | Linked code bytes |
| --- | ---: | ---: | ---: | ---: |
| GCC torture (300) | 205 / 94 / 1 | 189,491,194 → 54,467,490 (-135,023,704, -71.26%) | 98,896 → 50,449 (-48,447, -48.99%) | 636,431 → 500,453 (-135,978, -21.37%) |
| Csmith (384) | 384 / 0 / 0 | 1,266,835,348 → 441,072,068 (-825,763,280, -65.18%) | 6,809,120 → 4,331,602 (-2,477,518, -36.39%) | 10,239,144 → 7,839,194 (-2,399,950, -23.44%) |
| All (684) | 589 / 94 / 1 | 1,456,326,542 → 495,539,558 (-960,786,984, -65.97%) | 6,908,016 → 4,382,051 (-2,525,965, -36.57%) | 10,875,575 → 8,339,647 (-2,535,928, -23.32%) |

532 of 684 cases meet or beat every recorded VBCC lane.

Median per-case clock change is -60.13%.

### Final zicc versus the recorded VBCC pairs

| Cases | Faster / tied / slower | zicc master clocks | Application code bytes | Linked code bytes |
| --- | ---: | ---: | ---: | ---: |
| modified (678) | 532 / 0 / 146 | 848,673,914 → 495,501,888 (-353,172,026, -41.61%) | 1,237,074 → 4,381,368 (+3,144,294, +254.17%) | 11,618,930 → 8,332,924 (-3,286,006, -28.28%) |
| stock (242) | 113 / 0 / 129 | 8,190,630 → 6,142,058 (-2,048,572, -25.01%) | 60,122 → 30,986 (-29,136, -48.46%) | 214,915 → 351,472 (+136,557, +63.54%) |

The sole case slower than the original zicc inventory was
`950426-1.c`, up 24 clocks from 2,570 to 2,594. Application code shrank
from 165 to 154 bytes while linked code grew from 3,945 to 4,007 bytes.
The archived profiles in `build/slower-b19-start-regression` show two
fewer instructions in `main` and the same count in the string routine.

The 920 lane comparisons with timing, code sizes and relative changes
are in `build/slower-b19-cumulative/cases.csv`.


## Final sample and Dragon rechecks

See the [matched sample and Dragon FastROM results](slower-than-vbcc-final-benchmarks.md)
for the isolated pre-fix and final builds, including the instruction
trace accounting for the pathfield timing differences.
