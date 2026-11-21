; U32 mantissa at 3/5,S; signed binary exponent in A. Void result in the
; existing shared decimal state. Preserve Y/D/DBR, native A16/X16, D=0/DBR=$7E
.setcpu "65816"
.macpack longbranch
.a16
.i16
.export ___ieee_decimal
.import _decimal__dec_digits, _decimal__dec_n, _decimal__dec_scale, __udiv32
.importzp __arith_lhs, __arith_rhs
.segment "CODE"
___ieee_decimal:
    sta z:__arith_lhs
    phy
    tsc
    sec
    sbc #6
    tcs
    tay
    lda 11,s
    sta a:1,y                 ; m low
    lda 13,s
    sta a:3,y                 ; m high
    ora a:1,y
    jeq @zero
    lda z:__arith_lhs
    sta a:5,y                 ; private e, leave the argument home intact
    lda a:1,y
    and #1
    bne @cancelled
@bytes:
    lda a:5,y
    bpl @bits
    cmp #$FFF9                ; e<=-8
    bcs @bits
    lda a:1,y
    and #$00FF
    bne @bits
    lda a:1,y
    xba
    and #$00FF
    sta z:__arith_lhs
    lda a:3,y
    xba
    and #$FF00
    ora z:__arith_lhs
    sta a:1,y
    lda a:3,y
    xba
    and #$00FF
    sta a:3,y
    lda a:5,y
    clc
    adc #8
    sta a:5,y
    bra @bytes
@bits:
    lda a:5,y
    bpl @cancelled
    lda a:1,y
    and #1
    bne @cancelled
    lda a:3,y
    lsr a
    sta a:3,y
    lda a:1,y
    ror a
    sta a:1,y
    lda a:5,y
    inc a
    sta a:5,y
    bra @bits
@cancelled:
    lda #0
    sta f:_decimal__dec_n
    lda a:5,y
    bpl @unscaled
    eor #$FFFF
    inc a
    bra @scale
@unscaled:
    lda #0
@scale:
    sta f:_decimal__dec_scale
@extract:
    lda a:1,y
    sta z:__arith_lhs
    lda a:3,y
    sta z:__arith_lhs+2
    lda #10
    sta z:__arith_rhs
    stz z:__arith_rhs+2
    jsr .loword(__udiv32)
    sta a:1,y
    txa
    sta a:3,y
    ; The existing helper supplies quotient in L and remainder in L+8
    lda z:__arith_lhs+8
    pha
    lda f:_decimal__dec_n
    tax
    pla
    sep #$20
.a8
    sta f:_decimal__dec_digits,x
    rep #$20
.a16
    lda f:_decimal__dec_n
    inc a
    sta f:_decimal__dec_n
    lda a:1,y
    ora a:3,y
    bne @extract
    lda a:5,y
    jeq @done
    jmi @negative
    sta z:__arith_lhs
@double:
    pha
    lda f:_decimal__dec_n
    tay
    pla
    ldx #0
    clc
    sep #$20
.a8
@double_digit:
    lda f:_decimal__dec_digits,x
    rol a
    cmp #10
    bcc @double_store
    sbc #10
@double_store:
    sta f:_decimal__dec_digits,x
    inx
    dey                        ; Keep decimal carry live through the loop test
    bne @double_digit
    bcc @double_no_append
    lda #1
    sta f:_decimal__dec_digits,x
    rep #$20
.a16
    lda f:_decimal__dec_n
    inc a
    sta f:_decimal__dec_n
    bra @double_next
@double_no_append:
    rep #$20
.a16
@double_next:
    dec z:__arith_lhs
    bne @double
    bra @done
@negative:
    eor #$FFFF
    inc a
    sta z:__arith_lhs
@five:
    pha
    lda f:_decimal__dec_n
    tay
    pla
    ldx #0
    sep #$20
.a8
    stz z:__arith_rhs
@five_digit:
    lda f:_decimal__dec_digits,x
    lsr a
    sta z:__arith_lhs+2
    lda z:__arith_rhs
    bcc @five_store
    clc
    adc #5
@five_store:
    sta f:_decimal__dec_digits,x
    lda z:__arith_lhs+2
    sta z:__arith_rhs
    inx
    dey
    bne @five_digit
    lda z:__arith_rhs
    beq @five_no_append
    sta f:_decimal__dec_digits,x
    rep #$20
.a16
    lda f:_decimal__dec_n
    inc a
    sta f:_decimal__dec_n
    bra @five_next
@five_no_append:
    rep #$20
.a16
@five_next:
    dec z:__arith_lhs
    bne @five
@done:
    tsc
    clc
    adc #6
    tcs
    ply
    rts
@zero:
    lda #1
    sta f:_decimal__dec_n
    lda #0
    sta f:_decimal__dec_scale
    sep #$20
.a8
    lda #0
    sta f:_decimal__dec_digits
    rep #$20
.a16
    bra @done
__size___ieee_decimal = * - ___ieee_decimal
