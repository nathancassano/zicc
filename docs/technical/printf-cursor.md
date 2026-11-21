# Printf cursor trial, 2026-11-07

`printf` reads a format string one character at a time. Remembering its place cut the number of cursor-word stores from 32 to 8 in the calculator test. The whole program saved 3,294 master clocks.

The trial used the baseline with faster indexed reads from other banks. Only the assembly console's handling of the format cursor changed. The main compiler later adopted it with the newer console formatter and HiROM allocator. [Integration report](bank-cost-integration.md)

## Results against the committed candidate

All calculator measurements use FastROM and the same checked source/input.
Original and separate-TU forms each have two identical repeated measurements.

| Metric | Indexed far-byte baseline | Cursor trial | Difference |
|---|---:|---:|---:|
| Whole calculator master clocks | 633304 | 630010 | -3294 (-0.52%) |
| printf exclusive master clocks, two calls | 12770 | 8818 | -3952 (-30.95%) |
| printf executed instructions | 481 | 333 | -148 |
| Executed format-byte reads | 16 | 16 | unchanged |
| Executed cursor-word stores | 32 | 8 | -24 |
| printf code bytes, CALC console | 196 | 168 | -28 |
| Whole calculator STARTUP+CODE bytes | 14773 | 14745 | -28 |

The prompt and result use the same calls and output text. Decimal formatting
calls remain intact. Console VBlank waiting increases by 664 clocks, absorbing
some useful-work savings. Refresh shifts account for small changes in other
exclusive profile rows. The historical pre-bank calculator was 586538 clocks;
this trial is still 7.41% above it, versus 7.97% for the committed candidate.

Strings and structures in both source forms retain identical ROM hashes, clocks,
call counts and hardware operation counts. Their builds do not link the console.
No ROM file changes size: these images remain 32768 bytes.

## Finite printf cost without display waiting

The profiler compiles the same C driver against the frozen
baseline console object and the trial object. The separately assembled printf
kernel receives opaque format pointers; there is no LTO or caller folding.
Hooks verify each actual input string, returned count, all 301 emitted characters,
Y/D/DBR and stack restoration. Each span starts at printf entry and ends after
its RTS, excluding caller argument setup. There is no fflush/VBlank wait.
Two independent process executions per build agree exactly.

| Format length | Master clocks before / after | CPU cycles before / after | Master-clock saving |
|---|---:|---:|---:|
| empty | 1020 / 930 | 147 / 132 | 90 (8.82%) |
| one character | 2088 / 1740 | 306 / 252 | 348 (16.67%) |
| 300 characters | 318740 / 238890 | 47847 / 36132 | 79850 (25.05%) |

For these non-crossing formats, CPU-cycle measurements reconcile to 39 cycles
saved per fetched format
byte, offset by 24 additional fixed cycles per printf invocation for cursor
ownership. The terminating NUL is also fetched: savings are respectively
39*1-24=15, 39*2-24=54, and 39*301-24=11715 cycles. These figures retain
the identical console_putc work inside the spans. Master clocks additionally
include refresh, which explains their different percentage from CPU cycles.
The driver source and generated instructions are identical across the builds;
object debug paths differ. Commands/inputs and raw measurements are retained.

## Cursor ownership and implementation

Previously, every `format_next` copied two pointer words from this invocation's
stack into `console_format_pointer`, loaded one byte, then incremented the full
stack cursor. The new entry saves the prior four bytes of that private DP slot
in the same stack positions and loads the incoming format pointer there once.
Each byte load advances its low word with INC and advances the bank word only
on a low-word wrap. The final AND after the saved character is popped restores
the full-word N/Z test and clears the accumulator's retained high byte.

On every exit, including unsupported formats, PLX/STX restores both saved DP
words without disturbing the return value in A. A nested printf saves the outer
live cursor and restores it before returning. `_console_putc` and `_dec_format`
do not use the private slot; their separately allocated arithmetic/decimal
scratch remains independent. This is format-cursor ownership, while the console
map and screen cursor continue to be shared output state.

The public four-byte far-pointer/variadic ABI, Y/D/DBR preservation and A16/X16
return mode remain unchanged. The existing four-byte DP slot is reused. No RAM
is added, and the normal invocation's stack depth is unchanged: saved prior DP
words replace the old live stack cursor words. The variadic argument cursor
and character count keep their existing offsets and update logic.

The bank-word padding byte is private and ignored by long-indirect addressing.
Incrementing $00FF to $0100 therefore wraps the actual bank from $FF to $00,
preserving modulo-24-bit cursor arithmetic. Nested calls restore all four bytes
exactly, including the padding byte. Bank-crossing and wrap tests validate this.

## Verification

The new `tests/check-printf-cursor.py` is invoked from the normal compiler suite,
using the existing shared verification queue. Both NTSC and PAL check:

* Literal text, %% and multiple %g values followed by more format text.
* A runtime RAM format crossing $7E:FFFF into $7F, a NUL at $7F:FFFF, and a
  format crossing $FF:FFFF into mapped bank-$00 WRAM.
* Empty formats, unsupported formats, error/count returns and subsequent calls.
* Exact preservation of a poisoned four-byte prior cursor on every return.
* Nine actual printf invocations, five decimal-format calls, all output
  characters/tilemap contents, Y/D/DBR, stack balance and native width modes.
* Two real NMIs which themselves call printf: one immediately before a format
  byte read, the other immediately before decimal formatting. Every NMI return
  checks registers, stack/status/bank, all $E0-$FF words and the outer cursor.

Only the test library gets wait probes and an exported private cursor label.
The measured/production library has no probes or extra exports. The NMI handler
does not manually save the console cursor, so its preservation is exercised by
the nested printf implementation itself. It prints a literal and preserves its
other scratch/register state. Tests observe two nested NMI calls in each region.

`tests/check-prompt.py` now also prints 300 characters with a returned count of
300, checking the accumulator high-byte case. Existing prompt pixel verification,
font/palette, scrolling, control characters, WRAM-only output, VBlank DMA, ABI,
error paths and host references passed. Focused calculator checks also passed.

Full `make check` passed 27/27 suites / 76 jobs, including all 200873 arithmetic
cases, with the hardware-thread default of 20 workers in 391.94 seconds.
Evidence: `build/check/20261107T050010.644064Z/summary.json`. The compiler,
console objects, library source and registered tests still match the frozen
candidate used for measurement and verification. Compiler SHA256:
`50e3d1949c72d659368a9f160d231180cf2b78c0714712d1981ea766540b2619`.

## Evidence and reproduction

`build/printf-cursor/` retains baseline/candidate compiler/library/runtime objects,
sources, registered tests and SHA256 inventories; finite benchmark inputs and
per-process spans; instruction traces; `comparison.json`; and
`sample-summary.json` checking source/work-count identity and unchanged control
ROMs. The frozen compiler and all runtime objects except console.o and
calc_console.o match. Baseline/candidate sample artifacts and two checked
measurements per form are in `build/bank-costs/printf-before/` and `printf-after/`.

The initial cursor test link omitted io.o, which provides the decimal module's
ctype/errno dependencies. Adding the normal calculator dependency resolved it.
The first finite-driver source used an unsupported string-to-array initializer;
it was replaced with an ordinary string-literal argument before measurement.
No semantic failure was retried unchanged.

Reproduce with the saved baseline objects retained, fresh evidence paths and the
matching prerequisite build:

```text
make all smoke
python tests/check-printf-cursor.py
python tests/check-prompt.py
python tests/check-scalar-runtime.py
make check
```

The finite profiler needs the baseline snapshot and both calculator traces to
produce its combined summary. Do not rebuild the frozen baseline with the trial
library. Full arithmetic vectors, batch boundaries, assertions and default
hardware-thread worker selection are unchanged.
