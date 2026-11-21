.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import udiv16_hardware, udiv32_software
.export __umod32
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
__umod32:
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
    bra @done
@wide:
    cmp z:R
    bcs @divide_high
    ldx #1
    sep #$20
.a8
    bra @feed_byte
@divide_high:
.a16
    jsr .loword(udiv16_hardware)
    ldx #1
@byte:
    sep #$20
.a8
    lda f:$004216
@feed_byte:
    xba
    lda z:L,x
    rep #$20
.a16
    jsr .loword(udiv16_hardware)
    dex
    bpl @byte
@done:
    lda f:$004216
    ldx #0
    rts
@software:
    jsr .loword(udiv32_software)
    lda z:T
    ldx z:T+2
    rts
