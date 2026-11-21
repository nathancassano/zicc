.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __udiv16
.export __sdivmod16
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
SIGN=__arith_lhs+12
.segment "CODE"
__sdivmod16:
    lda z:L
    ora z:R
    bmi @signed
    jmp .loword(__udiv16)
@signed:
    lda z:L
    sta z:SIGN+2
    eor z:R
    sta z:SIGN
    lda z:L
    bpl @left_positive
    eor #$FFFF
    inc a
    sta z:L
@left_positive:
    lda z:R
    bpl @right_positive
    eor #$FFFF
    inc a
    sta z:R
@right_positive:
    jsr .loword(__udiv16)
    bit z:SIGN
    bpl @remainder_sign
    eor #$FFFF
    inc a
    sta z:L
@remainder_sign:
    lda z:SIGN+2
    bpl @done
    lda z:T
    eor #$FFFF
    inc a
    sta z:T
@done:
    lda z:L
    rts
