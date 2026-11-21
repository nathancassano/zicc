.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __mul8
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
; Byte operands are proven unsigned, but their promoted C result is a word
__mul8:
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
    rts
