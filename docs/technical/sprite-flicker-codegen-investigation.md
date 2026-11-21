# Sprite flicker code-generation investigation

Dragon's sprite code spent time on repeated address calculations, division by small powers of two, and an extra scan of the sprite list. This investigation traced that work to the C code and to compiler rules that missed these cases. The later [implementation and verification](sprite-flicker-optimizations.md) reports the fixes and repeated FastROM timings.

Investigated on 2026-11-11 with the compiler that added curated debugger symbols and Dragon's normal
production FastROM. This is an investigation: no compiler, runtime or game
implementation was changed.

The result is a combination of missing optimization coverage, existing passes
that do not reach these expressions, and a C implementation that performs an
additional sorted-pool scan. It is not a disabled-optimization build, and it
is not evidence of a regression relative to the former assembly.

## Findings

| Work in the current output | Classification | Owning implementation |
| --- | --- | --- |
| `i / 4` and `i % 4` call a division helper | Power-of-two division/remainder reduction is not implemented | `src/codegen.inc`, `binary_after_left` / `binary_loaded`; `src/divmod.inc` |
| A mask with shift count 0, 2, 4 or 6 calls `__shl32` | Variable word/byte shift selection and bounded mask-table synthesis are not implemented | `src/codegen.inc`, `binary_operands` / `binary_loaded`; `src/word_expr.inc`, `word_supported` |
| A discarded loop-step `i++` saves and restores its old value | Existing discarded-update optimization is bypassed by the loop emitter | `src/codegen.inc`, `emit_statements` / `emit_loop_body` / `emit_discarded` |
| `i * 4 + 1` is calculated twice per hidden sprite | Existing address normalization/reuse does not visit the enclosing loop/guard | `src/body_opt.inc`, `body_address_cse` / `body_reuse_addresses` |
| Runtime-bounded sprite loops repeatedly reload indices and switch accumulator width | Register/byte loop support exists, but does not cover this conditional multi-array shape | `src/index_retention.inc`, `retained_loop`; `src/register_loops.inc`; `src/byte_regions.inc` |
| The 12-byte high-table loops stay byte copies with a width change pair per iteration | Copy widening/unrolling for this loop idiom is missing | `src/affine_loops.inc`, `affine_accesses`; `src/loop_unroll.inc`; `src/index_retention.inc` |
| Sorted objects have their groups tested in two loops | Present in the C source; combining it requires a C change or new interprocedural loop fusion | Dragon `src/sprite_flicker.c`, `sprite_flicker_patch_sorted` |

### Division is unnecessary, although division/remainder reuse works

For each hidden sorted entry, the compiler emits one `__udiv16` call and keeps
both quotient and remainder in compiler homes. The second expression reuses
the remainder. Compiling with `--no-divmod-reuse` adds a separate `__umod16`
call.

The problem is earlier than reuse: unsigned `/ 4` should be two logical right
shifts, and unsigned `% 4` should be `& 3`. The current constant arithmetic
selectors cover multiplication and constant shifts, but have no corresponding
division/remainder selector. `divmod_emit` runs before the ordinary binary
selectors and unconditionally selects a helper for a cached pair; changing
only a later selector would therefore leave this paired case unfixed. Signed
division must preserve truncation toward zero; it cannot generally use the
same unadjusted shift as unsigned division.

Opaque-parameter compile probes confirm the distinction:

| Probe | Current output |
| --- | --- |
| `unsigned i / 4` | `__udiv16` |
| `unsigned i % 4` | `__umod16` |
| Both expressions in one function | One `__udiv16`, with remainder reuse |
| `unsigned i >> 2` | Two `LSR A`, no helper |
| `unsigned i & 3` | `AND #$0003`, no helper |

There is also one signed division per active prepare, even with empty pools.
The fireball endpoint is a difference of `fireball_t *` pointers: conversion
from a byte difference to an element count divides by `sizeof(fireball_t)`
(four) before the macro's outer unsigned cast. That emits `__sdiv16`, which
calls `__udiv16`. This has lower priority than the per-entry sorted work.

For divisor four, `__udiv16` uses the SNES hardware division path; this is not
the large-divisor software loop. Hardware setup, waiting, calls and staging
still do unnecessary work compared with shifts and a mask.

### A small variable mask becomes a 32-bit operation

The expression `2 << ((i % 4) * 2)` has a 16-bit `int` result on this target.
Its shift count can only be 0, 2, 4 or 6, and its result fits in a byte. However,
`binary_operands` deliberately widens word shifts to the existing long-helper
ABI when the constant-shift fast paths cannot handle them. `word_supported`
accepts only constant shift counts, so the variable expression calls `__shl32`.
This widening is a backend choice, not a requirement of C integer promotion.

Changing only `% 4` to `& 3` removes the division but retains `__shl32`. A
diagnostic C lookup with the four masks `$fd,$f7,$df,$7f` removes both helper
calls. Those compile probes show available selection, not a measured speedup
or a production source recommendation.

A smaller existing peephole also misses here. The emitted widening of literal
2 contains `LDA #2; LDX #0; CMP #$8000; BCC ...; LDX #$ffff`. The branch has a
known outcome, but `lp_const_branches` recognizes an immediately following
comparison; the intervening `LDX` blocks it. Removing that branch would only
trim setup, leaving the more expensive variable-shift helper.

### The loop step takes the wrong discarded-value path

An ordinary expression statement `i++;` has specific word-update handling in
`emit_statements`. A private direct-page home can become `INC home` without
producing the old value.

The fallback `for` emitter instead tries `strength_update`,
`scalar_home_update` and the far-update paths, then calls `emit_discarded` for
the step. `scalar_home_update` accepts compound assignments, not `EX_POST`.
`emit_discarded` has a special byte increment path but lacks the equivalent
word path, so it reaches the ordinary value-producing `EX_POST` emitter.

The patch loops consequently do:

```asm
lda index_home
pha
inc a
sta index_home
pla
```

Restore's promoted Y home produces:

```asm
tya
pha
inc a
tay
pla
```

The old accumulator value has no C consumer. Existing `lp_y_forms` can turn
an adjacent `TYA; INC A; TAY` into `INY`, but the unnecessary stack operations
prevent that match. Compile probes reproduce the difference between an
ordinary increment statement, a postfix loop step, and an `i += 1` loop step.
This is a concrete missed application of already implemented behavior.

### Address reuse stops outside the actual hot body

The small patch loop separately evaluates `s_oam[i * 4 + 1]` for the Y backup
and the subsequent store of 240. Each evaluation contains two shifts, carry
setup, addition of one and a transfer to X. It also preserves X around loads
and stores rather than retaining both useful displacements as in the reference.

Address CSE exists, but `body_address_cse` recursively visits `ST_BLOCK` only.
It does not descend into `ST_FOR` or `ST_IF` bodies; those statements are then
skipped as candidates. The current references are inside both constructs.

The diagnostic `address_straight` probe shares the address and computes the
scale once. Wrapping the same two statements in `if (saved)` leaves two full
calculations in `address_guarded`. Address normalization also belongs to this
walk. Extending it needs cost and register-pressure review: materializing a
pointer is not automatically better than retaining the original symbolic
indexed address.

### Existing loop optimizations do not provide the reference's register plan

`retained_loop` requires a constant right-hand loop bound. Both patch helpers
use runtime `end`; restore uses the runtime global backup count. These fail
that eligibility check before a retained X/Y plan is attempted.

The separate byte/register-loop selector handles narrower pointer/indexed
loop forms. Its ordinary loop body accepts straight expression statements;
the flicker body has a conditional, a shared count update and several arrays
with different indices. The byte-region selector covers copies and selected
signed comparisons against zero, not the full byte equality, backup and
counter region here. There is no general register allocator that recreates
`X = slot`, `Y = slot * 4` and borrows X for the backup index.

What does apply today:

- Direct symbolic indexed operands, instead of a completely general pointer
  calculation for every array access
- A saved direct-page countdown for both patch loops, while maintaining the
  separate C index
- Late Y promotion for the backup temporary or restore index
- X retention for each fixed-bound 12-byte high-table copy
- The normal ROM builder's additional accumulator-width cleanup

Disabling register-loop selection leaves these functions' selected instruction
streams unchanged. Disabling index retention changes the two high-table copy
loops, but does not change either patch helper. Disabling direct-page counters
changes the patch loops, confirming that this fallback optimization is active.

The high-table loops retain their byte load/store pair, with `SEP` and `REP`
inside the loop. The existing affine unroller requires a suitable running
address plan; these simple one-level indexed byte copies do not receive one.
No pass widens them into the reference restore's six unrolled word copies.
The diagnostic `memcpy(..., 12)` probe still calls the library, so spelling the
copy as `memcpy` alone does not establish that it becomes those six copies.

## Confirmed runtime work and current timings

The production fixture was rerun on the current ROM with additional execution
callbacks at the real helper entries and the two group-load instructions.
The callbacks capture counts at prepare's return and append them to the
existing timing sample line. They add no SNES instructions. Every one of the
416 samples matched the expected helper and scan counts, alongside the
fixture's 53,248 slot checks, high-table checks and maximum 128 backups.

| Case | Small-loop group tests | Second sorted-loop tests | `__udiv16` entries | `__shl32` entries |
| --- | ---: | ---: | ---: | ---: |
| active_empty | 0 | 0 | 1 | 0 |
| sorted_full | 48 | 48 | 49 | 48 |
| all_full_mixed | 128 | 48 | 17 | 16 |
| all_full_kept / all_full_player | 128 | 48 | 1 | 0 |
| all_full_hidden | 128 | 48 | 49 | 48 |

Each active row also has one `__sdiv16` entry. Its nested `__udiv16` entry is
already included in the table, so 49 means 48 mask divisions plus that one
endpoint division, not 49 independent mask operations. Inactive/probe/recovery
rows execute none of these helpers or group tests.

The full retained pool therefore performs 176 group comparisons for 128
sprites, despite saving none. The C sorted helper first calls the small
helper, then scans its range again to clear size bits. The reference fuses
these actions into one loop. No implemented interprocedural loop-fusion pass
combines the C loops. This source-level difference remains even after local
instruction selection improves.

Fresh worst-sample frame shares remain 26.03% retained/player, 52.86% mixed,
62.07% sorted-only hidden, and 105.26% all hidden. All 32 all-hidden samples
include an interrupt. Small differences from the supplied table are fresh
refresh/interrupt timing observations, not an optimization result.

The timing boundaries remain entry through caller resumption, including return
and excluding the call; prepare includes helpers, and upload/wait is excluded.
Times include refresh stalls and interrupts. Percentages use 357,366 master
clocks per NTSC frame. Inputs remain synthetic rather than gameplay averages.

## Work order supported by this evidence

1. Add constant power-of-two division/remainder lowering, including the paired
   divmod selector and signed pointer-difference scaling where valid.
2. Add word/byte variable-shift selection or bounded mask lowering. Removing
   division alone leaves a shift helper for every hidden sorted entry.
3. Route discarded word loop steps through existing update selection, and
   extend nested address normalization/reuse without defeating indexed operands.
4. Extend runtime-bound conditional indexed loops and byte regions, including
   restore's gather/scatter pattern. This is needed to address the large
   retained/player scan cost as well as hidden sprites.
5. Combine the sorted work in C if desired, and recognize fixed small byte-copy
   widening. These complement compiler improvements; they do not replace them.

No speedup for these changes has been measured here. In particular, the
reference assembly was not assembled or benchmarked. Its VASM sections,
imports, directives, stack argument locations, register/status saves and RTL
belong to the older ABI. The current build passes the first two word arguments
in X/A and uses same-bank JSR/RTS. Its `for (i = first; i < end; i++)` also
handles `first > end` differently from the reference's equality-only loop.
The reference is useful as a register/data-flow target, not a drop-in binary
or a proved timing baseline for the current ABI.

## Evidence and reproduction

Complete evidence is in `build/flicker-codegen-20261111-complete/`:

- `audit.json`: input/compiler/pass hashes, selected-allocation stage,
  four-function instruction-stream matches, compile commands, annotations,
  calls/opcodes and all helper/scan count assertions
- `inputs/`: frozen game C/headers, supplied reference, selected production
  assembly and allocation manifest
- `production-*.s` and `production-*.builder.s`: default output plus six
  optimization-disable controls, before and after the normal builder width pass
- `probes.c` and `probes-*.s`: 19 opaque-parameter or external-array diagnostic
  functions with three compilation controls; these are assembly investigations,
  not runtime throughput measurements
- `production-instrumented/`: frozen ROM/symbol companions, generated Lua,
  full raw log, timings, original fixture summary and `helper-counts.json`

The current ROM is SHA-256
`d1cbbddb7ebba611483ad80f797c79c2b8971ecfe2e69ac50329f67908c07962`.
The compiler executable is SHA-256
`324f2c1518d1c730df88448606117f883230cc72d905ec7da7491a8bc6c2ac17`.
The flicker C source is SHA-256
`6ae10b5b2f9d9950a023c4e01ba5ac94cb49ee67594723300b0444b61601fb26`.

Fresh compilation matches all four investigated production functions after
applying the normal builder width pass and normalizing allocator address
wrappers. The production allocation manifest agrees with the compiler binary
and flicker source hashes. Compiler and ROM hashes were checked again at the
end of the audit.

The investigation tool read the selected stage from the production allocation
manifest. Its instrumentation asserted the instruction shape and helper
selection for this baseline. Generated variants and evidence were kept in a
separate output directory.

No `make check` was needed for this investigation: compiler/code-generation
implementation and runtime inputs were unchanged. The reproduction tool and
documentation were added; the current production behavior was exercised by
the full flicker fixture.
