# PI: generated assembly and an ideal 65816 target

The pi sample runs the same inner loop over two million times. Saving even one
instruction inside it can matter. This report compares the assembly from
source LTO compiler (binary SHA-256
`5a925527ab6d2159415275f43b1b3e2c3cfdda76d971242a6203f17c184f2575`) for
the historical C kernel with a [handwritten version](pi-ideal-inner.s).
The handwritten loop was assembled for this study. The compiler and the
sample still use their regular builds and calculation.

Generated assembly is retained at
`build/pi/comparison/zicc-fast/sample-allocation/20261108T073532.147725Z/stage1/1_kernel.s`.
[The full-program measurements](pi-comparison.md) remain the accepted timings.

## What the C actually requires

The hot loop executes 2,407,552 times (2,687 positions times 896 passes):

```c
k = 2 * i - 1;
x = 10 * A[i - 1] + q * i;
q = divmodu(x, k);       /* aux = (u8)(x % k); q = (u8)(x / k) */
A[i - 1] = aux;
```

Each pass then divides the final q by ten and updates A[0]. Thus there are
2,408,448 logical divmod operations. Preserve unsigned 16-bit intermediate
wraparound, byte truncation of both quotient and stored remainder, and the
existing delayed-digit/carry behavior. The original algorithm's inaccurate
later digits must remain inaccurate in a semantics-preserving assembly target.

Useful facts follow from the C, without knowledge of the benchmark inputs:

- i descends from the fixed 2687 to 1; A's byte offset is i-1.
- k descends from 5373 to 1 in steps of two.
- q is zero-extended from a byte at every assignment, so q*i is byte*word.
- For k>=256, *any* unsigned 16-bit dividend has a quotient no larger than 255.
- A and aux are distinct, nonvolatile RAM objects. The stored byte can be
  forwarded directly to A without rereading aux.

The observed maximum quotient of 103 applies to this run. Arbitrary C inputs
can exceed it.

## What zicc already gets right

The static divmodu helper is inlined at both sites. Assembly explicitly marks
`divmod produce` followed by `divmod reuse`: `%` and `/` share one division.
There is no per-iteration C call frame for divmodu and no second division for
its quotient. Multiplication by ten uses shifts/addition. The inner scalar
homes move to direct page for the duration of the loop.

The remaining arithmetic helper calls are to __mul16 and __udiv16. Current
application code is 661 bytes: calculate_pi 625, main 16, print_digit 20.
The 30-byte calculate_pi local frame plus saved Y occupies 32 stack bytes,
excluding its return address and transient outgoing arguments.

## Where the hot loop loses work

| C operation | Current generated shape | Better general target |
| --- | --- | --- |
| A[i-1] load | Push A base, form i-1 in scratch, restore base, add, TAX, load/mask | Keep i-1 in X; load A,X |
| k=2*i-1 | Recompute and store a DP word each iteration | Keep k in Y, subtract two |
| q*i | Generic word*word helper, three hardware partial products | Byte*word low-product helper, two partial products |
| x temporary | Store, reload and copy into helper input | Keep result in A, store directly to input |
| quotient | Helper result -> clone temporary -> mask -> clone return -> q | Mask helper result and store q once |
| remainder | Helper result -> clone temporary -> aux -> reload/mask -> A | One byte value stored to aux and A |
| decrement/test | Load i, decrement, store, jump back, load, CMP #0, two branches | DEX/BPL after range-proven rebasing |
| region boundaries | Copy seven homes in and seven homes out, including dead/uninitialized temporaries | Initialize live-ins only; retain only live-out q |

The current loop has 153 static code bytes and 77 instruction statements.
For each nonzero iteration it executes 75 of those statements, excluding the
called helpers. Two header JMP instructions are skipped. Its unsigned CMP #0
makes the subsequent BCS always true; that carry test is redundant.

The two address constructions alone use 22 instruction statements per
iteration, before counting the final byte load/store and width controls.
Direct indexed addressing removes those constructions.

The region setup includes reading locals that are overwritten before use.
Those loads have no useful C value. On leaving the loop, k, x and inliner clone
homes are dead; their frame copies can also disappear. Their cost occurs only
896 times, so fixing the per-position work is the higher priority.

## Division cost and reference implementation

For i=129..2687, k>=256: 2,292,864 of the total 2,408,448 divisions take the
software path (95.2%). The other 115,584 can use the SNES 16/8 divider.
The hardware cannot directly divide a word by a word-sized divisor.

The existing software helper does 16 restoring-division steps, keeping both
shifted dividend and remainder in DP memory. But its existing k>=256 dispatch
already proves that the quotient fits a byte. Initialize the remainder with
x>>8, then consume only the eight low dividend bits. Keep the remainder in A:

```asm
; Large divisor path: L=dividend, R=divisor >=256, T=remainder
; Preserve caller X; Y is untouched
    phx
    lda z:L
    xba
    and #$00FF
    sta z:T
    lda z:L
    xba
    and #$FF00
    sta z:L
    lda z:T
    ldx #8
@bit:
    asl z:L
    rol a
    cmp z:R
    bcc @skip
    sbc z:R              ; CMP already supplied carry
    inc z:L
@skip:
    dex
    bne @bit
    sta z:T
    lda z:L
    plx
    rts
```

This is valid for all 16-bit dividends and divisors in 256..65535, not just
PI. Before each shift the already consumed dividend prefix fits 15 bits,
so the remainder cannot overflow a word. On completion L is the full quotient
and T the full remainder. The small-divisor path retains hardware division.
Preserving X enables the surrounding indexed loop.

## Ideal inner-loop shape

The reference saves the normal Y frame anchor once around this register region.
X is i-1; Y is k; Q and TEN are two private DP words beyond helper scratch.
Both helpers preserve X/Y. L/R/T use the existing arithmetic-helper scratch
contract. This keeps the original aux store on every iteration:

```asm
    phy
    ldx #2686
    ldy #5373
    stz z:Q
@loop:
    lda a:.loword(_A),x
    and #$00FF
    sta z:TEN
    asl a
    asl a
    clc
    adc z:TEN
    asl a
    sta z:TEN                ; 10*A[i-1]
    txa
    inc a
    sta z:R                  ; i
    lda z:Q
    sta z:L
    jsr mul_u8_u16_low
    clc
    adc z:TEN                ; wraps as the C word does
    sta z:L
    tya
    sta z:R                  ; k
    jsr divmod_u16           ; eight steps for large k, hardware for small k
    and #$00FF
    sta z:Q
    lda z:T
    sep #$20
    sta a:.loword(_aux)
    sta a:.loword(_A),x
    rep #$20
    dey
    dey
    dex
    bpl @loop
    lda z:Q
    ply
    rts
```

This is 32 hot-loop instructions and about 60 hot-loop bytes. The complete
standalone inner-pass function is 73 bytes; its mixed-width multiplier is 45
bytes and its divider, including the hardware launch routine, is 96 bytes.
These totals do not include outer digit handling, console calls or test adapters.
They must not be compared with 625 bytes as though both were entire functions.

Word loads followed by masking are appropriate here because A is known ordinary
RAM and the extra byte read is harmless; that choice does not generalize to
volatile/MMIO byte objects. The BPL exit depends on the fixed starting offset
2686. The reference preserves the aux stores.

## Measured breakdown and reference validation

A fresh NTSC FastROM run of the actual existing ROM stopped at the end of its
first inner pass. Entry/return hooks measured helper execution, including their
returns, while leaving instructions and source unchanged:

| First inner pass | Master clocks | Share |
| --- | ---: | ---: |
| __udiv16 bodies | 9,686,424 | 59.27% |
| __mul16 bodies | 1,749,434 | 10.71% |
| Caller body, loop control and call setup | 4,906,204 | 30.02% |
| Total | 16,342,062 | 100% |

There are exactly 2687 multiply and 2687 divide calls in that pass, including
2559 software divides and 128 hardware divides. The caller category includes
useful shifts/adds as well as addressing, spills and overhead; it is not all
waste. Refresh/NMI costs are included in whichever interval they interrupt.
This is a first-pass profile, not a claimed whole-run percentage.

The assembled reference passes:

- 344 target division cases, covering both hardware and software paths and
  boundaries such as divisor 255/256 and dividend/divisor 65535.
- 344 target byte*word product cases.
- 16 complete inner passes (42,992 positions), checking every final array byte
  and each final q against the original arithmetic, including the q/10 update.
- Stack, Y, D and DBR restoration through the normal test harness.
- 458,752 exhaustive Python division pairs across seven large divisors.

The reference's isolated first inner pass took 7,367,988 master clocks.
That test uses a different ROM/harness and NMI environment; it demonstrates
feasibility, not an end-to-end PI speedup or an exact matched before/after.
The reference measurements cover the isolated inner pass.
Evidence and the reproducing script are under `build/pi/analysis/`.

## Outer loop behavior

The 20-byte `print_digit` wrapper ran 897 times during the benchmark, compared
with about 2.4 million inner iterations. It calls `printf` and discards its six
argument bytes.

At `digits == 65535`, the original unsigned `for (j = 1; j <= digits; ++j)`
wraps and does not terminate. The measured run uses 896 digits.
