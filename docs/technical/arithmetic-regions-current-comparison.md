# Source LTO baseline timing and code size

Dhrystone finished 3,000 iterations in 61,005,636 master clocks with zicc FastROM, 71,184,596 with zicc SlowROM, and 87,305,174 with stock VBCC SlowROM. A smaller count means a shorter run.

This comparison uses the saved zicc build from the source LTO baseline with local changes. Stock vbcc65816_r2 used `-O3 -msfp4`. The zicc compiler had SHA-256 `ae6812f749fe204c960d9d0c65bd1451c51aa517eb3ec593402294c147152c72`. All 51 builds and 102 measurements passed. Each ROM ran twice in a fresh NTSC emulator process. The two times matched for every ROM.

The two zicc builds put the same instructions and runtime in the same HiROM banks. SlowROM sets MEMSEL to zero at startup and clears the header speed bit. A byte comparison checked that only those settings and the checksum changed. The Dhrystone startup checks verified MEMSEL and the execution bank in all three builds. VBCC used its stock SlowROM LoROM layout. The timings skip startup.

## Master clocks (lower is faster)

| Sample / mode | zicc FastROM | zicc SlowROM | VBCC r2 SlowROM |
| --- | ---: | ---: | ---: |
| minimal / original | 18,560 | 22,680 | 22,640 |
| minimal / runtime | 18,560 | 22,680 | 22,640 |
| prompt / original | 368,222 | 370,212 | 19,634 |
| prompt / runtime | 368,240 | 370,228 | 19,666 |
| calc / original | 503,868 | 528,718 | 1,502,818 |
| calc / runtime | 504,406 | 529,282 | 1,506,030 |
| insertion_sort / original | 14,386 | 16,844 | 35,430 |
| insertion_sort / runtime | 14,386 | 16,844 | 37,040 |
| string_processing / original | 12,088 | 14,454 | 25,152 |
| string_processing / runtime | 14,796 | 17,224 | 28,988 |
| integer_operations / original | 1,502 | 1,728 | 202 |
| integer_operations / runtime | 35,798 | 41,218 | 77,748 |
| function_calls / original | 78,084 | 89,608 | 146,150 |
| function_calls / runtime | 79,602 | 91,368 | 153,910 |
| structures_and_tables / original | 13,412 | 16,012 | 7,652 |
| structures_and_tables / runtime | 14,180 | 16,832 | 26,012 |
| dhrystone / original | 61,005,636 | 71,184,596 | 87,305,174 |

## Application code bytes

| Sample / mode | zicc FastROM | zicc SlowROM | VBCC r2 SlowROM |
| --- | ---: | ---: | ---: |
| minimal / original | 2 | 2 | 3 |
| minimal / runtime | 9 | 9 | 11 |
| prompt / original | 19 | 19 | 23 |
| prompt / runtime | 23 | 23 | 27 |
| calc / original | 573 | 573 | 2,184 |
| calc / runtime | 502 | 502 | 679 |
| insertion_sort / original | 322 | 322 | 729 |
| insertion_sort / runtime | 322 | 322 | 437 |
| string_processing / original | 418 | 418 | 854 |
| string_processing / runtime | 425 | 425 | 499 |
| integer_operations / original | 141 | 141 | 89 |
| integer_operations / runtime | 611 | 611 | 607 |
| function_calls / original | 291 | 291 | 550 |
| function_calls / runtime | 259 | 259 | 438 |
| structures_and_tables / original | 534 | 534 | 501 |
| structures_and_tables / runtime | 365 | 365 | 405 |
| dhrystone / original | 2,769 | 2,769 | 3,065 |

## All linked code bytes

| Sample / mode | zicc FastROM | zicc SlowROM | VBCC r2 SlowROM |
| --- | ---: | ---: | ---: |
| minimal / original | 120 | 120 | 466 |
| minimal / runtime | 127 | 127 | 474 |
| prompt / original | 1,938 | 1,938 | 2,038 |
| prompt / runtime | 1,942 | 1,942 | 2,042 |
| calc / original | 11,039 | 11,039 | 12,912 |
| calc / runtime | 10,968 | 10,968 | 11,407 |
| insertion_sort / original | 2,205 | 2,205 | 1,192 |
| insertion_sort / runtime | 2,205 | 2,205 | 900 |
| string_processing / original | 2,301 | 2,301 | 1,317 |
| string_processing / runtime | 2,308 | 2,308 | 962 |
| integer_operations / original | 3,601 | 3,601 | 552 |
| integer_operations / runtime | 4,071 | 4,071 | 1,340 |
| function_calls / original | 3,751 | 3,751 | 1,137 |
| function_calls / runtime | 3,719 | 3,719 | 1,025 |
| structures_and_tables / original | 3,994 | 3,994 | 1,088 |
| structures_and_tables / runtime | 3,825 | 3,825 | 992 |
| dhrystone / original | 8,339 | 8,339 | 13,178 |

Runtime rows compile identical drivers and kernels separately without LTO; hooks assert required calls, inputs and results. Original rows allow whole-program folding/inlining and must not be interpreted as matched arithmetic throughput. Dhrystone uses its original two source files (merged only with --lto); 3,000 Proc_8 and Func_2 executions, per-iteration array state, input strings and final globals/records are checked. Its interval is return from the first clock call to entry of the second, excluding printing.

Minimal measures 1,000 idle iterations; prompt stops after its first print/flush; calculator measures its first printf through the result printf for `(12 + 3) * 4 / 2`. Console/flush behavior differs. zicc uses IEEE binary32 and near 16-bit / padded far pointers; stock VBCC uses MSFP4 and 32-bit pointers. Linked runtime selection and console implementations differ. Code sizes exclude font assets, data and ROM padding. zicc ROM containers are 64 KiB; stock VBCC containers may be larger and are not code size.

Raw ROMs, generated assembly, linker maps, allocation manifests, symbols, commands, Lua assertions, repeated logs and hashes are retained beside this report.

VBCC sample builds define `__ZICC__` and an empty `__dpage` to bypass host-only qualifier shims while preserving VBCC's native `__far`; C source bytes remain unchanged. Optional missing vcpr6502 config commands are omitted. Compiler and runtime/library hashes are in inputs.json. The compiler executable is preserved as zicc.exe.

The benchmark did not modify compiler implementation or workload sources.

Dhrystone time relative to stock VBCC SlowROM: zicc FastROM -30.1%; zicc SlowROM -18.5%. Application code size relative to VBCC: -9.7%; total linked code: -36.7%.

Several small zicc examples link more runtime code than VBCC despite smaller application functions; consult both size tables. Dhrystone timing includes each runtime's normal interrupt overhead.

Evidence: `C:\snesdev\compiler\build\pi-optimization\after-samples`. Superseded SlowROM header measurements and first-attempt failure logs remain in that directory; comparison.json and verification.json identify the accepted final results.
