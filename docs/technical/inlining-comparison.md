# Sample timings before and after the same-TU inlining changes

On zicc FastROM, Dhrystone took 62,747,618 master clocks before the change and 61,042,722 afterward for the same 3,000 iterations.

The first compiler was built separately from the structured code generation baseline. The second adds the same-TU inlining changes. Both passed 51 builds and 102 fresh NTSC measurements. Every ROM gave the same time on two runs. The sample sources matched after accounting for LF line endings in Git and CRLF in the working tree. The checks also kept and verified the original file hashes. Stock vbcc65816_r2 used `-O3 -msfp4` and gave the same times and sizes in both runs.

Before compiler SHA-256: `98707927f184682008855fbff3aa54f4e482eb4ad016231978887f0e607345d0`. After: `1c5d324c8ec213ab730c7d9aee9670236b8c0e46492958fac46624d8913858fa`.

## Dhrystone

3,000 verified iterations, excluding startup and printing. Code sizes are identical between FastROM and SlowROM.

| Configuration | Master clocks, before → after | Time reduction | Dhrystones/s, before → after |
| --- | ---: | ---: | ---: |
| zicc FastROM | 62,747,618 → 61,042,722 | 2.72% | 1,026.84 → 1,055.52 |
| zicc SlowROM | 73,013,668 → 71,227,870 | 2.45% | 882.46 → 904.59 |
| VBCC r2 SlowROM | 87,305,174 → 87,305,174 | 0.00% | 738.01 → 738.01 |

Dhrystones/s here is calculated from exact measured clocks using nominal NTSC 21,477,272 Hz, rather than the program’s rounded 60-Hz frame timer. The screenshot uses that coarser frame timer, with frame quantization and nominal-rate error.

| Code bytes | zicc before → after | VBCC r2 |
| --- | ---: | ---: |
| Application | 2,686 → 2,778 | 3,065 |
| All linked code | 8,136 → 8,228 | 13,178 |
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
| calc | 502 → 502 | 10,848 → 10,848 | 679 / 11,407 |
| insertion_sort | 322 → 322 | 2,205 → 2,205 | 437 / 900 |
| string_processing | 425 → 425 | 2,308 → 2,308 | 499 / 962 |
| integer_operations | 611 → 611 | 3,951 → 3,951 | 607 / 1,340 |
| function_calls | 259 → 259 | 3,599 → 3,599 | 438 / 1,025 |
| structures_and_tables | 365 → 365 | 3,705 → 3,705 | 405 / 992 |

## Original whole-program examples

These permit folding and inlining by either compiler. In particular, the VBCC integer example folds away its arithmetic and is not a runtime arithmetic throughput comparison.

| Sample | FastROM clocks, before → after | SlowROM clocks, before → after | App bytes, before → after | Linked bytes, before → after | VBCC clocks / app / linked |
| --- | ---: | ---: | ---: | ---: | ---: |
| minimal | 18,560 → 18,560 | 22,680 → 22,680 | 2 → 2 | 120 → 120 | 22,640 / 3 / 466 |
| prompt | 368,222 → 368,222 | 370,212 → 370,212 | 19 → 19 | 1,938 → 1,938 | 19,634 / 23 / 2,038 |
| calc | 504,406 → 503,868 | 529,282 → 528,718 | 502 → 573 | 10,848 → 10,919 | 1,502,818 / 2,184 / 12,912 |
| insertion_sort | 14,386 → 14,386 | 16,844 → 16,844 | 322 → 322 | 2,205 → 2,205 | 35,430 / 729 / 1,192 |
| string_processing | 12,088 → 12,088 | 14,454 → 14,454 | 418 → 418 | 2,301 → 2,301 | 25,152 / 854 / 1,317 |
| integer_operations | 2,664 → 1,866 | 3,104 → 2,116 | 120 → 183 | 3,460 → 3,523 | 202 / 89 / 552 |
| function_calls | 79,602 → 78,084 | 91,368 → 89,608 | 259 → 291 | 3,599 → 3,631 | 146,150 / 550 / 1,137 |
| structures_and_tables | 13,412 → 13,412 | 16,012 → 16,012 | 534 → 534 | 3,874 → 3,874 | 7,652 / 501 / 1,088 |

FastROM/SlowROM zicc ROMs differ only in MEMSEL, the header speed bit and checksum; placement, instructions and runtime selection match. VBCC uses stock SlowROM LoROM and 32-bit pointers; zicc uses HiROM with near 16-bit / padded far pointers. Console implementations and linked runtime scope differ. Compare SlowROM against SlowROM to isolate memory speed. Code sizes exclude data, assets and padding. Container sizes are not code sizes.

See [implementation and selection rules](inlining.md) and [current three-compiler matrix](inlining-current-comparison.md).

Raw before evidence: `C:\snesdev\compiler\build\inlining\before-checkout\build\before-samples`. Raw after evidence: `C:\snesdev\compiler\build\inlining\after-samples`. Both retain generated assembly, map/allocation files, ROMs, Lua execution assertions, compiler/runtime/source hashes and repeated logs. The full Dhrystone verification also captured an NTSC screenshot.
