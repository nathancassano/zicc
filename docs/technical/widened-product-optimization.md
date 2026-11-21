# Deferred long operands and full word products

When two 16-bit numbers are widened before multiplication, the compiler can still use their original widths to calculate the full product. It also avoids saving and reloading an operand in long expressions when evaluating the other operand first is safe.

The trial started from the word-expression compiler on 2026-11-06. An independent rebuild of the baseline emits byte-identical assembly for all six measured sample translation units. Baseline and candidate use their own integer runtime objects. Sources, VBCC libraries/reference ROM and other calculator runtime objects match by SHA-256. Structure/frontend files, their tests and all eight linker configs remain unchanged.

## General rules

For long `+`, `&`, `|` and `^`, a direct left operand can be loaded after a complex right operand. The right subtree must contain only integer arithmetic, casts, fixed memory accesses or literals. Calls, writes, increments and dynamic accesses prevent this selection. This removes a spill/reload of the left value without reassociating the arithmetic tree. Subtraction keeps its operand roles and normal lowering.

A long multiplication whose two operands originate as words uses `__mul16wide`. Widening casts are peeled to find the word source; word truncation and signedness casts remain intact. Each operand retains its own sign/zero extension, so signed, unsigned and mixed products are supported. Byte sources work through their normal word promotion. Each expression is evaluated once; effectful right expressions retain stack preservation of the left. Unproven wide operands retain `__mul32`.

The helper computes four unsigned byte partial products, then corrects the high result word by subtracting the opposite source word for each sign-extended negative input. It returns the full 32-bit result in A/X and preserves Y/D/DBR and index width. No opt-in flag is required. Shared integer runtime CODE grows from 1,034 to 1,180 bytes; the object still links as a whole.

## Timing comparison

All times are SNES master clocks from two fresh matching runs. zicc runs in FastROM bank $80; stock VBCC r2 uses SlowROM bank $00 with `-O3 -msfp4 -lms4 -lvc`. These are system comparisons. VBCC folds the constant integer sample; its 202 clocks do not represent arithmetic throughput. Calculator measures the first printf through return from the result printf; basic samples measure main entry through return.

| Workload | Before | After | VBCC |
| --- | ---: | ---: | ---: |
| insertion_sort | 30,024 | 30,024 | 35,430 |
| string_processing | 13,122 | 13,122 | 25,152 |
| integer_operations | 26,350 | 26,350 | 202 |
| function_calls | 105,648 | 104,004 | 146,150 |
| integer_operations_runtime | 45,398 | 45,398 | 77,748 |
| calculator | 619,534 | 619,534 | 1,501,200 |

`add_scaled` itself falls from **3,936 to 2,332 clocks (40.8% faster)** and **94 to 74 bytes**. VBCC emits a 61-byte out-of-line body but inlines the workload call, so there is no comparable isolated function time. The complete call sample is 1.56% faster; the 1,644-clock workload reduction includes caller address/alignment timing as well as the 1,604-clock callee reduction.

## Code and non-asset bytes

Each cell is **all code / non-asset ROM**, in bytes. All code includes startup and linked helpers. Non-asset ROM adds numeric tables, strings, initialized data, header and vectors; graphics assets and unused fill are excluded.

| Workload | Before | After | VBCC |
| --- | ---: | ---: | ---: |
| insertion_sort | 499 / 563 | 499 / 563 | 1,192 / 1,268 |
| string_processing | 504 / 607 | 504 / 607 | 1,317 / 1,430 |
| integer_operations | 1,649 / 1,713 | 1,795 / 1,859 | 552 / 628 |
| function_calls | 1,494 / 1,558 | 1,620 / 1,684 | 1,137 / 1,213 |
| integer_operations_runtime | 1,755 / 1,819 | 1,901 / 1,965 | 1,340 / 1,416 |
| calculator | 12,669 / 13,149 | 12,757 / 13,237 | 12,873 / 13,568 |

The function-call sample application code is **364 -> 344 bytes**, versus **550** for VBCC. Its total code/non-asset ROM each grow by **126 bytes**: 146 bytes of shared runtime minus 20 application bytes. Calculator saves 58 generated code bytes, giving a net growth of 88 bytes. Samples that link the integer runtime without using these opportunities grow by 146 bytes; samples without it are unchanged. ROM file sizes stay 32,768 bytes for zicc and 163,840 for stock VBCC.

## Current add_scaled assembly

```c
unsigned long add_scaled(unsigned long base, int amount, int scale)
{
    return base + (unsigned long)amount * (unsigned long)scale;
}
```

```asm
_add_scaled:
    sta z:__arith_rhs
    phy
    tsc
    sec
    sbc #$000A
    tcs
    tay
    lda z:__arith_rhs
    sta a:$0005,y
    ldx #$0000
    cmp #$8000
    bcc cg_function_calls_relax_anon_5
    ldx #$FFFF
cg_function_calls_relax_anon_5 = *
    sta z:__arith_lhs
    stx z:__arith_lhs+2
    lda a:$0013,y
    ldx #$0000
    cmp #$8000
    bcc cg_function_calls_relax_anon_6
    ldx #$FFFF
cg_function_calls_relax_anon_6 = *
    sta z:__arith_rhs
    stx z:__arith_rhs+2
    jsr .loword(__mul16wide)
    clc
    adc a:$000F,y
    pha
    txa
    adc a:$0011,y
    tax
    pla
return_add_scaled = *
    sta a:$0009,y
    tya
    clc
    adc #$0008
    tcs
    pla
    ply
    rts
```

The existing ten-byte frame remains. `amount` is already in A after its home store. The product returns in A/X, and the two base words feed ADC directly; neither operand is spilled around the helper. Sign extensions are still required by the original signed int sources.

## Validation and reproduction

`tests/check-widened-products.py` checks 4,217 boundary/random vectors and 59,038 selected products against Python results. It covers every signedness pairing, full high results, byte truncation, casts from genuine longs, nonzero base high words, nested arithmetic, fixed struct/array accesses, all four deferred operations, one-time calls and preservation of a load across a mutating call. A true long multiplication must retain its full helper. Target checks cover final ABI/stack state and hardware latency (minimum 54 clocks, at least the required 48). It is part of `make check`.

Full `make check` passed, including 200,873 byte/word arithmetic vectors, 4,258 long hardware cases, 3,712 wide-codegen vectors, 123,600 word-expression results, structure/member checks, loop/comparison tests and 2,001 decimal pairs plus 14 boundaries. The complete suite log is `build/scaled-trial/check.log`. Baseline/candidate manifests, commands, sources, assembly, ROMs, maps, per-function CSVs and two-run profiler records are under `build/scaled-trial/{baseline,candidate}/comparison/`. The normal sample and calculator reports are refreshed as well.

```text
python tests/check-widened-products.py
make check
```
