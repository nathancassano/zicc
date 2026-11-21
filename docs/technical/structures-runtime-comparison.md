# Inventory comparison with enforced runtime work

How long does it take a SNES to add up an inventory? If the compiler can see
every item and price while building the ROM, it can calculate the answer
before the SNES starts. To time the work on the console, this test compiles the
driver and the two functions it calls in separate C files. Each compiler can
optimize within a file. Neither can see the catalog while compiling the driver.

Both compilers get the same header and source files,
`samples/structures_and_tables_runtime.c` and `samples/inventory_kernels.c`.
The build checks that the function bodies match the original
`structures_and_tables.c` and keeps cross-file optimization (LTO) off.

Mesen watches the running program and checks the work as it happens.

- Three inventory calls take counts 0, 3 and 1 and return 0, 1849 and 200.
- Two adjustment calls take a change of -2 and return 1 and 0.
- Four multiplications use quantity/price pairs (2, 125), (3, 200), (1, 999)
  and (1, 200).

The checks also cover the result from `main`, its stack, the direct-page and
data-bank registers, register widths and the number of hardware multiplications.
The MSVC build on the PC returns zero. Two independent Mesen runs for each
target agree exactly. As a cross-check, the original single-file VBCC ROM
fails the multiplication check because it calculated some answers in advance.

## Matched results

Timing starts when `main` begins and ends when it returns. Each tick is one
SNES master clock. Startup and exit cleanup fall outside the measurement.
The zicc SlowROM configuration
relocates the same compiled objects to bank $00, using a local copy of the
linker configuration. Startup establishes DBR from its code bank. Hooks confirm
DBR=$00 for both SlowROM targets and $80 for the normal FastROM target.

| Metric | zicc FastROM | zicc SlowROM | Stock VBCC SlowROM |
| --- | ---: | ---: | ---: |
| Main master clocks | 13,884 | 16,530 | 26,012 |
| Main microseconds | 646.45 | 769.65 | 1,211.14 |
| Application code bytes | 306 | 306 | 405 |
| All linked code bytes | 1,783 | 1,783 | 992 |
| Used non-asset ROM bytes | 1,871 | 1,871 | 1,092 |
| Inventory calls | 3 | 3 | 3 |
| Adjustment calls | 2 | 2 | 2 |
| Source-level products | 4 | 4 | 4 |
| Hardware byte products | 28 | 28 | 48 |

These figures include [guarded-update leaf selection](guarded-updates.md), which
reduces adjust_quantity from 70 to 17 code bytes and removes its frame. Before
that step, zicc took 15,066 FastROM / 17,900 SlowROM master clocks.

With both executing in SlowROM, zicc takes 36.45% less elapsed time. Normal
FastROM zicc takes 46.62% less time than stock SlowROM VBCC. This matches
runtime workload and, for the middle/right columns, ROM speed; each compiler
retains its native pointer, call and register ABI. The comparison does not force
identical machine instructions or disable legitimate local optimizations.

The current zicc source/frame layout is unchanged by splitting the files.
Its integer runtime is a monolithic object, accounting for the larger linked
code total despite smaller application code. VBCC pulls selected library members.
ROM fill/file length is excluded from used-ROM figures.

| Profiled component | zicc SlowROM | VBCC SlowROM |
| --- | ---: | ---: |
| inventory_value, 3 calls inclusive | 14,276 | 22,276 |
| inventory_value self time | 4,572 | 8,620 |
| 32-bit product helpers, 4 calls inclusive | 9,704 | 13,656 |
| adjust_quantity, 2 calls inclusive | 336 | 1,106 |

The total for `inventory_value` already includes time spent in its multiply
helpers. Use its self time to see how much work happened inside the function
itself. VBCC's 32-bit helper calls its 16-bit helper three times per product.
Those twelve calls account for 9,992 master clocks.

## Why the original VBCC result was faster

Inspection and fresh tracing of the saved single-file VBCC ROM confirm:

- Zero calls to inventory_value and adjust_quantity: surviving work is inlined.
- The two constant-catalog inventory checks disappear, leaving one product.
- No catalog reads remain during main; copied fields become immediate values.
- One 32-bit multiply invokes three 16-by-16 helpers: 1*200, 1*0 and 0*200.
- All twelve hardware byte products execute, including the zero cross-products.

There is no zero-value early exit or operand-width shortcut in that multiply.
The 58-byte wrapper always computes low*low, low*high and high*low via the
66-byte full 16-by-16 helper. That helper keeps A 16-bit, temporarily uses 8-bit
X/Y for byte hardware writes, and overlaps useful work with hardware waits.
Its conditional carry correction is unrelated to skipping zero operands.

The original single-file total of 7,652 clocks therefore measured less runtime
work than zicc's four products. It is a useful whole-program optimization
result, but not a measurement of the same inventory workload. Original-ROM trace
scripts, raw linked-helper bytes, logs and hashes are in
`build/vbcc-inventory-inspection/`.

## Historical evidence

The comparison runner has been retired.

The unchanged stock VBCC release uses `-O3 -msfp4 -lms4 -lvc`. Its local config
only omits the optional absent vcpr6502 commands, as in existing comparisons.
Commands, build logs, source/compiler/runtime/library hashes, assembly, symbols,
maps, ROMs, repeated execution logs and per-function profiles are retained in
`build/structures-runtime/manifest.json` and `comparison.json` and adjacent files.
