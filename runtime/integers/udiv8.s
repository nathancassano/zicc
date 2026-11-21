.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __udiv8
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
__udiv8:
    lda z:L
    sta f:$004204
    sep #$20
.a8
    lda z:R
    sta f:$004206
    rep #$20
.a16
    ; Use the same latency as the standalone quotient path
    nop
    nop
    nop
    nop
    nop
    lda f:$004216
    sta z:T
    lda f:$004214
    sta z:L
    rts
