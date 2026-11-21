.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __umod16
.export __smod16
L=__arith_lhs
R=__arith_rhs
SIGN=__arith_lhs+12
.segment "CODE"
__smod16:
    lda z:L
    sta z:SIGN+2
    bpl :+
    eor #$FFFF
    inc a
    sta z:L
:
    lda z:R
    bpl :+
    eor #$FFFF
    inc a
    sta z:R
:
    jsr .loword(__umod16)
    bit z:SIGN+2
    bpl :+
    eor #$FFFF
    inc a
:
    rts
