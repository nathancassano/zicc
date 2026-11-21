.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __uquot16
.export __sdiv16
L=__arith_lhs
R=__arith_rhs
SIGN=__arith_lhs+12
.segment "CODE"
__sdiv16:
    lda z:L
    ora z:R
    bmi @signed
    jmp .loword(__uquot16)
@signed:
    lda z:L
    eor z:R
    sta z:SIGN
    lda z:L
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
    jsr .loword(__uquot16)
    bit z:SIGN
    bpl :+
    eor #$FFFF
    inc a
:
    rts
