.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import signed32_magnitudes, __udiv32, negate_result32
.export __sdivmod32
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
SIGN=__arith_lhs+12
.segment "CODE"
__sdivmod32:
    lda z:L+2
    ora z:R+2
    bmi @signed
    jmp .loword(__udiv32)
@signed:
    lda z:L+2
    sta z:SIGN+2
    jsr .loword(signed32_magnitudes)
    jsr .loword(__udiv32)
    bit z:SIGN
    bpl @remainder
    jsr .loword(negate_result32)
    sta z:L
    stx z:L+2
@remainder:
    lda z:SIGN+2
    bpl @done
    sec
    lda #0
    sbc z:T
    sta z:T
    lda #0
    sbc z:T+2
    sta z:T+2
@done:
    lda z:L
    ldx z:L+2
    rts
