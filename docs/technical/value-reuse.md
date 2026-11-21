# Dominated immutable-value and comparison reuse

If two expressions read the same array element, zicc can sometimes keep the
first value and use it again. The first read must happen on every path to the
second, and nothing in between may change the array or its index. A similar
check lets zicc reuse the result of a comparison.

The baseline is the saved compiler and ROMs from the isolated homebrew-samples
[private-region work](private-regions.md). The first measurements were taken
before committing and used focused checks. Full verification followed before the follow-up commit.

## General selection and safety

`src/value_reuse.inc` performs bounded typed reuse after inlining/body
simplification and before address CSE. Named array bases must remain visible
until value selection; remaining addresses still receive the existing CSE pass.
`--no-value-reuse` restores the previous ordering and reproduces baseline assembly
for both sample C units.

The pass recognizes nonvolatile byte/word reads from immutable named arrays and
word reads from mutable named arrays, including fixed member arrays. Indices must
be pure expressions of constants and unescaped private integers. Arbitrary
pointer variables, volatile reads, wide values and unsupported control flow keep
their existing lowering. There are no source/function/asset-name selectors.

A capture is assigned at the original read, not hoisted or speculated. Only a
dominating capture from an earlier full expression can supply a later read.
Same-expression operands are not ordered by this analysis. Every expression's
possible writes/calls are accounted for before and after visiting its operands;
an expression that may modify an input cannot publish a reusable value for it.
This avoids depending on the backend's operand/argument evaluation order.

Writes invalidate the entire affected named mutable object, even for different
indices. Unknown pointer stores, calls and volatile effects invalidate mutable
memory facts. Immutable objects can survive those barriers only while their
private index inputs remain unchanged. Index assignments invalidate dependent
facts; escaped indices are excluded. Branch joins retain only dominating facts
available on all continuing paths. Loop entries/exits invalidate modified inputs
and objects; captures inside a loop remain per-iteration. Continue edges cannot
consume a capture that their path bypassed. Zero-trip loops add no reads.

The comparison phase rewrites equivalent typed comparisons in a common form.
It can reuse swapped strict operators, exact complements, and facts proven on a
branch. Signedness and operand types are part of identity. Expensive repeated
predicates can receive private boolean homes; cheap comparisons use branch facts
without paying for a capture. Opposite strict orders such as `a<b` and `a>b`
remain distinct, preserving the equality case. Writes invalidate predicate inputs
under the same rules as value inputs.

Selection is bounded to eight private captures per function. Ordinary dynamic
mutable reads need three structural uses; immutable reads need two. A simple current-loop
induction subscript needs five because its address is often already retained in
X/Y. Earlier trials that cached those cheap reads added frame traffic and were
rejected in favor of the measured rule. Fixed displacements are left alone.
The existing body/strength disabling flags also disable this pass.

## BouncingSprites results

Average work over 600 logical updates, excluding startup and VBlank waiting:

| Build | Baseline clocks | New clocks | New ms | Fewer work clocks |
| --- | ---: | ---: | ---: | ---: |
| FastROM | 234,587.32 | 231,158.00 | 10.762913 | 1.4619% |
| SlowROM | 278,831.43 | 274,783.19 | 12.794138 | 1.4519% |

Two fresh runs per speed agree exactly. Both remain at 600 logical updates in
600 physical frames. Maximum update work is 241,522 FastROM and 287,210 SlowROM
clocks. Including waits, averages are 357,365.90 and 357,365.87 clocks respectively.
Milliseconds use 21,477,272 master clocks per second.

| Category | Baseline bytes | New bytes | Change |
| --- | ---: | ---: | ---: |
| Application and shared support code | 4,833 | 4,827 | -6 |
| Runtime code | 3,460 | 3,460 | 0 |
| Total linked code | 8,293 | 8,287 | -6 |
| Constants | 4,520 | 4,520 | 0 |
| Initialized data | 64 | 64 | 0 |
| Padded ROM | 65,536 | 65,536 | 0 |
| Main's allocated frame | 30 | 40 | +10 |

Main shrinks 2,945 -> 2,939 code bytes; gradient remains 241 bytes. The stack
tradeoff is explicit: five private captures require ten additional frame bytes.
This is the main frame allocation, not a measured whole-program stack watermark.

Main selects five memory captures and no predicate captures/folds. SX/SY named
references fall from 28 to 26 each, and ROM size-table references from eight to
five. Mutable coordinate captures are invalidated by position writes and never
carried as stale state across collision iterations. The source already places the
outer sprite size outside the inner loop; this change does not claim a new hoist
of that value. Predicate reuse is validated by the general fixtures, rather than
claimed for BouncingSprites' distinct strict-order checks.

All staged C, shared headers and asset bytes match baseline. Startup/runtime,
separate translation units, ABI, ROM speeds, NTSC emulator configuration and
measurement interval retain the previous contracts. Disabling this pass produces
byte-identical baseline assembly for both C units at identical input paths.

Every update matches positions/velocities, full OAM shadow, HDMA table and phase.
All four state sequences retain SHA-256
`0bad2bb9b559eb75c14a74746e26f6122a74175e2d3291d8deb1742b5576fd1d`.
Final screenshots match baseline pixels, RGB SHA-256
`31f30fb3c18a97acbb3e58b3b7d8341e3289865420afda2a34fff77933192b5a`.

## Focused verification and retained evidence

The registered `value-reuse` part passes in selected, disabled, no-line-pass,
no-inline and no-retention modes, plus an MSVC /Od reference. Its 128 opaque
inputs cover mutable/immutable arrays, distinct-object writes, mutation through
named arrays and pointers, calls, escaped/changed indices, conditional dominance,
zero-trip loops, continue/break and backedges, member arrays, same-expression
operands and calls in unordered operands. Predicates cover complements, swapped strict
operators, equality, operand mutation and mixed signed/unsigned semantics.
Assembly assertions require actual memory/predicate selection, fewer repeated
comparisons, fewer immutable loads, and all three direct volatile-array reads.

Existing focused parts passed unchanged: body-codegen, inlining, source-lto,
indexed-operands, index-retention, known-values, private-regions, store-fusion,
arithmetic-regions, volatile, multidimensional and scalar-values. The latter
includes NTSC/PAL hardware and instruction-boundary software interrupts. The
compiler remained unchanged throughout these checks and the final measurements.

`build/value-reuse/results.json` records frozen/current compiler/source hashes,
baseline identity, disabled controls, matching staged-input hashes, sizes/frame
allocations, focused results and repeated timing/state/pixel results.
`final-build/` retains staged sources, assembly, maps and ROMs; `final-timing/`
retains four sets of Lua scripts, expected states, logs and screenshots. `control/` retains exact assembly
comparisons and `focused/` the twelve existing part logs. Earlier cost-selection
trials remain in separate directories.

```text
cmd.exe /d /c tools\build-compiler.cmd
python tests/check-compiler.py --part value-reuse
```

Use fresh paths and repeat timing for FastROM run 2 and SlowROM runs 1/2.
