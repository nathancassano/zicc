# Assembly decimal render trial, 2026-11-07

Writing the decimal digits into the output buffer in assembly saved the calculator 5,514 master clocks and 488 code bytes. The main compiler later adopted the routine with its newer console formatter and HiROM allocator. The figures below compare the original rendering trial with the earlier assembly matching build. [Integration report](bank-cost-integration.md)

## Results

Matched FastROM workloads use identical source hashes, inputs, compiler and
arithmetic runtime. Each original/separate-TU sample has two matching checked
runs. Runtime drivers/kernels are separate translation units without LTO;
execution assertions remain enabled. ROMs, assembly, source/compiler/runtime
hashes, profiles and instruction traces are retained.

| Calculator measurement | C render | Assembly render |
|---|---:|---:|
| Master clocks, both sample forms | 604494 | 598980 |
| STARTUP+CODE bytes | 14033 | 13545 |
| Complete dec_format call, inclusive clocks | 33656 | 28142 |
| Render inclusive clocks | 8670 | 3156 |
| Render exclusive clocks | 8552 | 3156 |
| Render calls | 1 | 1 |
| Instructions inside render | 343 | 141 |
| Far digit reads inside render | 6 | 6 |
| Render body bytes | 825 | 337 |

The calculator saves 5514 clocks (0.91%) and 488 code bytes. The render call is
63.60% faster, with the same six actual digit reads and output. Inline ASCII
folding removes its tolower call; direct output/digit cursors and indexed bounds
replace repeated pointer reconstruction and frame updates. This calculator
formats `30` through general formatting's fixed branch. The full formatted
number call still includes the unchanged conversion and rounding work.

Direct render fixtures measure the other branches independently. These are
CPU cycles for one opaque call, including the existing exponent helper when
used, and excluding display waiting. NTSC/PAL CPU-cycle counts agree in every
listed fixture.

| Input digits / e / spec / precision, alt=0 | Output | C cycles | Assembly cycles |
|---|---|---:|---:|
| 123400 / 1 / g / 6 | 12.34 | 1563 | 480 |
| 123400 / -6 / g / 6 | 1.234e-06 | 2401 | 1484 |
| 120030 / 1 / f / 6 | 12.003000 | 1846 | 427 |
| 120030 / 1 / E / 6 | 1.200300E+01 | 2437 | 1429 |

Strings and structures retain identical ROM hashes, clocks and code sizes in
both forms. Separate-TU strings remain 15404 clocks / 588 bytes, structures
15690 / 1938. Calculator ROM files remain 32768 bytes. There is no added static
RAM. The historical 586538-clock pre-bank calculator gap is now 2.12%.

## Entry contract and C reference

`runtime/ieee32/render.s` exports the same `_decimal__render` symbol. The near
output pointer is in X; the padded four-byte far digit pointer is at 3,S, then
signed word n/e/spec/precision/alt at 7/9/11/13/15,S. A returns the advanced near
output pointer through RTS. The function does not append a NUL. Entry/return
are native A16/X16, D=0 and DBR=$7E. Y, D, DBR and stack balance are preserved.
The assembly also leaves argument homes intact; the C reference uses those
homes for its mutable parameter copies, so this is an additional preservation,
not a requirement imposed on the reference.

Both digit cursors and output cursors are per invocation. The assembly uses
$E0-$F1 and a two-byte Y save. A/X/flags and $E0-$FF remain call-clobbered under
the existing ABI. Far reads carry across banks; output is the existing near
WRAM pointer. General formatting retains trimming, alternate form, threshold
selection and precision adjustment. Fixed/scientific output retains padding,
decimal points, uppercase handling, and the C behavior for zero/negative counts
and precisions where execution is defined.

Scientific output calls the existing C `_decimal__exponent` entry, with X=p,
A=e and upper on the stack. No private cursor state is needed after that call.
That helper remains unchanged at 328 bytes, including its two-digit minimum
exponent rendering. It is not exercised by the calculator's `30` output but is
covered by direct scientific fixtures and end-to-end binary32 formatting.

The original C render body remains unchanged behind
`ZICC_C_RENDER_REFERENCE`, and is selected automatically on host builds.
The target reference fixture selects it through a wrapper named decimal.c,
retaining its original symbol and entry ABI. The normal decimal archive gains
`decimal-render.o`; its established name and link order stay unchanged. The
standalone calculator builder also links the new object explicitly.

The comparison covers valid memory for each actual access and defined signed
arithmetic. In particular, fixed e=32766 and scientific precision=32767 loops
are tested; overflowing C counters/expressions are not additional promised
behaviors.

## Verification and retained evidence

`tests/check-assembly-render.py` runs 1986 direct cases per implementation and
region, plus 270 complete binary32 formatting calls. It checks:

- g/G/f/F/e/E, alternate forms, notation thresholds, trailing zeros, zero and
  negative counts/precisions, unknown specifiers, and all 256 digit-byte values.
- ROM/RAM digits, far bank crossings, output page crossings and high near
  addresses, overlapping input/output, intermediate lengths and signed limits.
- Every input argument, return pointer, output byte/write address, ordered digit
  read address, output guard, preserved register, CPU mode and caller stack.
- Live IRQ and nested NMI in long trimming, integer, fractional and scientific
  loops, with all registers, status and arithmetic scratch restored. Each case
  stops interrupt generation after the first completed IRQ/NMI pair.
- Signed zero, subnormals, normal boundaries, infinities, NaNs and 256 seeded
  random binary32 patterns. Independent expected strings use the exact binary32
  value and six-significant-digit formatting. Hooks require actual conversion
  calls and the expected finite-value render calls; no folded workload counts
  toward these results. Existing host decimal checks also compare with MSVC.

Both C and assembly pass all cases in NTSC and PAL. The test is registered in
the complete compiler suite. `make all smoke` and the standalone calculator
builder pass. Full `make check` passes 27/27 logical suites, 76/76 jobs, all
200873 arithmetic cases and 50 batches, with the hardware-thread default of
20 workers, in 535.30 seconds. The retained summary is
`build/check/20261107T063948.380774Z/summary.json`; the compiler suite includes
both the match and render differential checks. Compiler SHA-256 remains
`ef6e4166a19fe5a9803468b5b02c3006371cb00c118ad000cc50fc32251b677a`.
No runtime or registered-test edits were made during the complete run.

Evidence locations:

- `build/assembly-render/baseline-inputs/`: saved baseline runtime, compiler and
  SHA-256 manifest.
- `build/bank-costs/render-before/` and `render-after/`: six workload builds and
  two checked profiles each. The before variant explicitly links the frozen
  decimal archive, allowing replay without changing the candidate source.
- `build/assembly-render/trace-before/` and `trace-after/`: executed PC counts.
- `build/assembly-render/comparison.json`: checked summary from
  the profiler, including direct fixture measurements.
- `build/assembly-render-check/`: reference/candidate ROMs, generated assembly,
  retained Lua checks, four per-case timing arrays, logs and source/runtime hashes.
- `build/assembly-render/frame-build/`: standalone calculator build evidence.
- `build/assembly-render/verification.json`: checked coverage/timing summary.
