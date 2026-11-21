.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __mul16
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
__mul16:
    ; Only 00, 10 and 01 contribute to the low sixteen product bits
    ; A high byte of $FF contributes minus the other low byte
    sep #$20
.a8
    lda z:L
    sta f:$004202
    lda z:R
    sta f:$004203
    rep #$20
.a16
    clc
    lda f:$004216
    sta z:T
    sep #$20
.a8
    lda z:R+1
    beq @left_high
    cmp #$FF
    beq @right_negative
    sta f:$004203             ; WRMPYA still holds L
    clc
    lda z:T+1
    adc f:$004216
    sta z:T+1
@left_high:
    lda z:L+1
    beq @done
    cmp #$FF
    beq @left_negative
    sta f:$004202
    lda z:R
    sta f:$004203
    clc
    lda z:T+1
    adc f:$004216
@store_high:
    sta z:T+1
@done:
    rep #$20
.a16
    lda z:T
    rts
.a8
@right_negative:
    lda z:T+1
    sbc z:L
    sta z:T+1
    bra @left_high
@left_negative:
    lda z:T+1
    sbc z:R
    bra @store_high
