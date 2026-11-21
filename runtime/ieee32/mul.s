; IEEE binary32 multiplication kernel
.setcpu "65816"
.importzp __arith_lhs
.import unpack_checked, ieee32_normalize_ab, ieee32_pack
.import ieee32_right_a, ieee32_zero, ieee32_invalid, ieee32_infinity
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
tmp = __arith_lhs+22
pr = __arith_lhs+24

.segment "CODE"
.export ieee_fmul32_core
ieee_fmul32_core:
    jsr .loword(unpack_checked)
    lda z:ea
    cmp #255
    far_beq mul_inf
    lda z:eb
    cmp #255
    far_beq mul_inf
    lda z:ma
    ora z:ma+2
    bne :+
    jmp .loword(ieee32_zero)
:
    lda z:mb
    ora z:mb+2
    bne :+
    jmp .loword(ieee32_zero)
:
    jsr .loword(ieee32_normalize_ab)
    lda z:ea
    clc
    adc z:eb
    sec
    sbc #127
    sta z:ea
    lda z:ma
    ora z:mb
    bne mul_full
    ; Common exact dyadic operands have no low significand words
    sep #32
.a8
    lda z:ma+2
    sta f:$004202
    lda z:mb+2
    sta f:$004203
    rep #32
.a16
    nop
    lda f:$004216
    ; With both low words zero, the exact product is this word << 32
    ; Its low output word already holds zero. Extract the packer's 27 bits
    ; directly without clearing, writing, then rereading a 48-bit product
    tax
    and #$000f
    xba
    .repeat 4
        asl a
    .endrepeat
    sta z:ma
    txa
    .repeat 4
        lsr a
    .endrepeat
    sta z:ma+2
    jmp .loword(mul_round)
mul_full:
    stz z:pr
    stz z:pr+2
    stz z:pr+4
.include "runtime/ieee32/product.inc"
mul_product:
    ; Shift the 48-bit product right by 20, jamming the discarded tail
    lda z:pr
    sta z:tmp
    lda z:pr+2
    and #15
    ora z:tmp
    sta z:tmp
    lda z:pr+2
    sta z:ma
    lda z:pr+4
    sta z:ma+2
    ; Four fixed extraction shifts need no loop counter
    lsr z:ma+2
    ror z:ma
    lsr z:ma+2
    ror z:ma
    lsr z:ma+2
    ror z:ma
    lsr z:ma+2
    ror z:ma
    lda z:tmp
    beq mul_round
    lda z:ma
    ora #1
    sta z:ma
mul_round:
    lda z:ma+2
    bit #$0800
    bne :+
    jmp .loword(ieee32_pack)
:
    jsr .loword(ieee32_right_a)
    inc z:ea
    jmp .loword(ieee32_pack)
mul_inf:
    lda z:ma
    ora z:ma+2
    bne :+
    jmp .loword(ieee32_invalid)
:
    lda z:mb
    ora z:mb+2
    bne :+
    jmp .loword(ieee32_invalid)
:
    jmp .loword(ieee32_infinity)
