.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __fadd32, __fsub32, __fmul32
.export _expf
.ifndef ZICC_BINARY64
.export _exp
.endif
.include "common.inc"

.segment "CODE"
math_nan:
    constant V, $7fc00000
    finish V
math_zero:
    constant V, 0
    finish V
math_inf:
    constant V, $7f800000
    finish V

.ifndef ZICC_BINARY64
_exp:
.endif
_expf:
    enter
    lda V+2,s
    and #$7fff
    cmp #$7f80
    bcc exp_finite
    bne exp_nan
    lda V,s
    bne exp_nan
    lda V+2,s
    bmi exp_zero
    jmp .loword(math_inf)
exp_nan:
    jmp .loword(math_nan)
exp_zero:
    jmp .loword(math_zero)
exp_finite:
    ; Inputs beyond +/-128 are safely outside all binary32 output ranges
    cmp #$4300
    bcc exp_reduce
    lda V+2,s
    bmi exp_zero
    jmp .loword(math_inf)
exp_reduce:
    constant U, $3fb8aa3b
    binary __fmul32, T, V, U
    lda T+2,s
    and #$8000
    sta SIGN,s
    lda T+2,s
    and #$7fff
    sta T+2,s
    constant U, $3f000000
    binary __fadd32, T, T, U
    lda T+2,s
    xba
    asl
    adc #0
    and #$ff
    sta E,s
    lda #150
    sec
    sbc E,s
    sta COUNT,s
    lda T+2,s
    and #$7f
    ora #$80
    sta T+2,s
exp_integer:
    lda T+2,s
    lsr
    sta T+2,s
    lda T,s
    ror
    sta T,s
    lda COUNT,s
    dec
    sta COUNT,s
    bne exp_integer
    lda T,s
    tax
    lda SIGN,s
    beq exp_unsigned_value
    txa
    eor #$ffff
    inc
    bra exp_unsigned
exp_unsigned_value:
    txa
exp_unsigned:
    sta E,s
    exponent_float
    ; Split ln(2) avoids cancellation error near large multiples
    constant U, $3f317200
    binary __fmul32, T, N, U
    binary __fsub32, V, V, T
    constant U, $35bfbe8e
    binary __fmul32, T, N, U
    binary __fsub32, V, V, T
    constant P, $39500d01 ; 1/7!
    constant U, $3ab60b61 ; 1/6!
    binary __fmul32, P, P, V
    binary __fadd32, P, P, U
    constant U, $3c088889
    binary __fmul32, P, P, V
    binary __fadd32, P, P, U
    constant U, $3d2aaaab
    binary __fmul32, P, P, V
    binary __fadd32, P, P, U
    constant U, $3e2aaaab
    binary __fmul32, P, P, V
    binary __fadd32, P, P, U
    constant U, $3f000000
    binary __fmul32, P, P, V
    binary __fadd32, P, P, U
    constant U, $3f800000
    binary __fmul32, P, P, V
    binary __fadd32, P, P, U
    binary __fmul32, P, P, V
    binary __fadd32, P, P, U
    lda E,s
    cmp #128
    bne exp_not128
    constant U, $40000000
    binary __fmul32, P, P, U
    lda #127
    sta E,s
exp_not128:
    lda E,s
    bmi exp_negative
    cmp #128
    jump_cs math_inf
    bra exp_scale
exp_negative:
    cmp #$ff6a ; -150
    jump_cc math_zero
    cmp #$ff82 ; -126
    bcs exp_scale
    clc
    adc #24
    sta E,s
    constant U, $33800000 ; 2^-24
    binary __fmul32, P, P, U
exp_scale:
    lda E,s
    clc
    adc #127
    xba
    lsr
    sta U+2,s
    lda #0
    sta U,s
    binary __fmul32, V, P, U
    finish V
