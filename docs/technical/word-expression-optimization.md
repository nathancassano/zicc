# General word-expression optimization

For some 16-bit calculations, a few shifts and additions cost less than calling a multiplication routine. The compiler estimates that cost and can also evaluate a short arithmetic expression in registers and temporary memory.

Completed on 2026-11-06. The baseline compiler already supported structure layout and member access. The additional linker configurations did not alter compiler sources or the default `linker/lorom32.cfg`.

## General selection rules

`src/word_expr.inc` implements two independent selections. Neither looks for a function name, a particular coefficient list, or the shape of combine as a whole. Both are unconditional defaults.

1. A constant word multiplier is planned as a bounded binary shift/add recipe, a power-of-two-minus-one recipe, or a cheaper negated recipe. Selection compares conservative operation costs, including saving the original operand when needed, with a 32-cycle inline budget. Constants can appear on either side. The same recipes serve ordinary expression lowering and compound multiplication; the operand is evaluated once even for multiplication by zero. An expensive or non-word product retains its helper.
2. A side-effect-free word expression is planned into a small instruction list before any assembly is emitted. Its accumulator holds the current value; four existing caller-clobbered DP words provide temporary storage. A complex child can be evaluated before a direct operand of a commutative operation. Subtraction retains its operand roles and every subtree retains its original grouping. Initial parameter 0 stays available in X; parameter 1 stays in A until it must be saved for a future use. Temporary lifetimes allow the same scratch word to be reused across successive partial sums.

The planner accepts word add/subtract/bitwise operations, unary plus/minus/complement, bounded constant products, and valid constant shifts. It preserves signed versus unsigned right-shift behavior. It supports direct word objects, fixed array elements and fixed named structure members through the existing `fixed_memory_object` / `direct_operand` lowering. It does not duplicate the structure parser, layout or member-address logic.

A function with only an eligible word return and word parameters can omit the frame. Its first two parameters use X/A and later parameters retain their incoming stack homes. Parameters are remapped only after a complete plan succeeds, and their compiler offsets are restored afterward. The same expression planner also applies within ordinary framed functions.

Calls, stores, increments, comparisons/short-circuit control flow, dynamic indirection/member accesses, byte/wide values, and unsupported trees retain their established lowering. Constants around an effectful operand can still inline after that operand has been evaluated once. Scratch exhaustion or the 128-instruction limit discards the un-emitted plan and uses the normal backend. No reassociation across C subtrees is performed.

## Generated combine

The sample source is unchanged:

```c
int combine(int a, int b, int c, int d)
{
    return a + b * 2 + c * 3 + d * 4;
}
```

The general planner emits this 18-instruction, 27-byte leaf:

```asm
_combine:
    asl a
    stx z:__arith_lhs
    clc
    adc z:__arith_lhs
    sta z:__arith_lhs
    lda 3,s
    asl a
    clc
    adc 3,s
    clc
    adc z:__arith_lhs
    sta z:__arith_lhs
    lda 5,s
    asl a
    asl a
    clc
    adc z:__arith_lhs
    rts
```

It uses one scratch word and no frame, helper call, or explicit push/pull. Y, D and DBR remain untouched. Caller-owned stack arguments and the ordinary JSR/RTS return address retain their normal ABI behavior.

## Isolated steps

Times are SNES master clocks. The combine figures include its arithmetic helper in the baseline and are matched per-call profiler measurements. The whole call sample is dominated by unchanged recursive functions and invokes combine only once.

| Metric | Baseline | Constant recipes only | Recipes plus expression planner |
| --- | ---: | ---: | ---: |
| combine code bytes | 75 | 70 | 27 |
| combine clocks | 1,760 | 1,044 | 406 |
| function-call sample clocks | 107,002 | 106,286 | 105,648 |
| application code bytes | 412 | 407 | 364 |
| all code bytes | 1,542 | 1,537 | 1,494 |
| non-asset ROM bytes | 1,606 | 1,601 | 1,558 |

Combine is 76.93% faster (4.33x) and 48 bytes smaller. The full call sample improves 1.27%; its recursive call counts and results are unchanged. The integer runtime and its 1,034-byte code footprint are unchanged.

## Matched standard workloads

Each comparison uses two fresh emulator runs with identical clocks and ROM hashes. Basic samples span main entry through its return; calculator timing spans its first printf through return from the result printf, including console behavior. zicc runs in FastROM bank $80. Stock VBCC r2 uses bank-$00 SlowROM, `-O3 -msfp4 -lms4 -lvc`. The comparison retains those system differences.

| Workload | Baseline clocks | Final clocks | VBCC clocks |
| --- | ---: | ---: | ---: |
| insertion_sort | 30,024 | 30,024 | 35,430 |
| string_processing | 13,122 | 13,122 | 25,152 |
| integer_operations | 26,350 | 26,350 | 202 |
| function_calls | 107,002 | 105,648 | 146,150 |
| integer_operations_runtime | 45,398 | 45,398 | 77,748 |
| calculator | 620,846 | 619,534 | 1,501,200 |

The original integer_operations is mostly constant-folded by VBCC. The separately compiled integer_operations_runtime is the actual arithmetic-kernel workload; all twelve kernels are verified to execute. Calculator timings include polling/console effects, so its change is not a pure-computation speed claim.

Each byte cell below is **all code / non-asset ROM bytes**. Code includes application, startup and runtime. Non-asset ROM also includes tables, strings, headers, vectors and initialization images; graphics, RAM BSS and unused fill are excluded.

| Workload | Baseline | Final | VBCC |
| --- | ---: | ---: | ---: |
| insertion_sort | 499 / 563 | 499 / 563 | 1,192 / 1,268 |
| string_processing | 504 / 607 | 504 / 607 | 1,317 / 1,430 |
| integer_operations | 1,649 / 1,713 | 1,649 / 1,713 | 552 / 628 |
| function_calls | 1,542 / 1,606 | 1,494 / 1,558 | 1,137 / 1,213 |
| integer_operations_runtime | 1,755 / 1,819 | 1,755 / 1,819 | 1,340 / 1,416 |
| calculator | 12,671 / 13,151 | 12,669 / 13,149 | 12,873 / 13,568 |

## Independent expression validation

`tests/word-plan-driver.c` enumerates all 65,536 multiplier bit patterns with both operand-saving costs (131,072 candidate combinations). The selected 484 recipes pass 4,840 evaluations over boundary inputs, including the coefficient-one check for their linear map modulo 2^16. This checks recipes independently of the selection algorithm.

`tests/check-word-expressions.py` evaluates sixty differently named functions against Python results over 2,060 edge/deterministic-random eight-word vectors: 123,600 function results. It covers both constant operand orders, signed/unsigned modular products, repeated and late X/A inputs, eight parameters, signed and unsigned shifts with casts, subtraction grouping, bitwise trees, fixed structure fields, and deliberate scratch-exhaustion fallback. Separate effect checks require calls and member-address expressions to be evaluated once, including multiplication by zero, and check a destination selected before an RHS changes its root index. Wide multiplication retains its 32-bit helper.

The matched scalar validation workload takes 175,130,280 baseline clocks versus 64,319,800 after the change (2.72x). This includes callers and result checks, not just multiplication kernels. Its source and retained Lua input/expected-value tables match between versions.

## Integration and reproduction

The protected-file snapshots in build/expression-trial/protected.json and protected-linkers.json match: structure frontend sources, structure/member tests, integer runtime and all eight linker configs are unchanged. Both standard comparisons use the unchanged 32 KiB config. The three unrelated untracked Dhrystone files were not edited or included.

The full make check suite passed; its log is build/expression-trial/check.log.
This includes the existing struct layout tests, eight MSVC/Mesen member cases,
two plain member variants and 34 member diagnostics, as well as the 200,873
poisoned-upper-word arithmetic vectors, frame/ABI tests, wide arithmetic, arrays,
string/indexed/register loops, comparisons, strength reduction, branch boundaries
and decimal checks. The added expression and multiplier-recipe checks also pass.

- Baseline compiler SHA-256: `bfd38c7af13984af1c18e10588d76b7365e901bb877d4d2a1991a32bcae7db5e`.
- Final compiler SHA-256: `41161016e2cd8b31003fd9aa6fb6d9cb2e5bba082bd1950d7f952516c2a1fc1e`.

Evidence lives under `build/expression-trial/{before,scales-comparison,final}/`, with private compilers in baseline/scales/planner. The normal reports in docs/technical/basic-sample-comparison.md and docs/technical/comparison.md are refreshed. The added validation is part of make check.

```text
make check
python tests/check-word-expressions.py --compiler build/zicc.exe --output build/word-expression-check --expect-planner
```

Changes remain uncommitted.
