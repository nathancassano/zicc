.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __umod32, negate_result32
.export __smod32
L=__arith_lhs
R=__arith_rhs
SIGN=__arith_lhs+12
.segment "CODE"
__smod32:
    lda z:L+2
    ora z:R+2
    bmi @signed
    jmp .loword(__umod32)
@signed:
    lda z:L+2
    sta z:SIGN+2
    bpl :+
    sec
    lda #0
    sbc z:L
    sta z:L
    lda #0
    sbc z:L+2
    sta z:L+2
:
    lda z:R+2
    bpl :+
    sec
    lda #0
    sbc z:R
    sta z:R
    lda #0
    sbc z:R+2
    sta z:R+2
:
    jsr .loword(__umod32)
    bit z:SIGN+2
    bpl @done
    jmp .loword(negate_result32)
@done:
    rts
