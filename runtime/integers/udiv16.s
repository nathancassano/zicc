.setcpu "65816"
.a16
.i16
.importzp __arith_rhs
.import udiv16_software, __udiv8
.export __udiv16
R=__arith_rhs
.segment "CODE"
__udiv16:
    lda z:R
    beq @software
    cmp #$0100
    bcs @software
    jmp .loword(__udiv8)
@software:
    jmp .loword(udiv16_software)
