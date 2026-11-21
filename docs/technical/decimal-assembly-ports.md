# Decimal runtime assembly ports, 2026-11-07

The runtime now uses assembly for all twelve decimal routines covered here. That includes the nine described below and the three earlier changes to matching, rendering, and rounding.

The bank-cost investigation developed and verified these routines separately.
The main compiler integrates them with its newer
precision-aware formatter and HiROM allocator; see
[the integration report](bank-cost-integration.md). The measurements below
describe the frozen experimental branch before that integration. Original C bodies
remain available with individual `ZICC_C_*_REFERENCE` switches;
`ZICC_ALL_C_REFERENCE` selects the complete C implementation for differential
tests. Existing match/render/rounded reference fixtures now use that switch.

All nine ports are complete. Together with match/render/rounded, all twelve
production function bodies now use assembly. The C-generated object contains
only the unchanged 252-byte state; complete C bodies remain as references.

## hexval

The baseline already used assembly rounding. `runtime/ieee32/hexval.s` retains the word input in X,
signed word result in A, and native A16/X16/D=0/DBR=$7E contract. Y/D/DBR and
caller stack are preserved; A/X/flags are call-clobbered. It is a leaf routine
without scratch memory or a stack frame. It uses unsigned range tests and ASCII
case folding, preserving the existing target runtime's complete word mapping.

The body shrinks from 101 to 32 bytes. Calculator code shrinks from 13103 to
13034 bytes, while its checked clocks stay 593904: this workload never calls
hexval. Strings and structures retain their ROM hashes, clocks and code sizes.
All six sample forms have two matching FastROM measurements with identical
input hashes and execution assertions. Separate-TU drivers have no LTO.

`tests/decimal_assembly_fixture.c` is a separately compiled driver with opaque
inputs supplied at execution time. `tests/check-decimal-assembly.py` checks all
65536 word inputs against both the target C reference and independent ASCII
classification, in NTSC and PAL. Entry hooks require the actual input and every
call; return hooks check results, saved registers, stack and CPU modes. The
fixture stores and verifies every result, preventing caller folding/removal.

NTSC average CPU cycles per class, including the C helper's tolower calls:

| Class | Cases | C | Assembly |
|---|---:|---:|---:|
| Digits | 10 | 75.6 | 19 |
| Uppercase hex letters | 6 | 154.333 | 38 |
| Lowercase hex letters | 6 | 152.333 | 38 |
| Other word values | 65514 | 119.965 | 37 |

All inputs pass in both regions. Full `make check` passes 27/27 suites, 76/76
jobs and all 200873 arithmetic cases with 20 hardware-default workers in
650.93s: `build/check/20261107T073712.854968Z/summary.json`.
Raw evidence: `build/decimal-assembly/hexval/` (frozen inputs and logs),
`build/decimal-assembly/check/` (ROMs, generated assembly, Lua, input/runtime
hashes and per-class timings), and `build/bank-costs/lib-hexval-before/` /
`lib-hexval-after/` (matched checked samples).

## dec_copy

The baseline already used assembly hexadecimal digit decoding. This is a NUL-terminated far-source to near-WRAM string
copy, including the terminator, used for inf/nan text. No length is supplied;
it uses a byte loop, not MVN. The entry remains destination X and padded far
source at 3/5,S, with void return and preserved Y/D/DBR/native modes/stack.
The source cursor is private DP $E0-$E3. The body shrinks 39 -> 36 bytes by
reusing the zero byte already fetched at termination.

Measured taken CPU cycles against the frozen committed function:

| Non-NUL bytes | Before | After |
|---:|---:|---:|
| 0 | 59 | 56 |
| 3 | 119 | 116 |
| 16 | 379 | 376 |
| 256 | 5179 | 5176 |
| 40000 | 800059 | 800056 |

Both regions pass 291 cases per implementation: all byte values, empty/short/
long strings, ROM/WRAM sources, bank crossings, 24-bit wrap, same-buffer and
forward-safe overlap, exact terminators and output guards. The shared checker
now supports explicit `--before` archives and separate `--output` evidence
directories, keeping incremental cycle comparisons independent of the full-C
correctness reference. Source, ROM and compiler/runtime hashes are retained.

Calculator clocks stay 593904 and code shrinks 13034 -> 13031 bytes. Other
samples keep their clocks and ROM hashes; two checked runs cover each form.
Full `make check`: 27/27 suites, 76/76 jobs, all 200873 arithmetic cases,
20 hardware-default workers, 651.13s. Summary:
`build/check/20261107T075345.667913Z/summary.json`. Direct before/after evidence:
`build/decimal-assembly/dec-copy/measure/`; matched sample evidence:
`build/bank-costs/lib-dec-copy-before/` and `lib-dec-copy-after/`.

## exponent

The baseline already used assembly copying for special decimal values. `runtime/ieee32/exponent.s` keeps near output X, signed
exponent A, upper word at 3,S, near return A, and the preserved native ABI.
It emits e/E, sign, and at least two decimal digits. A bounded byte stack
reverses the digits; the existing unsigned division helper provides quotient
and remainder together, replacing C's separate modulo/divide calls.
The body shrinks 328 -> 107 bytes, without static RAM growth.

Taken CPU cycles against the frozen committed function, lowercase output:

| Exponent | Before | After |
|---:|---:|---:|
| 0 | 1019 | 258 |
| 1 | 1019 | 258 |
| -1 | 1037 | 265 |
| 99 | 1408 | 372 |
| 100 | 1998 | 514 |
| 32767 | 3178 | 798 |
| -32767 | 3196 | 805 |

2034 fixtures pass per implementation and region, covering signs, zero,
two-digit padding, decimal digit boundaries, uppercase/nonzero upper flags,
signed limits with defined negation, and seeded random exponents. Output bounds,
return pointers, actual arguments, preserved registers, modes and stacks are
checked. INT_MIN negation is undefined in the C reference and is not a promised
extra behavior. The existing render and complete-format fixtures exercise this
new helper as well. Calculator timing stays 593904, code 13031 -> 12810 bytes;
the calculator's result is fixed notation, so the direct fixture is the relevant
speed measurement. Other samples retain timings and ROM hashes.

Before/after evidence: `build/decimal-assembly/exponent/measure/` and
`build/bank-costs/lib-exponent-before/` / `lib-exponent-after/`. Two unrelated
benchmark workers stalled after READY; unchanged ROMs passed isolated reruns,
with failed and retry logs retained. Full `make check` passes 27/27 suites,
76/76 jobs and all 200873 arithmetic cases with 20 hardware-default workers
in 679.26s: `build/check/20261107T080811.645370Z/summary.json`.

## dec_format

The baseline already used assembly scientific exponent output. The public wrapper receives its U32 argument at 3/5,S,
not in A/X, and returns the near static output pointer in A. The new 18-byte
wrapper preserves that entry and the Y/D/DBR/native-mode/stack contract,
replacing the 25-byte C body. The private output symbol is exported from the
existing state module without changing its address, storage or size.

Before/after taken CPU cycles include the unchanged raw-format callee:

| Binary32 input | Before | After |
|---|---:|---:|
| zero | 1740 | 1723 |
| 1 | 3500 | 3483 |
| 16777216 | 6620 | 6603 |
| infinity | 704 | 687 |
| NaN | 684 | 667 |

278 fixtures pass in both regions, using the committed archive for incremental
measurements and complete C for differential full checks. They cover signed
zero, subnormals, normal boundaries, rounding thresholds, infinities, NaNs and
seeded random bits. An assembly caller poisons A/X while supplying the stack
argument, preventing accidental reliance on register copies left by C callers.
The first draft failed the real printf caller despite passing the original C
fixture; the ABI was corrected and both tests rerun before acceptance. Rejected
ROM and logs are retained under `build/decimal-assembly/dec-format/`.

Calculator clocks improve 593904 -> 593794; code 12810 -> 12803 bytes. Other
samples retain timings and ROM hashes. Full `make check` passes 27/27 suites,
76/76 jobs, all 200873 arithmetic cases with 20 hardware-default workers in
693.36s: `build/check/20261107T082648.607179Z/summary.json`. Direct cycle data:
`build/decimal-assembly/dec-format/measure/`. Matched checked samples:
`build/bank-costs/lib-dec-format-before/` and `lib-dec-format-after/`.

## dec_format_raw

The baseline already used an assembly decimal formatting wrapper. The assembly body preserves the near output pointer in X,
U32 stack argument at 3/5,S, and returned length in A. The complete C body
remains available as a reference. The body shrinks 596 -> 240 bytes with no
static RAM growth. Fixed general-format options avoid redundant option handling
and the initial exponent calculation that rounding replaces.

Taken CPU cycles against the frozen committed function, including its callees:

| Binary32 input | Before | After |
|---|---:|---:|
| zero | 1677 | 1128 |
| 1 | 3437 | 2901 |
| 16777216 | 6557 | 6021 |
| infinity | 641 | 280 |
| NaN | 621 | 270 |

278 direct fixtures pass per implementation in NTSC and PAL. An assembly caller
supplies the stack argument and poisons the unrelated A register. Tests verify
output, lengths, bounds, preserved registers, modes and stack balance. The
converter caller also has a poisoned-X fixture to check its stack/A argument ABI.
Calculator clocks improve 593794 -> 590182; code 12803 -> 12447 bytes.
Strings and structures retain their timings and ROM hashes. Direct evidence is
in `build/decimal-assembly/dec-format-raw/measure/`; matched checked samples are
in `build/bank-costs/lib-dec-format-raw-before/` and `lib-dec-format-raw-after/`.
The standalone calculator builder and smoke checks also pass.

Full `make check` passes 27/27 suites, 76/76 jobs and all 200873 arithmetic
cases with 20 hardware-default workers in 716.37s:
`build/check/20261107T084214.095628Z/summary.json`.

## __ieee_decimal

The baseline already used assembly raw decimal formatting. The assembly implementation retains the U32 mantissa on
the stack at 3/5,S, signed binary exponent in A, and existing shared decimal
state. Its body shrinks 817 -> 357 bytes without static RAM growth. It obtains
quotient/remainder together during digit extraction and carries the decimal
multiply through the digit loops without generic C arithmetic or addressing.
The original C body remains available through the reference switch.

Taken CPU cycles against the committed implementation:

| Mantissa / binary exponent | Before | After |
|---|---:|---:|
| 0 / -150 | 114 | 98 |
| 1 / 0 | 595 | 325 |
| 0x800000 / -149 | 936326 | 204011 |
| 0xffffff / 104 | 431347 | 64757 |
| 0xffffffff / -150 | 1563541 | 341207 |

246 direct fixtures pass per implementation in NTSC/PAL. An independent
arbitrary-precision model checks every decimal digit, count and scale, including
the untouched tail of the 200-byte array. Cases cover zero, cancellation,
word/long boundaries, extreme exponents within the state capacity and seeded
random values. The assembly caller poisons X and supplies the stack/A arguments;
registers, modes, stack balance and unrelated output storage are checked.

Calculator clocks improve 590182 -> 584606; code 12447 -> 11987 bytes.
Strings/structures retain timings and ROM hashes. The standalone calculator
builder and smoke check pass. Direct evidence:
`build/decimal-assembly/ieee-decimal/measure/`; repeated checked samples:
`build/bank-costs/lib-ieee-decimal-before/` and `lib-ieee-decimal-after/`.

Full `make check` passes 27/27 suites, 76/76 jobs and all 200873 arithmetic
cases with 20 hardware-default workers in 751.47s:
`build/check/20261107T085925.529006Z/summary.json`.

## __ieee_decimal_compare

The baseline already used assembly binary-to-decimal conversion. The assembly comparator preserves the three stack arguments
(two padded far pointers and signed long exponent), signed word result, shared
decimal state and register/mode/stack contract. The body shrinks 436 -> 254
bytes with no static RAM growth. It compares complete bank/offset pointers,
skips decimal points and pads missing input/reference digits with zero.
The C implementation remains available for reference builds.

Taken CPU cycles against the committed implementation:

| Case | Before | After |
|---|---:|---:|
| exponent 0 versus state exponent 1 | 300 | 139 |
| empty input versus one zero digit, equal exponents | 487 | 281 |
| input "0" versus one zero digit | 666 | 307 |
| 200 nines equal to 200 reference nines | 86037 | 25580 |

978 direct fixtures pass per implementation in NTSC/PAL against an independent
comparison model. They include signed long exponent boundaries, zero/negative
counts, decimal points, all 256 input byte values, 200-digit states, ROM/WRAM
sources and bank-crossing pointers. Shared state and output storage are checked
for unintended writes, along with actual stack inputs and preserved registers.

Calculator clocks stay 584606; code 11987 -> 11805 bytes. The calculator's
sample inputs use the integer parse shortcut, so the direct fixtures provide
the comparison-helper speed evidence. Strings/structures timings and ROM hashes
are unchanged. Standalone calculator and smoke builds pass. Direct evidence:
`build/decimal-assembly/ieee-decimal-compare/measure/`; repeated checked samples:
`build/bank-costs/lib-ieee-decimal-compare-before/` and
`lib-ieee-decimal-compare-after/`.

Full `make check` passes 27/27 suites, 76/76 jobs and all 200873 arithmetic
cases with 20 hardware-default workers in 728.07s:
`build/check/20261107T091223.050691Z/summary.json`.

## hexparse

The baseline already used assembly exact decimal comparisons. The assembly parser preserves the padded far input on the
stack at 3/5,S, near endptr in A, sign word at 7,S and U32 result in A/X.
It preserves the original endptr padding, exponent rollback, sticky/tie-to-even
rounding, signed-zero, range and errno behavior. The C body remains available
as a reference. The body shrinks 2264 -> 999 bytes without static RAM growth.
ASCII classification and fixed-width operations are direct assembly; the now
unused 32-byte hexval member also drops out of the calculator's linked runtime.

Taken CPU cycles against the committed implementation, sign zero / nonnull endptr:

| Input | Before | After |
|---|---:|---:|
| 0x | 624 | 310 |
| 0x0 | 927 | 407 |
| 0x1.8p2tail | 5072 | 1704 |
| 0x123456789 | 8622 | 2696 |
| 0x1p-149 | 5378 | 1423 |
| 0x1.ffffffp127 | 11196 | 3009 |

1734 direct fixtures pass per implementation in NTSC/PAL. Native MSVC strtof
independently supplies result bits; endptr offsets and errno are compared to
the retained target C implementation. Cases include exact binary32 encodings,
seeded long significands, sticky tails, half-way/subnormal/overflow boundaries,
malformed exponent rollback, both sign flags, high bytes, null endptr and
ROM/WRAM sources crossing banks. Actual stack/register arguments, return words,
far-pointer padding, shared state, output storage, preserved registers, modes
and stack balance are checked. Source, compiler, runtime and fixture hashes,
ROMs, generated assembly, Lua assertions and cycle records are retained.

Calculator clocks stay 584606; linked code 11805 -> 10508 bytes. Its sample
inputs do not use hexadecimal parsing, so the direct fixtures provide the
speed evidence. Strings/structures retain timings and ROM hashes. Standalone
calculator and smoke builds pass. Direct evidence:
`build/decimal-assembly/hexparse/measure/`; repeated checked samples:
`build/bank-costs/lib-hexparse-before/` and `lib-hexparse-after/`.

The shared parser fixture also contains the upcoming 1394-case general-parser
corpus. Its long runs exposed the emulator's wrapping timing counters; elapsed
CPU/master clocks now use unsigned modular subtraction. The rejected measurement
log is retained under `build/decimal-assembly/plans/parser-trial/`.

Full `make check` passes 27/27 suites, 76/76 jobs and all 200873 arithmetic
cases with 20 hardware-default workers in 823.03s:
`build/check/20261107T092612.625525Z/summary.json`.

## __ieee_parse

The baseline already used assembly hexadecimal floating-point parsing. The assembly implementation retains the padded far text
at 3/5,S, near endptr in A, U32 result in A/X, and existing register/mode/stack
contract. The 3190-byte C body becomes 1735 bytes of assembly, retaining 14
bytes of strings and adding no static RAM. The original C implementation remains
available through its reference switch. Direct assembly handles lexical work,
integer accumulation/normalization and search argument setup; the exact midpoint
algorithm and previously verified decimal helpers are preserved.

Taken CPU cycles against the committed implementation, nonnull endptr:

| Input | Before | After |
|---|---:|---:|
| empty input | 1041 | 713 |
| NaN | 1215 | 817 |
| -INFINITY | 1471 | 1041 |
| 1 | 5281 | 1860 |
| 16777216 | 6760 | 3108 |
| 0.125 | 543491 | 527107 |

All 1394 cases pass per implementation in NTSC/PAL. They include low/high
mantissa edges of every finite binary exponent, signed zeros, exact midpoint
ties and sticky tails, subnormal/normal/overflow boundaries, integer shortcuts,
long significands, whitespace, infinity, NaN payload acceptance/rollback,
hexadecimal delegation, invalid decimal exponent rollback, high bytes, null
endptr, ROM/WRAM sources and bank crossings. MSVC strtof independently supplies
result bits; endptr offsets and errno match retained target C. Actual arguments,
return words, preserved registers, CPU modes, stack balance, pointer padding
and unrelated output storage are checked. There are 0 cycle regressions across
these matched NTSC fixtures.

Calculator clocks improve 584606 -> 492674; linked code 10508 -> 9053 bytes.
Strings/structures timings and ROM hashes are unchanged. Smoke and standalone
calculator builds pass. Direct evidence: `build/decimal-assembly/ieee-parse/measure/`;
repeated checked samples: `build/bank-costs/lib-ieee-parse-before/` and
`lib-ieee-parse-after/`.

All twelve production function bodies in decimal.c are now assembly. Its
generated object contains zero CODE/RODATA bytes and the unchanged 252-byte BSS
layout; complete C bodies remain for differential and host reference checks.
The compiler-suite deadline is increased to accommodate the full C parser corpus;
coverage, assertions and hardware-default verification concurrency are unchanged.

Across the latest four ports, calculator clocks improve 590182 -> 492674
(-16.52%) and linked code 12447 -> 9053 bytes (-3394 bytes, -27.27%). Across
all nine newly converted functions, the starting point was 593904 clocks and
13103 code bytes: total savings are 101230 clocks (-17.04%) and 4050 bytes
(-30.91%). These are matched checked FastROM workloads, with two agreeing
measurements per sample form; main-checkout adoption remains separate.

Full `make check` passes 27/27 suites, 76/76 jobs and all 200873 arithmetic
cases with 20 hardware-default workers in 1897.70s:
`build/check/20261107T094802.397495Z/summary.json`.
