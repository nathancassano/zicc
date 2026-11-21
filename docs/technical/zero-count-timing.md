# Zero-count timing investigation

Both runs took the same 27 instructions to return from a loop with a count of zero. One took 592 master clocks and the other took 632. In the longer run, a memory refresh paused the subtraction that checked the count. Repeating the same ROM reproduced the pause.

## Original ROMs

Replayed the retained opaque driver/kernel ROMs with their existing input,
write-count, final-index, result and stack assertions. Instruction callbacks
recorded the entry state and every instruction up to the caller return boundary.

| Observation | Baseline | Candidate |
|---|---:|---:|
| Entry master clock | 4941122 | 4940594 |
| Entry horizontal clock | 738 | 210 |
| Entry scanline | 216 | 216 |
| Executed kernel instructions | 27 | 27 |
| Complete call master clocks | 592 | 632 |
| Guard `SBC a:$0003,y` clocks | 40 | 80 |

The instruction opcode sequences are identical. Initial A/X/Y, SP, P, D, DBR
and interrupt state also match. Code addresses differ, and the skipped region
has shrunk, changing the jump destination without changing its cost.

All instruction intervals match except the guard subtraction. It begins 312
clocks after entry: horizontal clock 1050 in the baseline, versus 522 in the
candidate. The candidate entry state explicitly reports
`memoryManager.dramRefreshPosition = 538` and `nextEventClock = 538`. The
subtraction crosses that refresh and gains exactly 40 clocks; the baseline
call starts after refresh and finishes before the next one.

The emulator's [DRAM refresh event implementation](https://github.com/SourMesen/Mesen2/blob/master/Core/SNES/SnesMemoryManager.cpp#L221-L230)
advances the master clock by 40. The installed executable's identity is retained
in the investigation manifest; the diagnosis is established by its actual traces
and matched-phase executions, rather than assuming its binary matches upstream.

## Matched entry phases

Extracted each retained C-generated `runtime_row` function into its own object
without changing its instructions. Linked it at the same FastROM address
`$80:9000` against an identical assembly driver, startup, WRAM workspace and
linker configuration. All linked ROM bytes before the kernel are identical.
The functions remain separate from the driver, with no LTO or constant folding.

The driver makes 1024 calls with zero in A, the matrix pointer in X, and 73 on
the stack. Execution assertions check all arguments, caller Y, the returned
index, stack restoration, zero matrix writes, final contents and completion.
Both ROMs were executed three times, retaining every sample.

- All 1024 paired calls have identical entry clocks, horizontal phases,
  scanlines, CPU cycle counts and elapsed master clocks.
- The run covers 331 distinct horizontal entry phases, spanning clocks 0-1360.
- Each version has 567 calls at 592 master clocks and 457 at 632.
- Every call takes 92 CPU cycles in the emulator's CPU counter; refresh adds
  master-clock time without adding executed instructions or CPU cycles.

Thus neither version has a zero-count kernel advantage at a matched phase.
The original candidate reaches the call 528 master clocks earlier, which moves
its guard across the refresh window. The raw whole-program samples remain valid;
their 40-clock difference must not be described as added loop dispatch overhead.

## Evidence

Inputs were the frozen before/after loop
outputs under `build/loop-overhead-evidence/`. Evidence under
`build/zero-count-confirmed/` includes `results.json`, original instruction
traces, generated drivers/kernels, objects, ROMs, maps, debug labels, three raw
controlled logs per version, and tool/runtime/emulator hashes.

No compiler or runtime code changed during this investigation. The existing
27/27-suite, 76/76-job full check remains the compiler verification record;
the new investigation itself passed all trace and phase-matching assertions.
