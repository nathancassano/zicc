# Post-mortem of the original SNES π demo

The intended contest was a Sega Genesis versus SNES race to calculate and
display π. The supplied SNES ROM reaches its completion signal, but only the
integer digit and the first 41 fractional digits are correct. The supplied
Genesis ROM implements the same faulty recurrence with native 68000 division.
Both original ROMs now have emulator timings.

## The state was already wrong on pass three

The sample uses the bounded Rabinowitz–Wagon spigot recurrence. Every pass
walks the mixed-radix array from right to left. At position `i` it divides
`10*A[i-1] + q*i` by `2*i-1`, carries the quotient left, and keeps the
remainder for the next pass. The radix reaches 5,373, while both `aux` and
`A[]` can store only 0 through 255.

On the third pass, the first position visited is `i = 2687`. The incoming
quotient is zero and the old cell contains 200, so the division is
`2000 ÷ 5373`. The quotient is zero and the remainder is 2,000. The byte
assignment stores 208. A write hook on the bundled ROM saw `A[2686]` go
`2 → 20 → 200 → 208`, including initialization. That cell is at the
low-significance end, so the screen can look convincing for many digits
after the calculation has gone wrong. The first visible arithmetic error
is fractional digit 42, where it emits `8` in place of `9`. The bundled ROM
and the portable legacy port agree on the entire faulty stream.
[Original ROM comparison](post-optimization-pi.md)

## Fixing one width exposes the next limit

A host replay kept the original recurrence and delayed-digit logic, varied
the indicated widths and array length, and compared each stream against
Chudnovsky π. The matching-prefix counts exclude the leading sentinel and
include the integer digit `3`.

| Remainder storage | Dividend | Array cells | Passes | Correct prefix |
| --- | --- | ---: | ---: | ---: |
| 8-bit | 16-bit | 2,687 | 896 | 42 of 896 |
| 16-bit | 16-bit | 2,687 | 896 | 536 of 896 |
| 16-bit | 32-bit | 2,687 | 896 | 810 of 896 |
| 16-bit | 32-bit | 2,986 | 896 | 896 of 896 |
| 16-bit | 32-bit | 3,000 | 904 | 904 of 904 |

The original byte-remainder run never overflows its 16-bit dividend.
With word remainders, the first overflowing dividend is
`10*3914 + 11*2682 = 68642` on pass five. A 16-bit dividend turns it into
3,106 before division. Once that width is fixed too, the finite series
behind the 2,687-cell array still runs out of precision. The larger arrays
in the table are verified for these exact runs. A general bounded spigot
needs enough terms to resolve the requested decimal prefix and its final
carry. [Gibbons, *Unbounded Spigot Algorithms for the Digits of Pi*, §3](https://www.cs.ox.ac.uk/jeremy.gibbons/publications/spigot.pdf)

Two independent display bugs made the result harder to judge. The code
prints its initial pending-digit value of zero as a real character and
never inserts the decimal point. It sends 897 characters to a 32-column
screen with 28 visible rows, placing the last character on row 29.
[Original display verification](post-optimization-pi.md)

## What the stopwatch measured

The original does 2,687 cell updates per pass for 896 passes, plus one
divide by ten per pass. The ROM trace counted **2,408,448 calls to
`divmodu`**. Its quotient comes from a TCC scratch byte at `$18` after the
remainder operation, a dependency on the shipped compiler and runtime.
Of those divisions, 2,292,864 (95.2%) have a divisor above 255. The SNES
hardware divider takes a 16-bit dividend and an 8-bit divisor, so those
operations cannot go straight through it. The Genesis's 68000 can use
`DIVU.W` for a 32-bit dividend and 16-bit divisor and get both a word
quotient and a word remainder in one instruction. That is a concrete
advantage for this particular recurrence. [Original ROM comparison](post-optimization-pi.md),
[Nintendo SNES Development Manual, §15](https://floating.muncher.se/bot/manual/book1_text.pdf),
[Sega Genesis Technical Overview](https://segaretro.org/images/1/18/GenesisTechnicalOverview.pdf),
[Motorola M68000 Programmer’s Reference Manual, DIVU](https://www.nxp.com/docs/en/reference-manual/M68000PM.pdf)

The shipped ROM took **788.433 seconds** from NTSC power-on to the measured
display endpoint. A later FastROM zicc build ran the same legacy
arithmetic and emitted the same stream in **251.949 seconds**, with a
different compiler, runtime, ROM mapping and text renderer. The replacement
assembly took **18.201 seconds** to display `3.` and 896 correct fractional
digits. It changes the arithmetic workload, using a base-64 arctangent
series and arranging its division steps around the SNES divider. Those
numbers show how much the chosen implementation mattered on the same
console. [Original timings](post-optimization-pi.md).

## What the Genesis ROM actually does

The supplied `pi_genesis.zip` contains `src/main.c`, the linked 68000 ELF
`out/rom.out`, symbols, and the 128 KiB cartridge image
`out/pi_megadrive.bin`. Both ELF load segments match the cartridge bytes
apart from the two-byte header checksum. The symbols therefore locate
the code and initialized data in the shipped ROM.

| ROM address | Evidence |
| --- | --- |
| `$012718` | Initial `len` is 2,687. |
| `$003420` | Initializes the outer pass counter to 896. |
| `$003474` | `ANDI.L #$FFFF,D0` zero-extends the word dividend. |
| `$00347A` | `DIVU.W D6,D0` returns the packed remainder and quotient. |
| `$003480–$003484` | `SWAP D7` exposes the remainder. `MOVE.B D7,(A0)` stores only its low byte, then `MOVE.W D0,D7` retains the word quotient. |
| `$00349A` | A second `DIVU.W` finishes the pass by dividing by ten. |
| `$00212A` | `print_digit` calls `VDP_drawText`. It advances to the next row at column 32. |

The loop bounds imply 2,408,448 native divides, the same number of
divmod operations observed on the SNES. A host replay of the Genesis
widths reproduces the first truncation on pass three and gives the same
897-character stream and final array as the archived SNES ROM run. The
Genesis keeps a 16-bit quotient and a 16-bit
count of pending nines, but in this workload the replay peaks at 103
and 2 respectively. Both fit in the SNES byte fields. The expected
Genesis display therefore has the same leading zero, missing decimal
point, and wrong digit 42 after the implied point. Its last character
is sent to column 0, row 28 in zero-based coordinates. The visible
capture confirms the 896 visible glyphs. [68000 `DIVU` semantics](https://www.nxp.com/docs/en/reference-manual/M68000PM.pdf)

The exact supplied cartridge booted in the Genesis Plus GX libretro core
(`v1.7.4 b9c2316`) with NTSC-U forced. Two headless runs agreed. The first
frame with all 896 visible characters and the expected final work array
was frame 5,603 (93.504 emulated seconds from power-on). The completion
background color first appeared on frame 5,604 (93.520 seconds) and the
captured image stayed identical through frame 5,611. This timing has one
frame of resolution at the core's reported 59.922743 Hz. The frame check
covers the visible 32 × 28 grid. The `print_digit` call trace and the
instruction-level calculation interval remain unmeasured.

For live verification, boot the bundled cartridge image in an NTSC
Genesis emulator with a 68000 debugger. The archive already contains the
linked ELF and symbols. Its header advertises `JUE` and `SEGA SSF`.
It stores checksum `$8AF6`, while the big-endian word sum of the file
from `$200` onward is `$C9D0`. Record whether the exact image boots.
[Sega Genesis Software Manual, checksum](https://segaretro.org/images/9/95/GenesisSoftwareManual.pdf)

1. At `print_digit` entry (`$002110`), read the first ASCII byte through
   the pointer at `12(SP)`. Expect 897 bytes in call order.
2. At the VDP control-port write of `$872F` (`$003510`), dump 2,687
   bytes from `$FF005A` and record the emulated clock count. Record
   the entry clock at `calculate_pi` (`$0033E4`) as well for a
   calculation-and-output interval.
3. Save the first completed frame with the final tilemap and its clock
   count for the power-on-to-display interval.

The five-configuration benchmark matrix
now covers both the legacy and revised kernels, including hand-written
assembly on both consoles and modified VBCC SlowROM.

## Matched Genesis versus SNES rematch

The revised C benchmark runs
the same fixed-point Machin kernel, digit-count driver and RAM output
routine on both consoles. The three shared units compile separately
without LTO, and the driver reads the 896-digit input through a volatile
object. Each platform draws the completed RAM buffer with its own renderer.

| Target | Kernel and RAM output | Power-on to complete screen |
| --- | ---: | ---: |
| Genesis NTSC-U, SGDK GCC 13.2.0 | 20.216 s | 20.743 s |
| SNES NTSC FastROM, zicc | 32.947 s | 33.293 s |

Both runs per target agreed and verified all 898 characters in RAM and
on screen. The Genesis disassembly uses native `DIVU.W`. Genesis Plus GX
verified the final sum limbs after decimal conversion and measured the
kernel with SGDK's VBlank and vertical-counter timer. The completed
screen first appeared on frame 1,243 at 59.922743 Hz. Mesen verified the
SNES sum before conversion and counted 247,507 term-limb writes. Its
kernel and display intervals were 707,613,444 and 715,038,900 master
clocks. The Genesis verifier samples frames and RAM and does not count
individual writes. These measurements include each platform's CPU and
compiler code generation, with startup and rendering included in the
completed-screen column.

The rerun's disassembly, input hashes, verification results and Genesis
screenshot are archived in
`C:/gendev/pi-benchmark-evidence/matched`.

## Evidence

The early write trace is in `C:/gendev/pi-benchmark-evidence/original/snes/trace.log`.
The width experiment applies separate masks to the stored remainder and
pre-division dividend. Its first row reproduces the archived original ROM's character stream.

Genesis static evidence is in
`C:/gendev/pi-benchmark-evidence/original/genesis/static-result.json`. The cartridge SHA-256
is `01536bbb8bca897360a6ccc80f88a0ba2609e8cd3f2de0058b38e9f1a421c984`.
The replayed digit stream and final array hashes match the archived
SNES results. Compare a live capture against these SHA-256 values.

| Capture | SHA-256 |
| --- | --- |
| ASCII stream, no terminator or newline | `a0ebe649b69aeb7abfb87592079508c07b39bbf00bcec42cd2424f929834e7c7` |
| Final work array | `f668a3d2e9c53650230a6b9f918d0410ae0a2ad5c36588725ac551aa85f24a39` |

The Genesis live capture is in `C:/gendev/pi-benchmark-evidence/original/genesis/genplus-result.json`.
Its final work-array dump is `genplus-final-array.bin` and its first frame
with the completion background is `genplus-frame-5604.png`. The headless
frontend is `run_genesis.py` in the same evidence directory.
