.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __mul16wide
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
; Full product of independently sign/zero-extended word operands. The caller
; supplies each extension in L+2/R+2 (zero or $FFFF). Four hardware products
; suffice; each negative source subtracts the opposite low word from high
__mul16wide:
    stz z:T
    stz z:T+2
    .repeat 2, I
        .repeat 2, J
    sep #$20
.a8
                .if J = 0
    ; WRMPYA latches; each multiplicand byte is written once
    lda z:L+I
    sta f:$004202
                .endif
    lda z:R+J
    sta f:$004203
    rep #$20
.a16
    clc
    lda f:$004216
    adc z:T+I+J
    sta z:T+I+J
            .if I+J = 0
    lda z:T+2
    adc #0
    sta z:T+2
            .elseif I+J = 1
    sep #$20
.a8
    lda z:T+3
    adc #0
    sta z:T+3
    rep #$20
.a16
            .endif
        .endrepeat
    .endrepeat
    lda z:L+2
    bpl @left_unsigned
    sec
    lda z:T+2
    sbc z:R
    sta z:T+2
@left_unsigned:
    lda z:R+2
    bpl @right_unsigned
    sec
    lda z:T+2
    sbc z:L
    sta z:T+2
@right_unsigned:
    lda z:T
    ldx z:T+2
    rts
