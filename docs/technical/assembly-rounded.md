# Assembly decimal rounding trial, 2026-11-07

Rounding the calculator's decimal output in assembly saved 5,076 master clocks and 442 code bytes. The main compiler later adopted the routine with its newer console formatter and HiROM allocator. The figures below compare the original rounding trial with the earlier assembly rendering build. [Integration report](bank-cost-integration.md)

## Measured results

Matched FastROM samples retain identical C input hashes, compiler, arithmetic
runtime and ABI. Original/separate-TU forms each have two matching checked runs;
the runtime drivers and kernels are separate translation units without LTO.

| Calculator measurement | C rounded | Assembly rounded |
|---|---:|---:|
| Master clocks, both forms | 598980 | 593904 |
| STARTUP+CODE bytes | 13545 | 13103 |
| Complete formatting call, inclusive clocks | 28142 | 23066 |
| Rounded inclusive/exclusive clocks | 6944 | 1868 |
| Rounded calls | 1 | 1 |
| Instructions inside rounded | 259 | 82 |
| Monitored decimal-array byte reads | 4 | 2 |
| Rounded body bytes | 742 | 300 |

The calculator saves 5076 clocks (0.85%) and 442 code bytes. Its rounded call
is 73.10% faster. Both versions copy the same two numeric input digits and
pad the output to six characters. The C compiler loads near bytes with word
loads and masks the high byte; the assembly uses byte loads. The monitored
array read reduction does not remove intended rounding or copying work.
Other exclusive profiler rows can shift slightly with refresh/placement; the
table reports the directly measured complete workloads and call spans.

Direct fixtures isolate rounding decisions. The following CPU-cycle counts
agree between NTSC and PAL, with identical opaque arguments and output.
Numeric input arrays are least-significant digit first.

| Input / keep | Result | C cycles | Assembly cycles |
|---|---|---:|---:|
| [0,5,2] / 1, exact even half | 2 | 776 | 297 |
| [0,5,3] / 1, exact odd half | 4 | 928 | 334 |
| [1,5,2] / 1, nonzero sticky tail | 3 | 851 | 290 |
| [0,5,9] / 1, carry overflow | 1, exponent incremented | 1012 | 361 |
| [9,9,9,9,9,9] / 9, padding | 999999000 | 1653 | 376 |

The optimized decision reads the first discarded digit before scanning a
sticky tail. Only an exact five needs a sticky scan, which stops at the first
nonzero byte. Retained parity is needed only for an otherwise exact half.
These are ordinary non-volatile shared decimal digits. Reverse copying and
zero padding use separate indexed loops, followed by the original carry rule.

Strings and structures retain identical ROM hashes, clocks and code sizes in
both forms: separate-TU strings 15404 clocks / 588 bytes, structures 15690 / 1938.
Calculator ROM files remain 32768 bytes; no static RAM is added. The historical
586538-clock pre-bank calculator gap is now 1.26%.

## ABI and retained C implementation

`runtime/ieee32/rounded.s` exports `_decimal__rounded`. Signed keep is in X,
the near output pointer in A, and near length/exponent pointers at 3/5,S.
Return is void through RTS; A/X/flags and $E0-$FF are call-clobbered. Native
A16/X16, D=0, DBR=$7E, Y/D/DBR, argument homes and stack balance are preserved.
This is a leaf routine using $E0-$EF and a two-byte Y save; the C routine used
a 16-byte local frame in addition to its Y save.

The original C body is unchanged behind `ZICC_C_ROUNDED_REFERENCE` and is
selected automatically for host builds. Existing match/render reference
fixtures also select C rounded, while their assembly versions use the current
decimal archive. The existing binary32 fixture therefore compares complete
formatting through C rounded versus assembly rounded as part of full checks.

`runtime/ieee32/decimal-state.s` assembles the generated decimal C module and
exports only the three existing private state symbols required by rounded.s.
Their C storage, names, order and sizes stay unchanged. This avoids changing
the C variables' linkage or exposing them in public C headers. The normal
decimal archive and standalone calculator builder use that assembly wrapper;
the archive gains decimal-rounded.o. Existing archive ordering is unchanged.

The assembly caches n before the first exponent store and preserves C's order
of writes through output, length and exponent pointers. Carry increments read
the current exponent after earlier writes, so supported pointer aliases retain
the C result. Negative n behaves as C for nonnegative copy indices; negative
keep emits zero, and zero keep retains the exact-half-to-even-zero rule.
Tests exclude overflowing signed C intermediate expressions and require valid
memory for every access. Decimal input lengths through the 200-byte array and
defined positive keeps through 32767 are covered.

## Verification and evidence

`tests/check-assembly-rounded.py` runs 3799 cases per implementation and region:
all three-digit decimal combinations with keeps 0/1/2; all 256 input byte values
for conversion and classification; even/odd ties; early/late/zero sticky tails;
all-nines carries; reverse copying; padding; negative/zero keeps and counts;
200-digit arrays; signed arithmetic boundaries; seeded random arrays; and
overlapping digit/state/result pointers. Hooks verify every argument and call,
ordered physical input reads, ordered byte writes, output/guards, final shared
state and fields, preserved registers, CPU modes and stack balance. Optimized
read sequences are checked separately from the reference's widened/full scans.
Long padding cases require actual IRQ and nested NMI while rounded is live,
checking every register, status and arithmetic scratch across interrupt returns.

Both implementations pass all 3799 cases in NTSC and PAL. The test is registered
in the complete compiler suite. The existing render suite adds 1986 direct
render cases and 270 complete binary32 formatting cases per region/version,
including signed zero, subnormals, normal boundaries, infinities and NaNs.
Host decimal checks also compare with MSVC. `make all smoke` and the standalone
calculator builder pass. Full `make check` passes 27/27 logical suites, 76/76
jobs, all 200873 arithmetic cases and 50 batches with the hardware-thread
default of 20 workers, in 571.27 seconds. The retained summary is
`build/check/20261107T071147.429495Z/summary.json`. Compiler SHA-256 remains
`ef6e4166a19fe5a9803468b5b02c3006371cb00c118ad000cc50fc32251b677a`.
No runtime or registered-test edits were made during the complete run.

Retained evidence:

- `build/assembly-rounded/baseline-inputs/`: saved baseline inputs and hashes.
- `build/bank-costs/rounded-before/` and `rounded-after/`: generated code,
  ROMs, hashes, execution assertions and two checked profiles per sample/form.
  The before variant explicitly links the frozen committed decimal archive.
- `build/assembly-rounded/trace-before/` and `trace-after/`: executed PC counts.
- `build/assembly-rounded/reads-before/` and `reads-after/`: physical decimal
  array reads during the actual calculator rounded call, with checked clocks.
- `build/assembly-rounded/comparison.json`: checked measurements and fixture
  hashes from the profiler.
- `build/assembly-rounded-check/`: C/assembly ROMs, assembly, Lua checks,
  four timing arrays, coverage logs and input/runtime hashes.
- `build/assembly-rounded/frame-build/`: standalone calculator build.
- `build/assembly-rounded/verification.json`: checked full-run summary.

The first assembly probe found a missing A8 assembler declaration on the
all-nines path. It was corrected before accepted measurements and verification;
the rejected ROM and failure log remain in the trial folder. One frozen
baseline worker stalled after profiler READY; its identical ROM passed an
isolated rerun, with the timeout and retry logs retained.
