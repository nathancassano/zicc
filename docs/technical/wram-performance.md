# WRAM reallocation: FastROM NTSC performance

Moving near variables lower in work RAM left the application's instructions and code size the same in all 34 images. The added startup check took 36 master clocks and added 15 bytes of startup code. Some timed sections then met a memory refresh at a different point.

Evidence for this historical isolated comparison is in `E:/archived-compiler/worktree-low-wram-evaluation.zip`, under `.worktrees/low-wram-evaluation/build/`. The measurements precede master's later loop optimizations; master integration is verified separately.

The saved baseline used the original high stack and near-WRAM placement. The candidate was the isolated low-WRAM implementation. Both use the automatic FastROM HiROM builder, stage 1, native A/X/Y16, D=0, DBR=$7E and the same near/far pointer ABI. The stack changes from $1FFF to $04FF and near allocation from $7E2000 to $7E0500. Bank-$7F buffer changes are excluded.

All 34 images have three agreeing fresh-process NTSC measurements: 102 successful runs, plus three phase-control measurements. Sources and headers match within each original/split pair. All application instruction lists (symbolic assembly operands) and application code sizes, including Dhrystone, match before/after; linked operand addresses and ROM hashes change with placement. Runtime sources differ only in startup. Hardware MEMSEL writes and entry DBR/D/stack are asserted. Master clocks and CPU cycles are recorded independently.

The split runtime rows compile drivers and kernels separately without LTO; existing execution assertions check expected calls, inputs and results, including twelve integer kernels, four inventory products, parser calls and recursive driver calls. Original rows retain legitimate whole-program optimizations and are not isolated arithmetic-throughput claims.

## Original samples

| Sample | Before clocks | After clocks | Delta | Time change | CPU cycles before / after |
|---|---:|---:|---:|---:|---:|
| minimal | 18,560 | 18,560 | +0 | +0.0000% | 3,000 / 3,000 |
| prompt | 368,208 | 368,156 | -52 | -0.0141% | 54,849 / 54,841 |
| calc | 502,974 | 502,882 | -92 | -0.0183% | 74,788 / 74,780 |
| insertion_sort | 30,008 | 30,008 | +0 | +0.0000% | 4,495 / 4,495 |
| string_processing | 12,736 | 12,736 | +0 | +0.0000% | 1,965 / 1,965 |
| integer_operations | 26,642 | 26,642 | +0 | +0.0000% | 3,877 / 3,877 |
| function_calls | 104,350 | 104,350 | +0 | +0.0000% | 15,692 / 15,692 |
| structures_and_tables | 14,452 | 14,452 | +0 | +0.0000% | 2,191 / 2,191 |

## Split driver/kernel samples

| Sample | Before clocks | After clocks | Delta | Time change | CPU cycles before / after |
|---|---:|---:|---:|---:|---:|
| minimal | 18,560 | 18,560 | +0 | +0.0000% | 3,000 / 3,000 |
| prompt | 368,284 | 368,220 | -64 | -0.0174% | 54,859 / 54,851 |
| calc | 502,974 | 502,882 | -92 | -0.0183% | 74,788 / 74,780 |
| insertion_sort | 30,008 | 30,008 | +0 | +0.0000% | 4,495 / 4,495 |
| string_processing | 15,404 | 15,444 | +40 | +0.2597% | 2,297 / 2,297 |
| integer_operations | 45,762 | 45,762 | +0 | +0.0000% | 6,610 / 6,610 |
| function_calls | 104,350 | 104,350 | +0 | +0.0000% | 15,692 / 15,692 |
| structures_and_tables | 15,690 | 15,690 | +0 | +0.0000% | 2,364 / 2,364 |

## Dhrystone

The unmodified two-TU Dhrystone 2.1 driver performs 3,000 iterations in both images. Hooks require every expected Proc/Func invocation, check live Proc_7/Proc_8/Func_2 inputs and per-iteration array state, verify final allocated-record links/contents, globals, local reports, timer arithmetic, final VRAM and the rendered 512x224 screen. Console reports match after normalizing the expected relocated record addresses; each screenshot is verified against its own report rather than requiring identical address digits. Normalized console and screenshot hashes are retained.

| Metric | Before | After |
|---|---:|---:|
| Kernel interval, master clocks | 86,337,170 | 86,337,164 |
| Kernel interval, CPU cycles | 12,831,860 | 12,831,860 |
| Exact interval Dhrystones/s (21.477272 MHz) | 746.281306 | 746.281358 |
| Displayed nominal 60 Hz ticks | 242 | 242 |
| Displayed integer Dhrystones/s | 743 | 743 |

Kernel time changes by -6 master clocks (-0.000007%). The exact interval starts immediately after the first clock() return and stops at entry to the second clock(); it includes timer-result stores, loop setup/exit, calls and interrupts, but excludes initial/final console reporting. The displayed rate is separately retained; frame ticks and integer rounding can conceal small differences.

## Boundaries, startup and interpretation

Finite samples measure main entry through return. Minimal measures 1,000 empty idle-loop iterations; prompt ends at its first completed print/flush; calculator measures its first printf through return from the result printf for `(12 + 3) * 4 / 2`. These three are checkpoints rather than program completion. Console measurements include their actual VBlank/flush behavior and interrupt/refresh phase; they are not pure compiler throughput.

| Sample / mode | Reset-entry-to-main change, master clocks | Linked code byte change |
|---|---:|---:|
| minimal / original | +36 | +15 |
| minimal / runtime | +36 | +15 |
| prompt / original | +36 | +15 |
| prompt / runtime | +36 | +15 |
| calc / original | +36 | +15 |
| calc / runtime | +36 | +15 |
| insertion_sort / original | +36 | +15 |
| insertion_sort / runtime | +36 | +15 |
| string_processing / original | +36 | +15 |
| string_processing / runtime | +36 | +15 |
| integer_operations / original | +36 | +15 |
| integer_operations / runtime | +36 | +15 |
| function_calls / original | +36 | +15 |
| function_calls / runtime | +36 | +15 |
| structures_and_tables / original | +36 | +15 |
| structures_and_tables / runtime | +36 | +15 |

The new empty LORAM_DATA check adds 36 master clocks before main in these images, with 15 additional linked startup bytes and no application code growth. LORAM_DATA is empty here; this does not measure the per-byte startup copy cost of newly initialized __loram objects. A tiny change in the phase of refresh, NMI delivery or a console polling loop can change elapsed clocks even with unchanged application instructions and call counts. Treat console checkpoint deltas separately from matched kernel work.

The split string-processing +40-clock delta is a startup-phase effect: an isolated old-layout ROM adds exactly 36 clocks outside the measured kernel (NOP plus a JML entry trampoline, retaining its original return frame). Its old RAM/stack layout and all kernel instructions are unchanged. All three fresh-process phase-control measurements reproduce the candidate exactly: 15,444 master clocks, 2,297 CPU cycles, and the same main-entry timestamp. This is consistent with a WRAM refresh boundary moving into the timed interval, rather than slower kernel execution. The control ROM, assertions and logs are retained under build/wram-performance/phase-control-confirmed/.

Dhrystone startup is measured from ram_cleared to main because an asynchronous ROM load can pass reset_entry before Lua hooks are installed. Its failed early-boot attempt is retained, and only its six measurements were rerun; all 96 successful sample runs were retained.

## Evidence

Preparation exported the baseline revision and built its own compiler and runtime. All sources, compiler/runtime hashes, exact generated measurement harnesses, assembly, objects, allocation manifests, maps, ROMs, execution logs, profiles and Dhrystone screenshots are under `build/wram-performance/`. `comparison.json` embeds all final measurements and checks repeated clocks/cycles, workload counts, source/compiler/ROM/harness identities and application instruction equivalence. Immutable execution harness snapshots are keyed by SHA-256 under execution-harnesses/. No compiler or runtime implementation was changed for this benchmark.
