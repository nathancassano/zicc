.setcpu "65816"
.a16
.i16
.importzp __arith_rhs
.import udiv32_software, udiv32_byte
.export __udiv32
R=__arith_rhs
.segment "CODE"
__udiv32:
    ; Use hardware whenever the unsigned divisor fits in a byte. The signed
    ; wrappers enter here after taking magnitudes, so they benefit too
    lda z:R+2
    bne @software
    lda z:R
    beq @software             ; division by zero retains the old undefined path
    cmp #$0100
    bcs @software
    jmp .loword(udiv32_byte)
@software:
    jmp .loword(udiv32_software)
