.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __fadd32, __fmul32
.export _sinf, _cosf
.ifndef ZICC_BINARY64
.export _sin, _cos
.endif
.include "common.inc"

.segment "CODE"
math_nan:
    constant V, $7fc00000
    finish V

.ifndef ZICC_BINARY64
_sin:
.endif
_sinf:
    enter
    lda #0
    sta MODE,s
    jmp .loword(trig_begin)
.ifndef ZICC_BINARY64
_cos:
.endif
_cosf:
    enter
    lda #1
    sta MODE,s
trig_begin:
    lda V+2,s
    and #$8000
    sta SIGN,s
    lda V+2,s
    and #$7fff
    sta V+2,s
    cmp #$7f80
    jump_cs math_nan
    cmp #$3f49
    jump_cc trig_direct
    ; Payne-Hanek reduction. Each exponent has floor((2/pi)*2^(e+73))
    ; modulo 2^98. Multiplying by the exact 24-bit significand gives the
    ; quadrant plus 96 fractional bits; omitted bits contribute <2^-72
    xba
    asl
    adc #0
    and #$ff
    sec
    sbc #126
    sta E,s
    asl
    asl
    asl
    sec
    sbc E,s
    asl
    tax
    .repeat 7, I
        lda f:trig_two_over_pi+I*2,x
        sta C+I*2,s
        lda #0
        sta F+I*2,s
    .endrepeat
    lda V,s
    sta M,s
    lda V+2,s
    and #$007f
    ora #$0080
    sta M+2,s
    lda #24
    sta COUNT,s
trig_product:
    lda M+2,s
    lsr
    sta M+2,s
    lda M,s
    ror
    sta M,s
    bcc trig_noadd
    clc
    .repeat 7, I
        lda F+I*2,s
        adc C+I*2,s
        sta F+I*2,s
    .endrepeat
trig_noadd:
    lda C,s
    asl
    sta C,s
    .repeat 6, I
        lda C+I*2+2,s
        rol
        sta C+I*2+2,s
    .endrepeat
    lda COUNT,s
    dec
    sta COUNT,s
    bne trig_product
    lda F+12,s
    and #3
    sta Q,s
    lda F+10,s
    bpl trig_fraction_positive
    ; Round to the nearest multiple of pi/2, leaving |r| <= pi/4
    lda Q,s
    inc
    sta Q,s
    sec
    .repeat 6, I
        lda #0
        sbc F+I*2,s
        sta F+I*2,s
    .endrepeat
    lda #$8000
    bra trig_fraction_sign
trig_fraction_positive:
    lda #0
trig_fraction_sign:
    sta T,s
    lda #126
    sta E,s
trig_normalize:
    lda F+10,s
    bmi trig_pack
    lda F,s
    asl
    sta F,s
    .repeat 5, I
        lda F+I*2+2,s
        rol
        sta F+I*2+2,s
    .endrepeat
    lda E,s
    dec
    sta E,s
    bra trig_normalize
trig_pack:
    ; Round the 96-bit fraction to 24 significant bits, ties to even
    lda F+8,s
    and #$00ff
    cmp #$0080
    bcc trig_pack_bits
    bne trig_round_up
    lda F,s
    ora F+2,s
    ora F+4,s
    ora F+6,s
    bne trig_round_up
    lda F+8,s
    bit #$0100
    beq trig_pack_bits
trig_round_up:
    lda F+8,s
    clc
    adc #$0100
    sta F+8,s
    lda F+10,s
    adc #0
    sta F+10,s
    bcc trig_pack_bits
    lda #$8000
    sta F+10,s
    lda E,s
    inc
    sta E,s
trig_pack_bits:
    lda F+8,s
    xba
    and #$00ff
    sta V,s
    lda F+10,s
    xba
    and #$ff00
    ora V,s
    sta V,s
    lda F+10,s
    xba
    and #$007f
    sta V+2,s
    lda E,s
    xba
    lsr
    ora T,s
    ora V+2,s
    sta V+2,s
    constant U, $3fc90fda
    binary __fmul32, P, V, U
    constant U, $33a22169
    binary __fmul32, T, V, U
    binary __fadd32, V, P, T
    bra trig_quadrant
trig_direct:
    lda #0
    sta Q,s
trig_quadrant:
    lda Q,s
    clc
    adc MODE,s
    sta Q,s
    binary __fmul32, Z, V, V
    lda Q,s
    and #1
    jump_ne trig_cosine
    ; sin(r) on [-pi/4, pi/4], odd Taylor polynomial through degree 11
    constant P, $b2d7322b ; -1/11!
    constant U, $3638ef1d ; 1/9!
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $b9500d01
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3c088889
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $be2aaaab
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3f800000
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    binary __fmul32, V, P, V
    jmp .loword(trig_result)
trig_cosine:
    constant P, $b493f27e ; -1/10!
    constant U, $37d00d01
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $bab60b61
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3d2aaaab
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $bf000000
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3f800000
    binary __fmul32, P, P, Z
    binary __fadd32, V, P, U
trig_result:
    lda Q,s
    and #2
    beq trig_input_sign
    lda V+2,s
    eor #$8000
    sta V+2,s
trig_input_sign:
    lda MODE,s
    bne trig_done
    lda V+2,s
    eor SIGN,s
    sta V+2,s
trig_done:
    finish V
.segment "RODATA"
trig_two_over_pi:
.include "runtime/math-two-over-pi.inc"
