; Analysis reference only: not wired into compiler or sample builds
; 65816 native mode, M=0, X=0, D=0, DBR=$7E, existing zicc scratch ABI
; A and aux are the C globals. Near function return is in 16-bit A
.setcpu "65816"
.a16
.i16
.import _A, _aux
.importzp __arith_lhs, __arith_rhs
.export _ideal_pass, _ideal_div, _ideal_mul, _ideal_rem
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
Q=__arith_lhs+12
TEN=__arith_lhs+14
.segment "BSS"
_ideal_rem: .res 2
.segment "CODE"

; One unchanged C inner pass. Returns the byte-truncated final q
; Outer digit/carry handling and q/10 are deliberately outside this routine
_ideal_pass:
    phy
    ldx #2686                 ; i-1, hence A can use direct absolute indexed
    ldy #5373                 ; 2*i-1
    stz z:Q
@loop:
    lda a:.loword(_A),x
    and #$00FF
    sta z:TEN
    asl a
    asl a
    clc
    adc z:TEN
    asl a                     ; 10*A[i-1], modulo 65536
    sta z:TEN
    txa
    inc a                     ; i
    sta z:R
    lda z:Q                   ; known zero-extended byte, from the C cast
    sta z:L
    jsr mul_u8_u16_low
    clc
    adc z:TEN                 ; x = 10*A[i-1] + q*i, modulo 65536
    sta z:L
    tya
    sta z:R                   ; k = 2*i-1
    jsr divmod_u16            ; preserves X/Y, returns quotient; T=remainder
    and #$00FF                ; preserve the original low-byte quotient
    sta z:Q
    lda z:T
    sep #$20
.a8
    sta a:.loword(_aux)        ; conservative: keep every original global store
    sta a:.loword(_A),x        ; forward the same byte directly, no reload
    rep #$20
.a16
    dey
    dey
    dex
    bpl @loop                 ; valid because fixed i-1 starts below $8000
    lda z:Q
    ply
    rts

; Two hardware products instead of a full word*word low-product's three
; L is a zero-extended byte, R is a word; preserves X and Y
mul_u8_u16_low:
    sep #$20
.a8
    lda z:L
    sta f:$004202
    lda z:R
    sta f:$004203
    rep #$20
.a16
    clc
    lda f:$004216
    sta z:T
    sep #$20
.a8
    lda z:R+1
    sta f:$004203
    clc
    lda z:T+1
    adc f:$004216
    sta z:T+1
    rep #$20
.a16
    lda z:T
    rts

; General unsigned 16/16 divmod. R>=256 guarantees quotient <=255
; Seed the remainder with dividend>>8, then consume only its eight low bits
; Invariant: A=remainder of the consumed dividend prefix, always <R
; Before each of these eight shifts that prefix fits 15 bits, so ROL A cannot
; lose a seventeenth remainder bit. CMP supplies carry for SBC on subtract
; L ends with quotient; T ends with full remainder. Preserves X and Y
divmod_u16:
    lda z:R
    beq @zero                 ; C division by zero is undefined; deterministic
    cmp #$0100
    bcc @hardware
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
    sbc z:R
    inc z:L
@skip:
    dex
    bne @bit
    sta z:T
    lda z:L
    plx
    rts
@hardware:
    lda z:L
    jsr launch_divide
    lda f:$004216
    sta z:T
    lda f:$004214
    sta z:L
    rts
@zero:
    lda z:L
    sta z:T
    lda #$FFFF
    sta z:L
    rts
launch_divide:
    sta f:$004204
    sep #$20
.a8
    lda z:R
    sta f:$004206
    rep #$20
.a16
    nop
    nop
    rts                       ; return/scheduling provides hardware latency

; Test adapters, not part of the proposed hot-loop code size
_ideal_div:
    sta z:R
    stx z:L
    jsr divmod_u16
    lda z:T
    sta a:.loword(_ideal_rem)
    lda z:L
    rts
_ideal_mul:
    sta z:R
    stx z:L
    jmp mul_u8_u16_low
