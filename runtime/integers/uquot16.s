.setcpu "65816"
.a16
.i16
.importzp __arith_rhs
.import udiv16_software, __uquot8
.export __uquot16
R=__arith_rhs
.segment "CODE"
__uquot16:
    lda z:R
    beq @software
    cmp #$0100
    bcs @software
    jmp .loword(__uquot8)
@software:
    jmp .loword(udiv16_software)
