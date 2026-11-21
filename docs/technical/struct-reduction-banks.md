# Struct reduction setup and bank entries

When a loop adds products from records in an array, the compiler can use the actual field positions and size of each record to find the next pair. The general far-pointer version uses six bytes in its stack frame, down from ten. Calls with a known bank can save more setup.

The counted field-product reduction keeps its established recognition grammar:
a signed word widened to unsigned long, multiplied by an unsigned-long field,
accumulated over a signed count. The plan records the actual record stride and
field offsets, with no function-name or field-name special cases.

## Generic far entry

Y is borrowed once for all three field-word loads, rather than twice. The sign
branch immediately follows the signed quantity load/store, before PLY can alter
N/Z, so the repair CMP is eliminated. Y is restored before `__mul16x32` and the
frame accesses. The helper and all arithmetic semantics remain unchanged.

The cursor stays at $F0-$F3, outside the multiply helper's $E0-$EB workspace.
Arithmetic scratch is caller-clobbered, so the callee no longer saves/restores
those cursor words. Its frame falls from 10 to 6 bytes: sum at 1/3,Y, remaining
count at 5,Y, saved Y at 7,Y. The existing generic 24-bit cursor carry and field
loads crossing a bank are retained. Zero/negative counts return before any data
access. Y, D and DBR retain their existing public ABI contracts.

## Known-bank entries

The existing out-of-line specialization pass also recognizes struct-pointer /
signed-word-count reductions. It shares the reduction analysis and near-loop
emitter with the normal near reduction. A private RAM entry uses absolute,X field
loads; a ROM entry uses relocatable absolute-long,X loads. The low pointer word
arrives in X and count in A, eliminating four-byte pointer marshalling and wide
result stack cleanup at each eligible call.

As with byte loops, an actual declared object extent supplies the bank proof;
linker assertions check ROM containment and bank consistency. Unknown pointers,
raw addresses, pointer arithmetic and external definitions retain the public
far ABI. The pass does not inline or fold the products into constants. The
multiply helper still receives every signed/extended word and full long value.

Both RAM and ROM variants are shared per function and bank pattern. Keeping the
public fallback and adding private entries has a code-size cost; the measurements
below report that cost explicitly alongside generic-only and specialized timing.
`--no-bank-specialization` isolates the generic emitter improvements.

## Validation

`tests/check-bank-reductions.py` executes specialization enabled, disabled and
unoptimized on NTSC/PAL for 6-, 8- and 12-byte records. It checks -32768/-1/0/32767
quantities, full-width prices, modulo-32-bit results, zero and negative counts,
opaque count expressions, caller values live across calls, raw crossing fields
and cursor carries. Definitions follow the caller to test forward analysis.

The IRQ/NMI suite additionally executes both private reduction entries and an
11000-record raw far reduction spanning a physical bank. Every interrupt return
checks all $E0-$FF words, registers, status and stack; the first IRQ waits for a
nested NMI. Existing byte-loop and generic full-Y-wrap checks are retained.
The full suite still uses the shared hardware-thread-default verification queue.

## Comparison

The baseline includes far-call setup improvements and proven-bank pointer specialization, with matched compiler and runtime artifacts
under `build/bank-call-specialization/candidate/`; a fresh snapshot is retained
in `build/struct-bank-reduction/baseline.zip`. The pre-bank baseline remains
`build/bank7e-change/baseline/`. Baseline and candidate objects are not mixed.
| Form | Pre-bank clocks | Before clocks | After clocks | Versus before | Code bytes pre / before / after |
|---|---:|---:|---:|---:|---:|
| original | 13884 | 16506 | 14452 | -12.44% | 1777 / 1964 / 2104 |
| runtime | 13884 | 16506 | 15702 | -4.87% | 1777 / 1964 / 1939 |

All 16 sample builds / 32 execution-checked repeated measurements agree. The
other seven samples have unchanged clocks and code sizes. Inventory still makes
three calls, executes four word-by-long products and triggers 28 hardware partial
products; inputs and results are checked in the separate-TU form without LTO.
The original form uses private entries, while the separate form retains the
public far ABI. No contents or products are folded into constants.

The original form improves 12.44% and remains 4.09% above pre-bank; generic-only
improves 4.87% and remains 13.10% above pre-bank. The private reduction's own
exclusive profile, excluding the multiplier, totals 3976 clocks: the same as
pre-bank. Most of the remaining whole-sample gap is in the existing multiply
helper's long bank-zero MMIO accesses. The helper source is unchanged here.

Code size is an explicit tradeoff. The public reduction shrinks 153 -> 128 bytes
and main shrinks 236 -> 188, but keeping the public fallback plus RAM/ROM private
bodies adds 105 + 108 bytes. Thus original total STARTUP+CODE grows by 140 bytes
(1964 -> 2104). Generic-only total shrinks by 25 bytes (1964 -> 1939). The catalog
remains 24 bytes, Item remains 8 bytes, and every image file remains 32768 bytes.

Public-before/public-after, private entries and caller assembly are retained in
`build/struct-bank-reduction/assembly.md`. Raw maps, hashes, measurements and
scripts are under `build/struct-bank-reduction/candidate/`. A concurrent integer
measurement hit Mesen's READY/resume timeout; its isolated retry passed and matched
the other repetition. The failure log and `measurement-retry.json` are retained.

Full `make check`: 27/27 suites / 76 jobs, 20 workers, 378.35 seconds, including
all 200873 arithmetic cases. Evidence:
`build/check/20261107T034224.477764Z/summary.json`.
Compiler SHA256: `33c88a0cbb0ead38cbe8f21d3963a522f91bf3a95d03e30d9bfe1c02f0c75fd9`.

