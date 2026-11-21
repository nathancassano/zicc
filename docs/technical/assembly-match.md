# Assembly decimal match trial, 2026-11-07

Matching decimal text in assembly saved the calculator 12,744 master clocks and 100 code bytes. The main compiler later adopted this version with its newer console formatter and HiROM allocator. The figures below come from the original trial against the compiler with reduced far-pointer and generic call overhead. [Integration report](bank-cost-integration.md)

## Results

FastROM runs use identical sources and inputs, two execution-checked repetitions
per sample/form, and separate driver/kernel translation units without LTO for
the runtime form. Compiler, arithmetic runtime, memory speed and public ABI are
unchanged.

| Measurement | C reference | Assembly candidate |
|---|---:|---:|
| Calculator clocks, original and separate-TU | 617238 | 604494 |
| Calculator STARTUP+CODE bytes | 14133 | 14033 |
| Match body bytes | 159 | 59 |
| Match calls in calculator | 8 | 8 |
| Match inclusive clocks | 17808 | 4984 |
| Instructions inside match | 632 | 184 |
| Far-byte reads inside match | 24 | 16 |
| Total calculator tolower calls | 12 | 4 |

The calculator saves 12744 clocks (2.06%) and 100 code bytes. The match inclusive
profile improves 72.01%; the whole-program saving includes small placement/timing
effects elsewhere and should not be inferred by subtracting one profiler row.
The eight calculator matches reject the first byte. These results describe that
actual workload, not a universal strtod speedup. Source case folding remains
executed in the assembly loop; it no longer calls tolower for these bytes.
Caching the tested word byte removes its redundant second read. The pointed-to
strings are ordinary non-volatile memory, as in the C reference.

Strings and structures, in both forms, retain identical ROM hashes, clocks and
code sizes. Separate-TU strings remain 15404 clocks / 588 bytes; structures
remain 15690 / 1938. Calculator ROM files remain 32768 bytes, with no added RAM.
Against the historical 586538-clock pre-bank calculator, the remaining gap is
3.06%.

## ABI and retained reference

`runtime/ieee32/match.s` exports the existing `_decimal__match` entry. Parameters
are padded four-byte far pointers at 3,S and 7,S on entry; the word result is
returned in A, with the same RTS convention. Entry/return are native A16/X16,
D=0, DBR=$7E. Y, D, DBR, argument homes and stack balance are preserved. A, X,
arithmetic flags and $E0-$E7 are call-clobbered. There are no nested calls or
static cursor variables. Only Y's two-byte save is added to the caller's stack.
Both pointers use full 24-bit long-indirect indexing, including bank carry and
24-bit address wrap. Only ASCII A..Z in the source is folded; word is unchanged.

The C function body remains intact in `runtime/ieee32/decimal.c`. Host builds
retain it automatically; defining `ZICC_C_MATCH_REFERENCE` selects it in target
builds. The defined C matching-count domain is 0..32767; incrementing a signed
int beyond that is not an additional promised behavior.

`build/decimal.o` is now an ar65 archive containing the C decimal body and
assembly match. ld65 recognizes archives independently of the filename suffix.
Place it after `io.o`, which imports the parser, as the normal calculator link
already does. Calculator/printf tests use that order, and the standalone
calculator trial builder assembles and links the new source explicitly.

## Verification and evidence

`tests/check-assembly-match.py`, also invoked by the complete compiler suite,
runs both implementations with the same opaque driver. Each version passes
530 cases in both NTSC and PAL: all 256 byte values and mismatches, mixed case,
uppercase words, empty words without a source read, early NUL, ROM/RAM pointers,
aliasing/overlap, bank crossings, 24-bit wrap, intermediate lengths and 32767.
Execution hooks check every call/result, exact source/word read counts, the
preserved ABI, unchanged arguments and scratch outside $E0-$E7. The longest
case requires a real IRQ and a nested NMI while match is live; all registers,
status, stack and arithmetic scratch are checked across both returns.
Interrupt generation stops after this pair to bound host instrumentation cost.
The initial repeated-interrupt probe timed out and is not counted as a pass.

Retained evidence:

- `build/assembly-match/baseline-inputs/`: saved baseline compiler and runtime inputs
  and SHA-256 manifest.
- `build/bank-costs/match-before/` and `match-after/`: generated assembly, ROMs,
  source/ROM hashes, execution assertions and two matched profiles per workload.
- `build/assembly-match/trace-before/` and `trace-after/`: executed PC counts.
- `build/assembly-match/comparison.json`: checked sample and profile summary,
  produced by the profiler.
- `build/assembly-match-check/`: reference/candidate ROMs, four timing arrays,
  logs, coverage and hashes.
- `build/assembly-match/frame-build/`: separately verifies the standalone
  calculator builder's new link input.

The baseline replay explicitly linked the frozen committed decimal object.
The frozen replay reproduces all initial ROM hashes and measurements. One
strings worker stalled after the profiler READY checkpoint; its unchanged ROM
passed an isolated rerun. Both logs are retained as
`baseline-replay-timeout.log` and `baseline-replay-retry.log` in the trial folder.

`make all smoke` and the standalone calculator builder pass. Complete
`make check` passes 27/27 logical suites and 76/76 jobs with the hardware-thread
default of 20 workers, preserving all 200873 arithmetic cases and 50 batches.
It completed in 418.32 seconds. The retained summary is
`build/check/20261107T060406.715755Z/summary.json`; the compiler suite includes
the four new match runs. Compiler SHA-256 remains
`ef6e4166a19fe5a9803468b5b02c3006371cb00c118ad000cc50fc32251b677a`.
No runtime or registered-test edits were made during this complete run.
