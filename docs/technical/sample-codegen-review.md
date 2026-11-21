# Sample code-generation review (2026-11-07)

This review traces which instructions each sample ran in the baseline build
identified below. Later measurements with the
[direct-page and cursor optimizations](operations.md#direct-page-homes-and-register-cursors)
reported 20,124 FastROM clocks for insertion_sort versus the baseline's 30,008
and about 28,203 clocks/run for Dhrystone versus 28,779.

Every finite sample was compiled with the saved zicc build (`zicc.exe`
SHA-256 `4c574d51…68ec`) through the
normal HiROM `tools/build-rom.py` pipeline. Each was traced in Mesen from `main`
entry to its return, with an execution count and master-clock cost recorded for
every executed instruction. The same sources were also built with stock VBCC
from `C:\snesdev\vbcc65816_r2`: the unmodified web-release binaries, `-O3`, the
stock startup and `libvc`. No custom VBCC tree was used. The emitted assembly
was then read against the C source, and the two hottest functions were rewritten
by hand as "ideal" code under the existing ABI and measured in the same harness.

## Measured totals (master clocks, main entry → return)

| Case | zicc FastROM | zicc SlowROM | VBCC SlowROM | zicc/VBCC (Slow) | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| insertion_sort | 30,008 | 35,124 | 35,430 | 0.99 | VBCC inlines the sort into main |
| string_processing | 12,736 | 15,192 | 25,152 | 0.60 | |
| integer_operations | 26,642 | 30,830 | 202 | - | **VBCC constant-folds everything**; not a throughput figure |
| function_calls | 104,350 | 120,190 | 146,150 | 0.82 | |
| structures_and_tables | 14,452 | 17,292 | 7,652 | 2.26 | VBCC inlines and partly folds the const table |
| integer_runtime (split kernels) | 45,762 | 52,670 | 77,748 | 0.68 | all 12 kernels hooked and verified |
| structures_runtime (split kernels) | 15,690 | 18,668 | 26,012 | 0.72 | both kernels hooked and verified |
| **insertion_sort, ideal kernel** | **13,468** | **15,860** | | | hand-written `_insertion_sort` only |
| **function_calls, ideal fibonacci** | **71,718** | **82,516** | | | hand-written `_fibonacci` only |

The SlowROM column is the identical zicc ROM with its single MEMSEL write
(`sta f:$00420D`) replaced by NOPs, so it compares code generation at VBCC's memory
speed. Both zicc runs execute the same instruction counts at every address.
Every row is two fresh emulator processes with identical results, and every
program returns 0. Remaining target differences: zicc uses JSR, register
arguments and HiROM, with DBR=$7E and 24-bit `__far`. VBCC uses JSL, DP
pseudo-registers and LoROM bank $00, and keeps its own predefined 24-bit
`__far`. VBCC is compiled with `-D__ZICC__=1`, which only skips the samples'
`#define __far` fallback that collides with VBCC's built-in definition.

Ideal kernels pass all of the sample's own checks. They do the same work:
`fibonacci` is entered 217 times in both versions, and the sort runs the same
comparisons. Their size also drops: `insertion_sort` from 194 to 83 bytes and
`fibonacci` from 52 to 26 bytes.

## Where the time goes

| Case | Largest zicc cost | Share |
| --- | --- | ---: |
| insertion_sort | `_insertion_sort` frame-slot traffic (`lda/sta a:$nn,y`) | 93% |
| function_calls | `_fibonacci` frame setup/teardown per call (217 calls) | 84% |
| integer_operations | `udiv32_software` dividing two known constants | 54% |
| integer_runtime | `udiv32_software` (divisor `$1234` is above 255) | 63% |
| structures_* | `__mul16x32` (≈2,150 clocks per multiply) | 55–59% |
| string_processing | already near-ideal loops; residue is in `main` | - |

## Code-generation findings

### 1. Loop scalars in registers and direct page

In the baseline, locals in framed functions lived at `a:$nn,y`. That is
40 master clocks per 16-bit access in FastROM, against 28 for `z:` and 12 for a
register. `insertion_sort` keeps `i`, `j`, `value` and two cursors there and
reloads them on every use. It also maintains both `j` and the strength-reduced
cursor for `values[j]`, although `j` is used only in `j > 0`.

Baseline inner loop (per comparison step, ~14 instructions, ~550 clocks):

```asm
    lda a:$0007,y      ; j
    sec
    sbc #$0000         ; j > 0 ?
    beq done
    bvc :+
    eor #$8000
:   bmi done
    ldx a:$000D,y      ; cursor &values[j]
    dex
    dex
    lda a:$0000,x
    sec
    sbc a:$0009,y      ; value
    ...
    lda a:$0007,y      ; --j
    dec a
    sta a:$0007,y
    lda a:$000D,y      ; cursor -= 2
    dec a
    dec a
    sta a:$000D,y
```

In the hand-written comparison, X holds `&values[j-1]` for the inner loop.
Y holds the outer cursor and is saved once. `value`, the end pointer and the `&values[-1]` stop
pointer go in call-clobbered `$E0–$E7`, and `j > 0` becomes a pointer compare:

```asm
@inner:
    cpx z:$E6          ; j > 0  <=>  &values[j-1] != &values[-1]
    beq @place
    lda a:$0000,x
    sec
    sbc z:$E4          ; values[j-1] > value (signed)
    beq @place
    bvc :+
    eor #$8000
:   bmi @place
    lda a:$0000,x
    sta a:$0002,x      ; values[j] = values[j-1]
    dex
    dex
    bra @inner
```

Measured: the `_insertion_sort` kernel drops from 28,028 to 11,488 clocks
(−59%), and the whole program from 30,008 to 13,468.

The baseline's frame also explains the overhead in `inventory_value`. With Y
as the frame register, each far element access uses
`phy; ldy #k; lda [p],y; …; ply`.

### 2. Frameless calls: stack-relative temporaries and argument-register reuse

`fibonacci` runs `phy; pha; phx; tsc; tay` on entry and `plx; plx; ply` on
exit, and reloads `n` from its home with `lda a:$0001,y`, even though X still
holds `n`. Ideal:

```asm
_fibonacci:
    txa
    sec
    sbc #$0002          ; n - 2, reused below
    bvs @leaf           ; n - c overflows only when n < c for positive c
    bmi @leaf
    pha                 ; save n-2
    dex                 ; n-1 from the live argument
    jsr .loword(_fibonacci)
    plx                 ; X = n-2
    pha                 ; left
    jsr .loword(_fibonacci)
    clc
    adc 1,s
    plx
    rts
@leaf:
    txa
    rts
```

Measured: `_fibonacci` drops from 87,288 to 54,656 clocks (−37%), and the whole
program from 104,350 to 71,718.

### 3. Constant propagation through non-escaping scalar locals

`integer_operations` stores each constant initialiser into the frame, reloads
it, and then runs `__udiv32` and `__sdivmod32` at runtime on operands it knows
(about 15k clocks). It even evaluates `-32767 - 1` as `lda #$8001; sec; sbc #1`.
The same gap appears elsewhere:

- `function_calls`: `saved != 1234` compiles to `lda #$04D2; cmp #$04D2`.
- `string_processing`: the `bytes[]` checks reload three just-stored constants.

VBCC folds all of these, reducing `main` to 202 clocks through whole-program
constant folding.

### 4. Peepholes found in every sample

| Baseline pattern | Equivalent instruction sequence | Seen in |
| --- | --- | --- |
| `sta n,y` then `lda n,y` (same value still in A/X) | drop the reload | function_calls main, string_processing `length`, integer_operations div results (4 words stored and reloaded) |
| `sta lo,y; pha; txa; sta hi,y; pla` when A is dead afterwards | drop `pha/pla`; store immediates directly | integer_operations (3×), structures main |
| `lda x; pha; tyx; inx; pla` | `tyx; inx; lda x` (or no pha/pla) | string_processing (each `reverse_text` call) |
| `lda #k; and #$00FF; sep #$20; sta; rep #$20` ×3 | one `sep` region with three byte stores, or a 16-bit store for adjacent pairs | string_processing `bytes[]` |
| `lda m; and #$00FF; cmp #$0000; beq` | drop the `cmp` | string_processing |
| `lda v; sec; sbc #$0000; beq; bvc; eor; bmi` (compare with zero) | `lda v; beq; bmi` | insertion_sort `j > 0` |
| `jsr helper; rts` | `jmp helper` (tail call) | every `integer_kernels` wrapper |
| identical ROM string literals emitted twice | merge | string_processing (three pairs) |

### 5. Runtime helper costs

In the measured build, `__mul16x32` accounts for 55–59% of both structures
cases. `udiv32_software` accounts for 63% of `integer_runtime`.

## Comparison notes

VBCC ties `insertion_sort` despite poor code (redundant moves, long-indirect
`[r8]` through every pointer) because all of its locals live in DP
pseudo-registers. The hand-written direct-page version reduces that cost in
zicc. VBCC pays JSL/RTL, saves five callee-saved DP
registers per `fibonacci` call, and uses stack arguments. zicc's specialised
ROM-bank string loops in `string_processing` are better than VBCC's inlined
version.

## Evidence and reproduction

Everything is under `build/codegen-review/`:

- `trace_samples.py` (zicc) and `trace_vbcc.py` (stock VBCC) build, trace and
  verify the samples. Each run checks that the return is 0, that two runs give
  identical clocks, that the paged per-PC records sum to the instruction total,
  that every required kernel was called, and that FastROM and SlowROM execute
  the same instruction counts.
- `summary.json` and `vbcc/summary.json` hold totals and per-function
  clocks/instructions.
- `<case>/*.s.annotated` is the emitted assembly with per-line execution counts
  and clocks. `vbcc/<case>/hot-pcs.txt` and the VBCC `.s`/`.lst` files are the
  VBCC equivalents.
- `ideal/*.s.inc` are the hand-written bodies. `ideal/splice.py` splices one
  into the retained stage-1 assembly, relinks with the identical retained ld65
  command and traces it.
- `vbcc/toolchain.sha256` holds the release binary hashes (`vbcc65816.exe`
  `ebf43c73…98f9`) and `compiler.sha256` the zicc hash. Raw Mesen logs are in
  each `mesen/` subdirectory.

Run `python build/codegen-review/trace_samples.py` and
`python build/codegen-review/trace_vbcc.py` after `make all smoke`.
