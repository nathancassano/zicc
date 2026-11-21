.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __mul16x8
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
__mul16x8:
    ; Same low-word product with the byte supplied on the right
    sep #$20
.a8
    lda z:R
    sta f:$004202
    lda z:L
    sta f:$004203
    lda z:L+1
    rep #$20
.a16
    bne @wide
    lda f:$004216
    sta z:T
    rts
@wide:
    lda f:$004216
    sta z:T
    sep #$20
.a8
    lda z:L+1
    sta f:$004203
    clc
    lda z:T+1
    adc f:$004216
    sta z:T+1
    rep #$20
.a16
    lda z:T
    rts
