# Tiny frames and integer operation widths

For functions that need only two or four bytes of local stack space, pushing a register can reserve that space and save an incoming argument at the same time. The compiler also selects integer helpers that match the width of the calculation.

The subsequent [general word-expression investigation](word-expression-optimization.md)
adds constant-multiply recipes and frame-free pure arithmetic returns on top of
this work. The measurements below describe the preceding width/frame change.

Investigation dated 2026-11-06. The baseline includes the earlier frame and accumulator changes. These follow-up changes are unconditional defaults, with no compiler/build opt-in. The shared integer runtime size increase is accepted in favor of faster general operations.

## Tiny-frame selection

Frames with at most four local bytes use pushes to allocate their homes. The incoming first word parameter in X is pushed directly into home +1; a second word parameter in A fills home +3. Other homes receive arbitrary initial contents until C initializes them. TSC/TAY retains the ordinary Y-relative layout. Stack arguments are still remapped against the final frame size.

For a two-byte factorial frame this is `PHY; PHX; TSC; TAY`. It initializes the parameter home while allocating it. Direct TSX/TXS adjustment would first overwrite the incoming argument in X. Returning a word can discard a two-byte home with PLX, then restore caller Y with PLY. A four-byte home takes two pulls. Wide returns discard homes with PLY so A/X remain intact, then restore caller Y with the final PLY. Tiny wide frames therefore need no return staging slot. Larger frames retain the previous allocation/restoration strategy. Expression/argument spills are balanced before the epilogue.

A frame load can also reuse A from a preceding matching load/store across PHA and source comments: PHA preserves A/N/Z and S movement does not change a Y-relative address. A store still requires a producer with valid full-word N/Z. Labels, calls, mode changes and other instructions stop the reuse.

## Width-specific arithmetic

| Operation | Selected implementation |
| --- | --- |
| Proven unsigned byte multiply | `__mul8`: one full 8x8-to-16 hardware product |
| Word multiply | `__mul16`: three byte products, 00/10/01, producing the low sixteen bits |
| Long multiply | Existing `__mul32`: ten byte products contributing below bit 32 |
| Proven unsigned byte divide/modulo | `__udiv8` / `__umod8`: direct hardware path |
| Unsigned word divide/modulo | `__udiv16` / `__umod16`: one hardware operation for byte divisors, otherwise 16-step restoring division |
| Signed word/byte divide/modulo | `__sdiv16` / `__smod16`; magnitude division plus C quotient/remainder signs |
| Long divide/modulo | Existing signed/unsigned 32-bit routines and their hardware fast path |

Byte selection proves that both inputs are nonnegative byte values, including unsigned char objects, suitable constants and value-preserving word casts. Signed-char casts stop that proof. C promotes bytes to the target 16-bit int: a byte product can need all sixteen result bits, and signed-byte -128 / -1 must return 128. Signed multiplication can share the word low-product routine because its valid result has the same low-bit representation. Word staging no longer writes unused upper operand words. Quotient/remainder reuse stores word pairs in four private frame bytes and long pairs in eight; signed paired helpers normalize both results.

The expanded probes also exposed the old direct-operand selector stripping a word signedness cast before a wider use. That could zero-extend `(int)unsigned_word` when long sign extension was required. Such casts now use the normal conversion path. Regression cases cover word/long arithmetic and comparisons, unsigned-to-signed byte casts, signed-byte division and negative remainders. The old baseline fails the supplemental negative-word cast probe, so no speed ratio is claimed for that incorrect execution.

## Current factorial

The C source is unchanged. The base-case guard still returns before frame creation. The recursive path is now:

```asm
    phy
    phx                     ; allocate and initialize n at +1
    tsc
    tay
    lda a:$0001,y
    pha                     ; preserve n across the recursive call
    sec
    sbc #$0001
    tax
    jsr .loword(_factorial)
    sta z:__arith_rhs
    pla
    sta z:__arith_lhs
    jsr .loword(__mul16)
    plx                     ; discard n home, preserving result A
    ply
    rts
```

Factorial shrinks from 62 to 43 bytes. Fibonacci shrinks from 62 to 52 bytes. Their two-/four-byte C home layouts are unchanged from the frame and accumulator baseline. The number and order of recursive calls remain unchanged.

## Matched performance

Times are SNES master clocks. Basic samples span main entry through its return. Calculator timing spans its first printf entry through return from the result printf. Every entry below has two fresh runs with identical timing and ROM hashes. All compared original samples return zero; calculator output remains result: 30. zicc uses FastROM bank $80; stock VBCC r2 uses its stock SlowROM bank $00, `-O3 -msfp4 -lms4 -lvc`. These are system comparisons.

| Workload | Frame and accumulator baseline | Tiny frames/PHA reuse | Final width paths | VBCC |
| --- | ---: | ---: | ---: | ---: |
| insertion_sort | 30,024 | 30,024 | 30,024 | 35,430 |
| string_processing | 13,122 | 13,122 | 13,122 | 25,152 |
| integer_operations | 26,350 | 26,350 | 26,350 | 202 |
| function_calls | 131,322 | 129,330 | 107,002 | 146,150 |
| integer_operations_runtime | 45,398 | 45,398 | 45,398 | 77,748 |
| calculator | 625,714 | 625,304 | 620,846 | 1,501,200 |

The function-call sample improves 18.52% below the baseline: the frame/PHA stage saves 1,992 clocks and width-specific arithmetic saves another 22,328. The original integer_operations is mostly folded away by VBCC; its 202 clocks do not represent runtime arithmetic throughput. The separately compiled runtime kernels retain actual arithmetic and remain unchanged in elapsed time.

## Bytes and the accepted runtime cost

The shared integer object grows from 805 to 1,034 code bytes, a 229-byte increase. Its original source from __mul32 onward is unchanged; new narrow entries precede it. The current link includes that entire object when any integer helper is needed. Thus a long-only workload can gain 229 bytes with unchanged speed. The user explicitly accepted this cost and requested unconditional availability.

Each cell is **total code / non-asset ROM bytes**. Code includes application, startup and runtime. Non-asset ROM also includes numeric tables, strings, headers, vectors and initialization images; graphics, RAM BSS and unused fill are excluded.

| Workload | Frame and accumulator baseline | Final | VBCC |
| --- | ---: | ---: | ---: |
| insertion_sort | 499 / 563 | 499 / 563 | 1,192 / 1,268 |
| string_processing | 504 / 607 | 504 / 607 | 1,317 / 1,430 |
| integer_operations | 1,420 / 1,484 | 1,649 / 1,713 | 552 / 628 |
| function_calls | 1,361 / 1,425 | 1,542 / 1,606 | 1,137 / 1,213 |
| integer_operations_runtime | 1,526 / 1,590 | 1,755 / 1,819 | 1,340 / 1,416 |
| calculator | 12,656 / 13,136 | 12,671 / 13,151 | 12,873 / 13,568 |

Application code in the function-call sample shrinks from 460 to 412 bytes. The runtime increase makes the whole sample grow by 181 non-asset bytes. Calculator application code shrinks from 612 to 590 bytes; reductions in its generated decimal runtime limit its total non-asset increase to 15 bytes. Sort/string samples import no integer helpers and pay no new runtime bytes.

## Validation and provenance

`tests/check-small-integers.py` exhausts all 65,536 unsigned-byte pairs and all 65,536 signed-byte pairs. Its word sweep covers every 16-bit dividend against rotating divisor boundaries, the boundary Cartesian set, and 4,096 seeded random pairs: 69,801 word vectors. Total coverage is 200,873 vectors, with division by zero and signed quotient overflow excluded from defined-result assertions. The driver verifies exact hardware operation counts, call/exit ABI, and minimum ALU read latency. Narrow-path verification poisons unused operand/remainder upper words. Each worker handles at most 4,096 vectors, retaining emitted C/assembly, ROM, scripts, logs, hashes and results.

The targeted frame checks cover pushed register parameters, incoming stack arguments, wide A/X returns, narrow byte returns, pointer results, recursion, control-flow barriers and the signed-cast regressions. The original 4,258-case 32-bit ALU checks and 3,712-case wide-codegen checks remain part of the full suite.

The final `make check` passed; its complete log is
`build/word-call-trial/check-final.log`. All fifty exhaustive batches match the
final comparison's compiler/runtime hashes and poison unused upper words.
Minimum observed result-read delays are 54 master clocks for multiplication
and 106 for division, above the required 48 and 96. Final validation also
includes the signed-cast widening case, quotient/remainder reuse, startup/ROM,
console/calculator, arrays, string/register/indexed loops, comparisons, strength
reduction, direct-page addressing, branch boundaries and 2,001 decimal round
trips plus fourteen boundary fixtures.

Matching 4,096-case supplemental byte probes show 23,167,422 -> 8,441,924 clocks for unsigned-byte arithmetic and 26,667,854 -> 14,941,676 for the selected signed-byte batch. These are whole-loop measurements with checks and instrumentation, not isolated helper timings. The negative-word baseline probe is a correctness failure, not a performance result.

Baseline, frame-only and final system evidence is retained in `build/word-call-trial/{before,frames-comparison,final}/`. Compiler and original runtime snapshots are in `build/word-call-trial/baseline/`. The intermediate narrow-runtime trial is in `build/word-call-trial/word/`. The supplemental byte timings are in `build/word-call-trial/{baseline-small,poison}/`. Manifests record compiler, integer-object/source, library, source and ROM hashes. The standard sample/calculator reports are refreshed for the final compiler.

- Baseline compiler SHA-256: `0a40440ee51b190376247604561cad73b393fd1c60a9b040b2c8dc6efe03d3aa`.
- Final compiler SHA-256: `04a63211e5670ad35feaf69a13c9189cb5d44f9a17aa5472e314562ef36e771b`.

```text
make check
```

Changes are uncommitted.
