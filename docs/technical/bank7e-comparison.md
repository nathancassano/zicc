# DBR $7E sample comparison

With data bank register DBR set to $7E, the original string example took 86,932 master clocks. The last build took 13,122. Accessing ROM strings through far pointers added work. The minimal example took 18,560 clocks on both builds.

The test rebuilt eight FastROM samples in two forms. One uses the original program. The other compiles the caller and its functions separately with link-time optimization off. Each build ran twice and gave the same times and call counts. The emulator checked calls, inputs, results, loop work and hardware multiply counts. Each compiler used the saved runtime for its own calling rules.

The saved last build is at `build/bank7e-change/last-sample-builds/` and the freshly rebuilt baseline is at `build/bank7e-change/baseline/`. The candidate assembly, maps, ROMs, hashes, scripts and logs are at `build/bank7e-change/candidate/`. The file `sample-deltas.json` records both baselines. Timings include function calls and runtime work. Minimal runs 1,000 idle iterations, prompt finishes its screen update, and the calculator evaluates one expression.

All files remain 32768 bytes. Code means STARTUP + CODE; used ROM additionally
includes RODATA/header/vectors and excludes the 2056-byte console assets.

| Sample | Form | Last clocks | Current clocks | Change | Code bytes, last -> current | Used ROM, last -> current |
|---|---|---:|---:|---:|---:|---:|
| minimal | original | 18560 | 18560 | +0.00% | 99 -> 94 | 163 -> 158 |
| minimal | runtime | 18560 | 18560 | +0.00% | 109 -> 104 | 173 -> 168 |
| prompt | original | 374568 | 374578 | +0.00% | 1913 -> 2114 | 1980 -> 2181 |
| prompt | runtime | 374648 | 374646 | -0.00% | 1923 -> 2124 | 1990 -> 2191 |
| calc | original | 586872 | 644700 | +9.85% | 12541 -> 15162 | 13021 -> 15642 |
| calc | runtime | 586872 | 644700 | +9.85% | 12541 -> 15162 | 13021 -> 15642 |
| insertion_sort | original | 30024 | 30008 | -0.05% | 499 -> 518 | 563 -> 582 |
| insertion_sort | runtime | 30024 | 30008 | -0.05% | 499 -> 518 | 563 -> 582 |
| string_processing | original | 13122 | 86932 | +562.49% | 504 -> 980 | 607 -> 1083 |
| string_processing | runtime | 13122 | 86932 | +562.49% | 504 -> 980 | 607 -> 1083 |
| integer_operations | original | 26350 | 26642 | +1.11% | 1996 -> 2077 | 2060 -> 2141 |
| integer_operations | runtime | 45398 | 45762 | +0.80% | 2102 -> 2183 | 2166 -> 2247 |
| function_calls | original | 104004 | 104656 | +0.63% | 1821 -> 1902 | 1885 -> 1966 |
| function_calls | runtime | 104004 | 104656 | +0.63% | 1821 -> 1902 | 1885 -> 1966 |
| structures_and_tables | original | 13884 | 31166 | +124.47% | 1783 -> 2140 | 1871 -> 2228 |
| structures_and_tables | runtime | 13884 | 31166 | +124.47% | 1783 -> 2140 | 1871 -> 2228 |

ROM string/table readers now explicitly accept `__far` pointers. The same kernels
also accept near RAM through widening. Calculator parsing keeps its RAM cursor
near and explicitly narrows the far strtod end pointer, whose origin is that RAM
buffer. The qualifiers are blank on host/reference compilers. Hardware registers
use explicit bank-zero addresses; ordinary allocations start at $7E:2000.

The large string/inventory regressions are real. Existing 16-bit register-loop,
counted-reduction and shared-member selectors deliberately decline far addresses.
Their general lowering maintains four-byte pointer values and full address
arithmetic. Known named ROM reads use absolute-long,X, but arbitrary passed-around
far pointers in this build use long-indirect DP scratch. The CPU's long MMIO instructions add
one instruction byte and affect the smaller integer/call deltas. This is a bank
ABI change, not an isolated instruction-selection comparison.

The historical last builds predate intervening committed changes. Fresh
prechange measurements differ for prompt, calc and insertion sort; the JSON
retains both baselines so the entire historical delta is not attributed to this
migration. In particular, sort is slightly faster than its last recorded build
but slower than the fresh prechange build. The table above answers the requested
last-build comparison; `sample-deltas.json` also isolates the immediate migration.

Dhrystone compiles and assembles. A stock-runtime link no longer overflows near
RAM and now reports only unresolved malloc, strcpy and strcmp. The diagnostic
`dhrystone/layout-only.map` uses explicitly nonfunctional labels only to obtain
layout: BSS 5396, DATA 2 and console map 2048 bytes, total 7446, occupying
$7E:2000-$7E:3D15. The 56 KiB general allocator has 49898 bytes left before heap
allocation. This diagnostic image is not runnable. Library allocation/string
functions, proper declarations for the generic readers, formatted Dhrystone
output and explicit application NMI enabling are still needed for a benchmark run.
The supplied C64 timing configuration hardcodes 60 Hz and also needs the runtime
clock rate before a PAL benchmark is meaningful.
