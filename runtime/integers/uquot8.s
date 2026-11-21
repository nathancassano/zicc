.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __uquot8
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__uquot8:
    ; The quotient is the only result. Waiting here saves the nested call
    lda z:L
    sta f:$004204
    sep #$20
.a8
    lda z:R
    sta f:$004206
    rep #$20
.a16
    ; REP, five NOPs and the long load's fetches cover 16 cycles
    nop
    nop
    nop
    nop
    nop
    lda f:$004214
    rts
