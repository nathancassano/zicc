# Argument setup and known-bank entries

When the compiler knows which memory bank holds an argument, it can call a private version of the function that uses that bank directly. Other callers keep using the public version, which accepts a far pointer. Both versions are separate functions.

The subsequent [struct-reduction extension](struct-reduction-banks.md) also
handles a struct pointer plus signed word count, using the same object proof
and private call mechanism. The byte-loop limits and measurements below record
the initial implementation.

## Generic setup

The existing ABI makes A, X, flags and $E0-$FF arithmetic scratch call-clobbered;
Y, D and DBR are preserved. The earlier far-byte-loop backends unnecessarily
saved and restored their arithmetic DP words at every ordinary C call. These
saves and their return-value staging are removed. Far bases still live in the
same scratch locations, and the generic path retains all 24-bit bank-crossing
and full-Y-wrap handling. No new scratch or changed public ABI is introduced.

Live caller expressions remain on their invocation stack, as required by the
existing ABI. Native interrupt wrappers still preserve the scratch words their
handler uses. Local $00-$01 loop-counter ownership is unchanged.

## Private bank entries

`src/bank_calls.inc` scans direct calls before emission and reuses the existing
far-leaf/byte-loop analysis. It currently accepts two byte-pointer parameters,
one synchronized leaf loop and at most 48 loop-IR instructions. Each far actual
must be a real declared object address or string literal with a known extent.
Native near parameters already carry the bank-$7E contract. Unknown pointers,
integer addresses, unresolved ROM placement, pointer arithmetic and two-ROM
cursor combinations retain the generic call. No bank-number-only proof is used.

A private entry receives low-word offsets in X/A. For RAM/RAM, absolute X/Y
accesses use DBR=$7E. For one ROM cursor, that cursor uses X and absolute-long,X;
the RAM cursor uses absolute,Y. The ROM bank is a linker relocation, not a
hardcoded $80, and object containment and matching-bank assertions are checked
by ld65. A valid C access through the proven object stays inside that object;
its complete declared extent must fit the bank. Raw far addresses remain on the
bank-crossing generic path. Writes through a ROM cursor are never specialized.

Entries are shared by function and bank pattern, rather than by literal value.
The bank patterns are RAM/RAM, RAM/ROM and ROM/RAM: at most three per function,
with a translation-unit cap of 256. Only entries whose calls survive ordinary
emission are emitted. Forward definitions work. Definitions in another
translation unit retain their public ABI; there is no LTO, content folding,
call removal or inlining. `--no-bank-specialization` disables private entries
independently of the generic setup improvement.

## Validation and measurement

`tests/check-bank-calls.py` executes specialization on/off on NTSC and PAL.
Cases cover forward definitions, all three bank patterns, same-buffer copying,
unknown-bank physical crossings, two-ROM fallback, live caller values and
nested calls. A synthetic cross-bank ROM placement must fail the linker proof.
The normal interrupt test also runs a 12000-byte ROM copy/equality through the
private entries under IRQ/NMI, while unknown far scans still cross a physical
bank and wrap Y. Both private entries must actually receive interrupts; an NMI
nests inside the first IRQ. Every interrupt return checks registers, status,
D/DBR/PBR, stack and the live arithmetic DP words. Ordinary callees check the
public stack/Y contract, rather than inventing a callee-saved arithmetic ABI.

The sample harness records each private entry's logical function and narrow
argument ABI. Hooks count the real calls and decode ROM bank offsets correctly;
separate-driver/kernel builds still enforce opaque runtime inputs without LTO.
Assembly, maps, compiler/runtime/source hashes, raw logs and two matching runs
per sample form are retained in `build/bank-call-specialization/candidate/`.
The immediate baseline is the independently built loop integration compiler and
runtime under `build/merged-loop-recheck-047e073/candidate/`; a source/object
snapshot is retained in `build/bank-call-specialization/baseline.zip`.

| Sample | Form | Pre-bank clocks | Before clocks | After clocks | Versus before | Code bytes pre / before / after |
|---|---|---:|---:|---:|---:|---:|
| minimal | original | 18560 | 18560 | 18560 | +0.00% | 93 / 94 / 94 |
| minimal | runtime | 18560 | 18560 | 18560 | +0.00% | 103 / 104 / 104 |
| prompt | original | 374532 | 374578 | 374578 | +0.00% | 1907 / 2114 / 2114 |
| prompt | runtime | 374648 | 374646 | 374646 | +0.00% | 1917 / 2124 / 2124 |
| calc | original | 586538 | 644064 | 644064 | +0.00% | 12574 / 14986 / 14974 |
| calc | runtime | 586538 | 644064 | 644064 | +0.00% | 12574 / 14986 / 14974 |
| insertion_sort | original | 29444 | 30008 | 30008 | +0.00% | 509 / 518 / 518 |
| insertion_sort | runtime | 29444 | 30008 | 30008 | +0.00% | 509 / 518 / 518 |
| string_processing | original | 13122 | 18544 | 12696 | -31.54% | 498 / 636 / 581 |
| string_processing | runtime | 13122 | 18544 | 15964 | -13.91% | 498 / 636 / 602 |
| integer_operations | original | 26350 | 26642 | 26642 | +0.00% | 1990 / 2077 / 2077 |
| integer_operations | runtime | 45398 | 45762 | 45762 | +0.00% | 2096 / 2183 / 2183 |
| function_calls | original | 104004 | 104492 | 104492 | +0.00% | 1815 / 1885 / 1885 |
| function_calls | runtime | 104004 | 104492 | 104492 | +0.00% | 1815 / 1885 / 1885 |
| structures_and_tables | original | 13884 | 16506 | 16506 | +0.00% | 1777 / 1964 / 1964 |
| structures_and_tables | runtime | 13884 | 16506 | 16506 | +0.00% | 1777 / 1964 / 1964 |

Original string timing is 31.54% below the immediate baseline and 3.25% below
the pre-bank build. Separate-TU strings improve 13.91% versus the immediate
baseline and remain 21.66% above pre-bank. These are different optimization
contexts: private entries require the definition and actual object proofs in
the same TU; the separate version measures the generic public ABI alone.

String code falls from 636 to 581 bytes in the original form and to 602 bytes
in the separate form. For the original form, public copy/equality shrink by
12/22 bytes and main shrinks by 90; two private entries add 31/38 bytes, for a
net 55-byte reduction. No call is removed. Actual recorded calls remain three
copies, four equalities and four reversals in both forms. Source bytes and bank
numbers are not folded into return constants. The calculator saves 12 code bytes
without a timing change; the other six sample timings and sizes are unchanged.
All ROM files remain 32768 bytes.

`build/bank-call-specialization/assembly.md` retains the complete public entries,
private entries and caller assembly. `--no-bank-specialization` gives the generic
setup-only behavior when the definition is visible. The benchmark's separate
TU form independently prevents call-site specialization and LTO.

A single concurrent structure-sample run timed out at the emulator's READY/resume
boundary. The isolated retry succeeded and matched the other repetition; the
failing worker log and `measurement-retry.json` are retained.


Full `make check`: 27/27 suites / 76 jobs, 20 workers, 359.33 seconds,
including all 200873 arithmetic cases. Evidence:
`build/check/20261107T031753.017630Z/summary.json`. Compiler SHA256:
`66b80f02f153142fbfd7f49bf785b629ebd24451a6d801b24fb6f465175a1ec4`. No compiler changes followed this run.
