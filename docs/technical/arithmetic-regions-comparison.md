# Sample timings before and after the arithmetic-region and runtime changes

On zicc FastROM, Dhrystone took 61,042,722 master clocks before the change and 61,005,636 afterward for the same 3,000 iterations.

The first compiler was built separately from the source LTO baseline. The second adds the arithmetic-region and runtime changes. Both passed 51 builds and 102 fresh NTSC measurements. Every ROM gave the same time on two runs. The sample sources matched after accounting for LF line endings in Git and CRLF in the working tree. The checks also kept and verified the original file hashes. Stock vbcc65816_r2 used `-O3 -msfp4` and gave the same times and sizes in both runs.

Before compiler SHA-256: `9602e34b9ca64667b403f92232bf5a4e243de79ab01ce3cfd93c54c6e0136d7b`. After: `ae6812f749fe204c960d9d0c65bd1451c51aa517eb3ec593402294c147152c72`.

## Dhrystone

3,000 verified iterations, excluding startup and printing. Code sizes are identical between FastROM and SlowROM.

| Configuration | Master clocks, before → after | Time reduction | Dhrystones/s, before → after |
| --- | ---: | ---: | ---: |
| zicc FastROM | 61,042,722 → 61,005,636 | 0.06% | 1,055.52 → 1,056.16 |
| zicc SlowROM | 71,227,870 → 71,184,596 | 0.06% | 904.59 → 905.14 |
| VBCC r2 SlowROM | 87,305,174 → 87,305,174 | 0.00% | 738.01 → 738.01 |

Dhrystones/s here is calculated from exact measured clocks using nominal NTSC 21,477,272 Hz, rather than the program’s rounded 60-Hz frame timer. The screenshot uses that coarser frame timer, with frame quantization and nominal-rate error.

| Code bytes | zicc before → after | VBCC r2 |
| --- | ---: | ---: |
| Application | 2,778 → 2,769 | 3,065 |
| All linked code | 8,228 → 8,339 | 13,178 |
| ROM container | 65,536 → 65,536 | 163,840 |

## Other samples: matched runtime work

Drivers and opaque kernels are separate translation units without LTO. Hooks require the expected calls, inputs, iterations/operations and results; return values alone are not used as proof of work. Minimal counts 1,000 idle iterations. Prompt and calc include their console work and retain their existing measurement boundaries.

| Sample | FastROM clocks, before → after | SlowROM clocks, before → after | VBCC r2 SlowROM |
| --- | ---: | ---: | ---: |
| minimal | 18,560 → 18,560 | 22,680 → 22,680 | 22,640 |
| prompt | 368,240 → 368,240 | 370,228 → 370,228 | 19,666 |
| calc | 504,406 → 504,406 | 529,282 → 529,282 | 1,506,030 |
| insertion_sort | 14,386 → 14,386 | 16,844 → 16,844 | 37,040 |
| string_processing | 14,796 → 14,796 | 17,224 → 17,224 | 28,988 |
| integer_operations | 35,798 → 35,798 | 41,218 → 41,218 | 77,748 |
| function_calls | 79,602 → 79,602 | 91,368 → 91,368 | 153,910 |
| structures_and_tables | 14,180 → 14,180 | 16,832 → 16,832 | 26,012 |

| Sample | Application bytes, before → after | Linked code bytes, before → after | VBCC app / linked |
| --- | ---: | ---: | ---: |
| minimal | 9 → 9 | 127 → 127 | 11 / 474 |
| prompt | 23 → 23 | 1,942 → 1,942 | 27 / 2,042 |
| calc | 502 → 502 | 10,848 → 10,968 | 679 / 11,407 |
| insertion_sort | 322 → 322 | 2,205 → 2,205 | 437 / 900 |
| string_processing | 425 → 425 | 2,308 → 2,308 | 499 / 962 |
| integer_operations | 611 → 611 | 3,951 → 4,071 | 607 / 1,340 |
| function_calls | 259 → 259 | 3,599 → 3,719 | 438 / 1,025 |
| structures_and_tables | 365 → 365 | 3,705 → 3,825 | 405 / 992 |

## Original whole-program examples

These permit folding and inlining by either compiler. In particular, the VBCC integer example folds away its arithmetic and is not a runtime arithmetic throughput comparison.

| Sample | FastROM clocks, before → after | SlowROM clocks, before → after | App bytes, before → after | Linked bytes, before → after | VBCC clocks / app / linked |
| --- | ---: | ---: | ---: | ---: | ---: |
| minimal | 18,560 → 18,560 | 22,680 → 22,680 | 2 → 2 | 120 → 120 | 22,640 / 3 / 466 |
| prompt | 368,222 → 368,222 | 370,212 → 370,212 | 19 → 19 | 1,938 → 1,938 | 19,634 / 23 / 2,038 |
| calc | 503,868 → 503,868 | 528,718 → 528,718 | 573 → 573 | 10,919 → 11,039 | 1,502,818 / 2,184 / 12,912 |
| insertion_sort | 14,386 → 14,386 | 16,844 → 16,844 | 322 → 322 | 2,205 → 2,205 | 35,430 / 729 / 1,192 |
| string_processing | 12,088 → 12,088 | 14,454 → 14,454 | 418 → 418 | 2,301 → 2,301 | 25,152 / 854 / 1,317 |
| integer_operations | 1,866 → 1,502 | 2,116 → 1,728 | 183 → 141 | 3,523 → 3,601 | 202 / 89 / 552 |
| function_calls | 78,084 → 78,084 | 89,608 → 89,608 | 291 → 291 | 3,631 → 3,751 | 146,150 / 550 / 1,137 |
| structures_and_tables | 13,412 → 13,412 | 16,012 → 16,012 | 534 → 534 | 3,874 → 3,994 | 7,652 / 501 / 1,088 |

FastROM/SlowROM zicc ROMs differ only in MEMSEL, the header speed bit and checksum; placement, instructions and runtime selection match. VBCC uses stock SlowROM LoROM and 32-bit pointers; zicc uses HiROM with near 16-bit / padded far pointers. Console implementations and linked runtime scope differ. Compare SlowROM against SlowROM to isolate memory speed. Code sizes exclude data, assets and padding. Container sizes are not code sizes.

See [implementation and selection rules](arithmetic-regions.md) and [current three-compiler matrix](arithmetic-regions-current-comparison.md).

Raw before evidence: `C:\snesdev\compiler\build\pi-optimization\before-checkout\build\before-samples`. Raw after evidence: `C:\snesdev\compiler\build\pi-optimization\after-samples`. Both retain generated assembly, map/allocation files, ROMs, Lua execution assertions, compiler/runtime/source hashes and repeated logs. The full Dhrystone verification also captured an NTSC screenshot.


## PI: complete calculation and display

The C calculation and console sources are unchanged, compiled as separate translation units without LTO. Both sides verify all 897 emitted characters, 2,411,135 work-array writes, the final array, VRAM and stable screenshots. The original algorithm retains its byte truncation and only 42 correct mathematical pi digits. Kernel time includes per-digit console calls; boot-to-display includes startup and final display flush. The frame-extended counter handles 32-bit master-clock wraps.

| Configuration | Kernel clocks, before → after | Kernel time reduction | Boot-to-display seconds, before → after |
| --- | ---: | ---: | ---: |
| original | 16,931,028,338 → 16,931,028,338 | 0.00% | 788.432538 → 788.432538 |
| zicc-fast | 14,767,631,596 → 7,564,601,374 | 48.78% | 687.881466 → 352.500459 |
| zicc-slow | 17,076,605,654 → 8,801,490,914 | 48.46% | 795.387751 → 410.088952 |
| vbcc-slow | 16,412,404,774 → 16,412,404,774 | 0.00% | 764.305605 → 764.305605 |

| Configuration | Application bytes, before → after | Linked code bytes, before → after | ROM bytes |
| --- | ---: | ---: | ---: |
| original | 1,169 → 1,169 | unavailable | 262,144 → 262,144 |
| zicc-fast | 661 → 513 | 5,836 → 5,808 | 65,536 → 65,536 |
| zicc-slow | 661 → 513 | 5,836 → 5,808 | 65,536 → 65,536 |
| vbcc-slow | 1,155 → 1,155 | 3,579 → 3,579 | 163,840 → 163,840 |

The supplied original ROM is FastROM LoROM; stock VBCC is SlowROM LoROM, while zicc uses identical HiROM placement for both speeds. The original has no complete linked-code map. Code sizes exclude assets/data/padding. The final line extends offscreen in the supplied layout: completion verifies the entire stream and VRAM, rather than claiming every character fits simultaneously on screen.



## Additional imported samples

Whetstone and BouncingSprites were also rebuilt with unchanged source. Their
existing zicc near-pointer/language compatibility errors remain in both speeds;
stock VBCC builds link. No zicc runtime or before/after timing is claimed for
these unsupported imports. Diagnostics and input hashes are retained in
`build/pi-optimization/after-homebrew/results.json`; baseline import diagnostics
remain in `build/homebrew-samples/recorded/results.json`.

## Verification scope

A full `make check` followed by focused fixes and changed-suite verification
covers all 27 suites and all 200,873 arithmetic cases. Failed attempts remain in
the evidence directory. The final immediate-equality cost guard reuses the
existing word-comparison path; comparisons, strings, byte predicates,
indexed/register loops and the new arithmetic-region tests were rerun for this
scoped refinement. The compiler is frozen across accepted benchmark runs.
