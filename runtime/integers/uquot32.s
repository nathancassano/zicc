.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import udiv32_software, udiv16_hardware, udiv32_byte_wide
.export __uquot32
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__uquot32:
    lda z:R+2
    bne @software
    lda z:R
    beq @software
    cmp #$0100
    bcs @software
    lda z:L+2
    bne @wide
    lda z:L
    jsr .loword(udiv16_hardware)
    lda f:$004214
    ldx #0
    rts
@wide:
    ldx #0
    jmp .loword(udiv32_byte_wide)
@software:
    jmp .loword(udiv32_software)
