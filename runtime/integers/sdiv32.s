.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import signed32_magnitudes, __uquot32, negate_result32
.export __sdiv32
L=__arith_lhs
R=__arith_rhs
SIGN=__arith_lhs+12
.segment "CODE"
__sdiv32:
    lda z:L+2
    ora z:R+2
    bmi @signed
    jmp .loword(__uquot32)
@signed:
    jsr .loword(signed32_magnitudes)
    jsr .loword(__uquot32)
    bit z:SIGN
    bpl @done
    jmp .loword(negate_result32)
@done:
    rts
