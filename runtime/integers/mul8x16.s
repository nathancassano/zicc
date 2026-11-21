.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __mul8x16
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
; Keep the byte operand in WRMPYA for both partial products. Test the
; word's high byte while the first product runs; X and Y stay untouched
__mul8x16:
    sep #$20
.a8
    lda z:L
    sta f:$004202
    lda z:R
    sta f:$004203
    lda z:R+1
    rep #$20
.a16
    bne @wide
    ; LDA, REP and BNE cover the multiplier latency
    lda f:$004216
    sta z:T
    rts
@wide:
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
