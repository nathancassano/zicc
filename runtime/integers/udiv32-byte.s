.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import udiv16_hardware
.export udiv32_byte, udiv32_byte_wide
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
udiv32_byte:
    stz z:T+2
    lda z:L+2
    bne @wide
    lda z:L
    jsr .loword(udiv16_hardware)
    lda f:$004214
    sta z:L
    bra udiv32_byte_remainder
@wide:
    ldx #1
udiv32_byte_wide:
    ; Use the high word as a seed when it is smaller than the divisor
    ; Each subsequent dividend is remainder*256+byte, so its quotient fits U8
    cmp z:R
    bcs @divide_high
    stz z:L+2
    sep #$20
.a8
    bra @feed_high_byte
@divide_high:
.a16
    jsr .loword(udiv16_hardware)
    lda f:$004214
    sta z:L+2
    sep #$20
.a8
    lda f:$004216
@feed_high_byte:
    xba
    lda z:L+1
    rep #$20
.a16
    jsr .loword(udiv16_hardware)
    sep #$20
.a8
    lda f:$004214
    sta z:L+1
    lda f:$004216
    xba
    lda z:L
    rep #$20
.a16
    jsr .loword(udiv16_hardware)
    sep #$20
.a8
    lda f:$004214
    sta z:L
    rep #$20
.a16
    cpx #0
    beq udiv32_byte_result
udiv32_byte_remainder:
    lda f:$004216
    sta z:T
udiv32_byte_result:
    lda z:L
    ldx z:L+2
    rts
