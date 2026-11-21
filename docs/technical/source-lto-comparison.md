# Letting zicc optimize across C files

With source LTO, zicc can optimize calls between C files. On FastROM, the same 3,000 Dhrystone iterations took 61,042,722 master clocks with separate compilation and 59,939,474 with source LTO.

The first compiler used the same-unit inlining baseline and passed 51 builds and 102 NTSC measurements. The second enabled source LTO for the application and passed 75 builds and 150 measurements. Each ROM gave the same time twice. The extra rows show what happens when the same split source files are built with and without LTO. Stock vbcc65816_r2 used `-O3 -msfp4` without LTO in every run.

Compiler SHA-256 before: `586f9ebd122cb482819a11eb2a805309952ffe7f91d8ea43609cec319fc70121`; after: `5a925527ab6d2159415275f43b1b3e2c3cfdda76d971242a6203f17c184f2575`. Source contents match after CRLF/LF normalization; raw hashes are independently verified.

## Dhrystone

Original two-file C source, 3,000 verified iterations. Before compiles separately; after merges typed inputs for cross-TU optimization. Startup and result printing are excluded.

| Configuration | Master clocks, before -> after | Time reduction | Dhrystones/s, before -> after |
| --- | ---: | ---: | ---: |
| zicc FastROM | 61,042,722 -> 59,939,474 | 1.81% | 1,055.52 -> 1,074.95 |
| zicc SlowROM | 71,227,870 -> 70,093,330 | 1.59% | 904.59 -> 919.23 |
| VBCC r2 SlowROM | 87,305,174 -> 87,305,174 | 0.00% | 738.01 -> 738.01 |

Rates use exact clocks at nominal NTSC 21,477,272 Hz. The program screen uses its coarser 60-Hz frame timer.

| Size | zicc before -> after | VBCC r2 |
| --- | ---: | ---: |
| Application code bytes | 2,778 -> 2,832 | 3,065 |
| All linked code bytes | 8,228 -> 8,282 | 13,178 |
| ROM container bytes | 65,536 -> 65,536 | 163,840 |

LTO exposes Proc_7 to callers in dhry_1.c; assembly records expansions in main and Proc_1. It also makes existing whole-unit analyses available across the source boundary. Selection keeps the existing pressure/growth budgets. Public out-of-line definitions remain emitted. Dhrystone adds 54 application/linked code bytes.

The independent full verifier passes NTSC twice and PAL once for each speed. It counts ABI entries and zero-byte inline markers, checks 3,000 Proc_8/Func_2 executions, per-iteration arrays and string arguments, final locals/globals/records, stack/DP/DBR, printed report, presented VRAM and every screenshot pixel. Matrix hooks independently check timed iterations and state. Fast/Slow ROM byte differences are limited to MEMSEL, header speed and checksum; live speed/bank probes pass.

## Split sources: separate compilation -> source LTO

Identical drivers/kernels before without LTO and after with LTO. These are whole-program optimization results, permitting specialization, folding and inlining, rather than matched arithmetic-throughput claims. Separate-TU controls below keep the strict workload requirement.

| Sample | FastROM clocks, before -> LTO | SlowROM clocks, before -> LTO | App bytes, before -> LTO | Linked bytes, before -> LTO |
| --- | ---: | ---: | ---: | ---: |
| minimal | 18,560 -> 18,560 | 22,680 -> 22,680 | 9 -> 9 | 127 -> 127 |
| prompt | 368,240 -> 368,240 | 370,228 -> 370,228 | 23 -> 23 | 1,942 -> 1,942 |
| calc | 504,406 -> 503,868 | 529,282 -> 528,718 | 502 -> 573 | 10,848 -> 10,919 |
| insertion_sort | 14,386 -> 14,386 | 16,844 -> 16,844 | 322 -> 322 | 2,205 -> 2,205 |
| string_processing | 14,796 -> 12,088 | 17,224 -> 14,454 | 425 -> 418 | 2,308 -> 2,301 |
| integer_operations | 35,798 -> 35,650 | 41,218 -> 41,024 | 611 -> 620 | 3,951 -> 3,960 |
| function_calls | 79,602 -> 78,084 | 91,368 -> 89,608 | 259 -> 291 | 3,599 -> 3,631 |
| structures_and_tables | 14,180 -> 13,412 | 16,832 -> 16,012 | 365 -> 534 | 3,705 -> 3,874 |

Assembly inspection: calc expands num_exp into prim_exp; integer_operations expands word_add/word_sub/signed_add/unsigned_div while keeping opaque input reads; function_calls expands add_scaled and keeps recursive factorial/fibonacci calls. String and inventory gains use cross-unit bank specialization rather than inline substitutions: all 3 copy, 4 reverse, 4 equality, 3 inventory and 2 adjustment calls still execute. Inventory keeps four products and 28 hardware multiplier writes. Integer keeps 10 hardware multiplier writes. Missing ABI calls alone do not establish eliminated operations.

## Separate-TU runtime controls

All eight rows keep identical clocks and application/linked sizes before and after when LTO is disabled; all 16 zicc FastROM/SlowROM control ROMs are byte-identical to baseline. Strict hooks assert required calls, inputs, iterations/products and results. These are the matched runtime workload controls.

| Sample | FastROM clocks | SlowROM clocks | App / linked bytes | VBCC SlowROM clocks / app / linked |
| --- | ---: | ---: | ---: | ---: |
| minimal | 18,560 | 22,680 | 9 / 127 | 22,640 / 11 / 474 |
| prompt | 368,240 | 370,228 | 23 / 1,942 | 19,666 / 27 / 2,042 |
| calc | 504,406 | 529,282 | 502 / 10,848 | 1,506,030 / 679 / 11,407 |
| insertion_sort | 14,386 | 16,844 | 322 / 2,205 | 37,040 / 437 / 900 |
| string_processing | 14,796 | 17,224 | 425 / 2,308 | 28,988 / 499 / 962 |
| integer_operations | 35,798 | 41,218 | 611 / 3,951 | 77,748 / 607 / 1,340 |
| function_calls | 79,602 | 91,368 | 259 / 3,599 | 153,910 / 438 / 1,025 |
| structures_and_tables | 14,180 | 16,832 | 365 / 3,705 | 26,012 / 405 / 992 |

## Original single-file samples

All eight originals keep identical measured clocks and application/linked sizes with source LTO. Same-TU inlining was already enabled before.

| Sample | FastROM clocks | SlowROM clocks | App / linked bytes |
| --- | ---: | ---: | ---: |
| minimal | 18,560 | 22,680 | 2 / 120 |
| prompt | 368,222 | 370,212 | 19 / 1,938 |
| calc | 503,868 | 528,718 | 573 / 10,919 |
| insertion_sort | 14,386 | 16,844 | 322 / 2,205 |
| string_processing | 12,088 | 14,454 | 418 / 2,301 |
| integer_operations | 1,866 | 2,116 | 183 / 3,523 |
| function_calls | 78,084 | 89,608 | 291 / 3,631 |
| structures_and_tables | 13,412 | 16,012 | 534 / 3,874 |

## Scope and evidence

Minimal times 1,000 idle iterations. Prompt includes its first console flush. Calculator times its first printf through the checked result of `(12 + 3) * 4 / 2`. Console/runtime implementations and pointer/float ABIs differ from VBCC (zicc IEEE binary32 versus MSFP4; near16/padded far24 versus stock VBCC pointer representation). Compare the same memory speed when isolating code generation. Linked code excludes assets, data and padding. All zicc containers remain 64 KiB; container size is not code size.

Full make check: 27/27 suites pass, preserving all 200,873 arithmetic cases. Benchmark recovery resumes only missing infrastructure-failed measurements. No semantic assertion failure was discarded. First-attempt logs remain.

Baseline evidence: `C:\snesdev\compiler\build\source-lto\before-checkout\build\before-samples`. After: `C:\snesdev\compiler\build\source-lto\after-samples`. Full-screen/timing evidence: `C:\snesdev\compiler\build\source-lto\final-performance`. Commands, assembly, maps, ROMs, repeated logs, assertions and source/compiler/runtime/tool hashes remain available. Complete current/VBCC tables: [matrix report](source-lto-current-comparison.md).
