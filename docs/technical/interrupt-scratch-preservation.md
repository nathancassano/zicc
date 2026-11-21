# Interrupt scratch preservation

An interrupt can pause a calculation that uses temporary memory. Before its handler runs, it needs to save only the words it might change. Afterward it restores them so the paused calculation can continue.

Generated native user handlers preserve only arithmetic workspace words they
can overwrite. `src/codegen/codegen.inc` emits a handler once, records stores and memory
read/modify/write effects in its complete selected instructions (including frame
cleanup), then inserts ascending saves and descending restores. Analysis is per
function and unions effects across emitted paths; saves need no runtime tests.

The workspace is sixteen words at `$00E0-$00FF`. Read-only use needs no save.
Allowed software comparison helpers clobber no workspace; `__shl32`, `__ushr32`
and `__sshr32` clobber `$E0/$E2`. Their staged inputs can cause additional caller
stores. These contracts live with the interrupt-safe helper whitelist; unsafe
helpers remain rejected. Other reserved workspace ownership rules are unchanged.
Register saves, user-before-library order, early returns and explicit interrupt
enabling are unchanged. The library-only NMI clock wrapper still needs no scratch.

## Matched fixture

`tests/interrupt_scratch.c` places a helper-heavy COP before a scratch-free NMI
to detect mask leakage. It includes user DMA, an IRQ with one inline scratch
word and a BRK with discontiguous scratch use.

| Handler | Saved words | Scratch stack before | Scratch stack after | Code saved |
| --- | --- | ---: | ---: | ---: |
| `supervisor` (COP) | E0, E2, E4, E6 | 32 B | 8 B | 60 B |
| `vblank` (NMI) | None | 32 B | 0 B | 80 B |
| `raster` (IRQ) | E2 | 32 B | 2 B | 75 B |
| `software_break` (BRK) | E0, E4 | 32 B | 4 B | 70 B |

Identical source compiled with the pre-change and candidate compilers assembles
to 929 versus 644 code bytes: **285 bytes saved**, with unchanged 52 B BSS.
Each removed word eliminates a two-byte PEI and a three-byte PLA/STA pair.
Assembly, objects and segment dumps are in `build/interrupt-scratch-change/`.
No CPU timing claim is made from byte counts.

## Verification

`tests/check-interrupt-scratch.py` checks exact save/restore sets, register-only
32-bit shifts, empty handlers, code after unconditional return and user globals
with names resembling workspace symbols. It independently audits runtime helper
clobbers and shared comparison exits; unexpected instructions/targets fail.

The fixture executes on NTSC and PAL using the native interrupt test driver.
Actual NMI, IRQ, BRK and COP delivery exercises all four A/X widths, nonzero D/DBR,
stack checks, user DMA before the clock tick, and sentinels across **all 32 scratch
bytes**, including unsaved words. Evidence/input hashes are retained under
`build/interrupt-scratch-check/`. The existing compiler suite includes these
checks without changing the shared verification queue.
