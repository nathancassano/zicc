; Convert an unsigned 64-bit integer to digits without a terminator
; Input: __arith_lhs+0..7 magnitude, A=one-past-end near buffer, X=base
; (10 or 16), __arith_lhs+26=0 for uppercase or $20 for lowercase
; Output: A=first digit pointer, X=digit count. Y/D/DBR preserved; A/X,
; flags and arithmetic scratch clobbered. Requires native A16/X16, D=0
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.import __udiv64
.export __int64_format
.export __format_int64_hook := __int64_format
.export __require_int64_format := __int64_format
.segment "CODE"
__int64_format:
    sta z:__arith_lhs+28
    sta z:__arith_lhs+30
    stx z:__arith_lhs+8
    stz z:__arith_lhs+10
    stz z:__arith_lhs+12
    stz z:__arith_lhs+14
@digit:
    lda z:__arith_lhs+8
    cmp #16
    beq @hex_digit
    jsr .loword(__udiv64)
    lda z:__arith_lhs+16
    bra @encode
@hex_digit:
    lda z:__arith_lhs
    and #15
    pha
    .repeat 4
    lsr z:__arith_lhs+6
    ror z:__arith_lhs+4
    ror z:__arith_lhs+2
    ror z:__arith_lhs
    .endrepeat
    pla
@encode:
    cmp #10
    bcc @decimal_digit
    clc
    adc #'A'-10
    ora z:__arith_lhs+26
    bra @store
@decimal_digit:
    clc
    adc #'0'
@store:
    ldx z:__arith_lhs+28
    dex
    stx z:__arith_lhs+28
    sep #$20
.a8
    sta a:0,x
    rep #$20
.a16
    lda z:__arith_lhs
    ora z:__arith_lhs+2
    ora z:__arith_lhs+4
    ora z:__arith_lhs+6
    bne @digit
    lda z:__arith_lhs+30
    sec
    sbc z:__arith_lhs+28
    tax
    lda z:__arith_lhs+28
    rts
