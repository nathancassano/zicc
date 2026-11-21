# Indexed far byte loops

When a loop advances several far pointers by one byte at the same time, each
pointer has traveled the same distance from its starting address. Register Y
can hold that distance for all of them. Register X can track one near pointer.
The earlier byte-loop code in `src/register_loops.inc` used a separate memory
slot for each pointer. The new code in `src/indexed_far_loops.inc` keeps each
far starting address in three locally saved direct-page bytes and preserves
the zero padding byte required by the calling rules.

The subsequent [argument/base setup work](bank-call-specialization.md) removes
redundant ordinary-call saves of caller-clobbered arithmetic DP and adds proven
known-bank private entries. Measurements below retain this earlier stage.

## Selection and semantics

Every indexed far cursor must advance exactly once per iteration, after its
last memory access in that iteration. Deferring its private step to the shared
INY preserves the order of all loads and stores, including overlapping source
and destination regions. Up to two far bases can share Y. The loop never assumes
that either base starts at a bank boundary or stays in one bank. Long-indirect,Y
performs the physical bank carry; when Y wraps, each far base's bank byte is
incremented modulo 256. The byte in B survives all address maintenance.

A near cursor uses absolute,X, with ordinary INX/DEX updates. All-far counted
loops can hold their remaining count in X. Other shapes retain the prior DP
backend: backward far cursors, multiple far steps, a far access after its step,
and counted loops that also need X for a near cursor. Calls, escaping cursor
homes and unsupported expressions remain barriers under the existing IR rules.

The selector consumes any live X/A word input before initializing its far bases.
It saves Y and only the DP words occupied by far bases; it no longer snapshots
unused X/A inputs or creates a DP copy of a near cursor. Word iteration results
come from Y modulo 65536. Predicate exits reuse an already loaded byte and the
comparison flags where every incoming failure edge makes them available.

Near-to-far conversion also omits the NULL test for an actual array object's
address or `&object`. Pointer variables and pointer arithmetic keep the general
NULL-preserving conversion. This is an expression-shape proof, with no function
or parameter-name special cases.

## Validation

The separate driver/kernel checks cover optimized, disabled and saved-compiler
variants on NTSC and PAL. They include unaligned bank crossings, forward and
backward cursors, identical pointers, overlapping bounded copies, byte temporaries,
reordered register/stack parameters, returned near pointers, nullable conversions,
and cases that must retain the DP fallback.

`tests/check-far-loop-interrupts.py` seeds a 65793-byte input to force a physical
bank crossing and a full Y wrap. The optimized and disabled versions run on both
regions under real NMI and vertical IRQ delivery. The first IRQ waits for a
nested NMI. Hooks require interrupts during near-X copying, scanning and equality,
and verify A (including B), X, Y, D, DBR, PBR, status, stack and $E0-$E7 after every
interrupt return. Optimized callees also restore their private DP words and Y.
Raw scripts and logs are in `build/far-loop-interrupt-check/`.

Both checks run inside the normal compiler suite of `make check`.

## Comparison

The immediate baseline already includes the recovered far-byte loops and aggregate cursors; the second baseline is the fresh build
immediately before the bank-$7E migration. Baseline assembly, ROMs and runtime
objects are retained separately. No baseline compiler is linked with candidate
runtime objects. The previous inputs are frozen in
`build/indexed-far-loops/previous-sources.zip` and its comparison JSON; the
pre-bank baseline is `build/bank7e-change/baseline/`.

| Sample | Form | Pre-bank clocks | Previous clocks | New clocks | Versus previous | Versus pre-bank | Code bytes: pre / previous / new |
|---|---|---:|---:|---:|---:|---:|---:|
| minimal | original | 18560 | 18560 | 18560 | +0.00% | +0.00% | 93 / 94 / 94 |
| minimal | runtime | 18560 | 18560 | 18560 | +0.00% | +0.00% | 103 / 104 / 104 |
| prompt | original | 374532 | 374578 | 374578 | +0.00% | +0.01% | 1907 / 2114 / 2114 |
| prompt | runtime | 374648 | 374646 | 374646 | +0.00% | -0.00% | 1917 / 2124 / 2124 |
| calc | original | 586538 | 644700 | 644652 | -0.01% | +9.91% | 12574 / 15079 / 15038 |
| calc | runtime | 586538 | 644700 | 644652 | -0.01% | +9.91% | 12574 / 15079 / 15038 |
| insertion_sort | original | 29444 | 30008 | 30008 | +0.00% | +1.92% | 509 / 518 / 518 |
| insertion_sort | runtime | 29444 | 30008 | 30008 | +0.00% | +1.92% | 509 / 518 / 518 |
| string_processing | original | 13122 | 24174 | 18544 | -23.29% | +41.32% | 498 / 727 / 636 |
| string_processing | runtime | 13122 | 24174 | 18544 | -23.29% | +41.32% | 498 / 727 / 636 |
| integer_operations | original | 26350 | 26642 | 26642 | +0.00% | +1.11% | 1990 / 2077 / 2077 |
| integer_operations | runtime | 45398 | 45762 | 45762 | +0.00% | +0.80% | 2096 / 2183 / 2183 |
| function_calls | original | 104004 | 104656 | 104656 | +0.00% | +0.63% | 1815 / 1902 / 1902 |
| function_calls | runtime | 104004 | 104656 | 104656 | +0.00% | +0.63% | 1815 / 1902 / 1902 |
| structures_and_tables | original | 13884 | 16554 | 16506 | -0.29% | +18.89% | 1777 / 1972 / 1964 |
| structures_and_tables | runtime | 13884 | 16554 | 16506 | -0.29% | +18.89% | 1777 / 1972 / 1964 |

String profiler breakdown (exclusive master clocks across all calls):

| Function | Pre-bank | Previous | New |
|---|---:|---:|---:|
| copy_text | 2402 | 6070 | 3428 |
| reverse_text | 3856 | 3816 | 3816 |
| text_equal | 3880 | 9912 | 7156 |
| main | 3002 | 4394 | 4162 |

The profiler includes the same 18-clock boundary difference in each complete
string profile; differences between these columns cancel it. Measurements use
FastROM and identical runtime work, with two matching repetitions for both
original and separate-driver/kernel builds without LTO. Calls, inputs, results,
iterations and hardware operations are checked. All ROM files remain 32768 bytes.
Code bytes above mean STARTUP+CODE, not file size.

Candidate raw measurements, maps, hashes and ROMs are in
`build/indexed-far-loops/candidate/`. All three complete string-function assembly
versions, including caller main, are retained in
`build/indexed-far-loops/assembly.md`. The default build recompiles runtime C
with the candidate compiler before measurement.

Full `make check`: 27/27 suites, 76 jobs, 20 workers, 358.41 seconds;
all 200873 arithmetic cases retained. Evidence: `build/check/20261107T020112.715348Z/summary.json`.
Compiler SHA256: `23cb8c6d3c0583a7d723dd77fd37201c14fb01990a83e9469874f76cf454fcc0`.


## Assembly changes and remaining cost

| Operation | Pre-bank | Previous far backend | Indexed far backend |
|---|---|---|---|
| Copy load | `LDA absolute,X` | `LDA [$E0]` | `LDA [$E0],Y` |
| Copy store | `STA absolute,Y` | `STA [$E4]` | `STA absolute,X` |
| Copy cursor steps | INX / INY | DP increments and carry branches | INX / INY, bank update on Y wrap |
| Copy DP save set | none | $E0/$E2/$E4/$E6 | $E0/$E2 |
| Equality cursor steps | INX / INY | Two DP increments and carry chains | One INY, bank updates on Y wrap |
| Equality DP save set | none | $E0/$E2/$E4/$E6 | $E0/$E2/$E4/$E6 |
| Extra X/A snapshots in far leaves | n/a | PHX / PHA | none |

The copy hot loop is now (labels shortened):

```asm
loop:
    lda [$E0],y
    beq done
    sta a:$0000,x
    inx
    iny
    bne loop
    inc z:$E2
    bra loop
done:
    sta a:$0000,x
```

Equality uses one displacement for both bases:

```asm
loop:
    lda [$E0],y
    beq terminated
    cmp [$E4],y
    bne compared
    iny
    bne loop
    inc z:$E2
    inc z:$E6
    bra loop
terminated:
    cmp [$E4],y
compared:
    ; Boolean result from Z, then restore the saved DP words and Y
```

Total string clocks fall from 24174 to 18544 (-23.29%), and code from 727 to
636 bytes. The pre-bank figures were 13122 clocks and 498 code bytes. The
remaining 5422 clocks (+41.32%) comprise copy +1026, equality +3276, caller/main
+1160 and reverse -40. Reverse retains its instruction sequence. Equality is
the largest remaining gap: each call still saves/restores four DP words,
initializes two bases, and receives two four-byte stack arguments instead of
register-held near pointers. Long-indirect data accesses fetch three pointer
bytes from WRAM. The copy keeps only one far base, but still has its setup and
stack argument costs. Empty and one-character calls amplify fixed costs.

The calculator also saves 41 code bytes and 48 clocks; the structure sample
saves 8 code bytes and 48 clocks through simpler proven-address widening. Other
sample code sizes and timings are unchanged from the immediate baseline.

One concurrent structure-sample measurement timed out after Mesen's READY
pause. Its failing worker log is retained; the isolated retry passed and matched
the other repetition. `build/indexed-far-loops/measurement-retry.json` records it.
