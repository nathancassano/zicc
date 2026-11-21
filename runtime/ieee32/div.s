; IEEE binary32 division kernel
.setcpu "65816"
.importzp __arith_lhs
.import unpack_checked, ieee32_normalize_ab, ieee32_pack
.import ieee32_zero, ieee32_invalid, ieee32_infinity
.macro far_beq target
    bne :+
    jmp .loword(target)
:
.endmacro
.a16
.i16
ea = __arith_lhs+8
eb = __arith_lhs+10
ma = __arith_lhs+14
mb = __arith_lhs+18
pr = __arith_lhs+24

.segment "CODE"
.export ieee_fdiv32_core
ieee_fdiv32_core:
    jsr .loword(unpack_checked)
    lda z:ea
    cmp #255
    bne div_binf
    lda z:eb
    cmp #255
    bne :+
    jmp .loword(ieee32_invalid)
:
    jmp .loword(ieee32_infinity)
div_binf:
    lda z:eb
    cmp #255
    bne :+
    jmp .loword(ieee32_zero)
:
    lda z:mb
    ora z:mb+2
    bne div_bnonzero
    lda z:ma
    ora z:ma+2
    bne :+
    jmp .loword(ieee32_invalid)
:
    jmp .loword(ieee32_infinity)
div_bnonzero:
    lda z:ma
    ora z:ma+2
    bne :+
    jmp .loword(ieee32_zero)
:
    jsr .loword(ieee32_normalize_ab)
    lda z:ea
    sec
    sbc z:eb
    clc
    adc #127
    sta z:ea
    ; A normalized power-of-two divisor only changes the exponent. Keep
    ; all 24 numerator bits and append the three rounding bits for pack
    lda z:mb
    bne div_compare
    lda z:mb+2
    cmp #$0080
    bne div_compare
    asl z:ma
    rol z:ma+2
    asl z:ma
    rol z:ma+2
    asl z:ma
    rol z:ma+2
    jmp .loword(ieee32_pack)
div_compare:
    lda z:ma+2
    cmp z:mb+2
    bcc div_less
    bne div_start
    lda z:ma
    cmp z:mb
    far_beq div_unit
    bcs div_start
div_less:
    asl z:ma
    rol z:ma+2
    dec z:ea
div_start:
    stz z:pr
    stz z:pr+2
    lda z:ma
    ora z:mb
    bne div_full
    ; Cancel 2^16 to leave a byte divisor. Generate three initial bits,
    ; then three bytes from remainder*256, for 27 quotient bits
    lda z:ma+2
    asl a
    asl a
    ldx #3
div_byte_digit:
    jsr .loword(div_byte_hardware)
    sep #$20
.a8
    lda f:$004214
    sta z:pr,x
    rep #$20
.a16
    lda f:$004216
    dex
    bmi :+
    xba
    bra div_byte_digit
:
    sta z:ma+2
    jmp .loword(div_remainder)
div_byte_hardware:
    sta f:$004204
    sep #$20
.a8
    lda z:mb+2
    sta f:$004206
    rep #$20
.a16
    nop
    nop
    rts
div_full:
    ; Accumulate the high eleven bits once, then shift in the low word
    ldx #11
    jsr .loword(div_digits)
    lda z:pr
    sta z:pr+2
    ldx #16
    jsr .loword(div_digits)
    bra div_remainder
div_digits:
    lda z:ma
    sec
    sbc z:mb
    tay
    lda z:ma+2
    sbc z:mb+2
    bcc div_bit
    sta z:ma+2
    sty z:ma
div_bit:
    rol z:pr
    asl z:ma
    rol z:ma+2
    dex
    bne div_digits
    rts
div_remainder:
    lda z:ma
    ora z:ma+2
    beq div_exact
    lda z:pr
    ora #1
    sta z:pr
div_exact:
    lda z:pr
    sta z:ma
    lda z:pr+2
    sta z:ma+2
    jmp .loword(ieee32_pack)
div_unit:
    ; Equal normalized significands have the exact quotient 1.0
    stz z:ma
    lda #$0400
    sta z:ma+2
    jmp .loword(ieee32_pack)
