.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import udiv16_software, __umod8
.export __umod16
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
__umod16:
    lda z:R
    beq @software
    cmp #$0100
    bcs @software
    jmp .loword(__umod8)
@software:
    jsr .loword(udiv16_software)
    lda z:T
    rts
