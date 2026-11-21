; IEEE binary64 division, round to nearest, ties to even, with gradual
; underflow. Inputs: scratch +0..7 and +8..15; output: +0..7. Scratch
; +8..+29 and A/flags clobbered. X/Y/D/DBR preserved. NaN inputs and invalid
; operations return the same quiet NaN
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __fp_round_increment, __fp_raise, __fp_overflow, __fp_tiny
.export __ddiv, __ddiv_soft
L = __arith_lhs
R = __arith_lhs+8
Q = __arith_lhs+16
EA = __arith_lhs+24
EB = __arith_lhs+26
SG = __arith_lhs+28

; Collect 56 quotient bits from most significant to least significant
; Each full word shifts the preceding bits out of Q before it is saved
.macro quotient_words digits
    ldx #8
    jsr .loword(digits)
    lda z:Q
    sta z:Q+6
    ldx #16
    jsr .loword(digits)
    lda z:Q
    sta z:Q+4
    ldx #16
    jsr .loword(digits)
    lda z:Q
    sta z:Q+2
    ldx #16
    jsr .loword(digits)
.endmacro
.segment "CODE"
__ddiv_soft:
    phx
    ldx #1
    bra :+
__ddiv:
    phx
    ldx #0                  ; path selector until quotient initialization
:
    lda z:L+6
    eor z:R+6
    and #$8000
    sta z:SG
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    sta z:EA
    lda z:R+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    sta z:EB
    lda z:EA
    cmp #2047
    bne div64_check_b
    lda z:L+6
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    jne div64_lhs_nan
 div64_check_b:
    lda z:EB
    cmp #2047
    bne div64_special
    lda z:R+6
    and #$000f
    ora z:R+4
    ora z:R+2
    ora z:R
    jne div64_rhs_nan
 div64_special:
    lda z:EA
    cmp #2047
    bne div64_rhs_inf
    lda z:EB
    cmp #2047
    jeq div64_invalid
    jmp .loword(div64_inf)
 div64_rhs_inf:
    lda z:EB
    cmp #2047
    jeq div64_zero
    lda z:R+6
    and #$7fff
    ora z:R+4
    ora z:R+2
    ora z:R
    bne div64_rhs_nonzero
    lda z:L+6
    and #$7fff
    ora z:L+4
    ora z:L+2
    ora z:L
    jeq div64_invalid
    lda #2
    jsr .loword(__fp_raise)
    jmp .loword(div64_inf)
 div64_rhs_nonzero:
    lda z:L+6
    and #$7fff
    ora z:L+4
    ora z:L+2
    ora z:L
    jeq div64_zero
    ; Normalize both input significands to have the hidden bit at bit 52
    lda z:L+6
    and #$000f
    sta z:L+6
    lda z:EA
    bne div64_l_normal
    inc z:EA
 div64_l_words:
    ; A word shift is safe only when it cannot pass the hidden bit at 52
    lda z:L+6
    bne div64_l_normalize
    lda z:L+4
    cmp #$0010
    bcs div64_l_normalize
    sta z:L+6
    lda z:L+2
    sta z:L+4
    lda z:L
    sta z:L+2
    stz z:L
    lda z:EA
    sec
    sbc #16
    sta z:EA
    bra div64_l_words
 div64_l_normalize:
    lda z:L+6
    bit #$0010
    bne div64_l_ready
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    dec z:EA
    bra div64_l_normalize
 div64_l_normal:
    lda z:L+6
    ora #$0010
    sta z:L+6
 div64_l_ready:
    lda z:R+6
    and #$000f
    sta z:R+6
    lda z:EB
    bne div64_r_normal
    inc z:EB
 div64_r_words:
    lda z:R+6
    bne div64_r_normalize
    lda z:R+4
    cmp #$0010
    bcs div64_r_normalize
    sta z:R+6
    lda z:R+2
    sta z:R+4
    lda z:R
    sta z:R+2
    stz z:R
    lda z:EB
    sec
    sbc #16
    sta z:EB
    bra div64_r_words
 div64_r_normalize:
    lda z:R+6
    bit #$0010
    bne div64_r_ready
    asl z:R
    rol z:R+2
    rol z:R+4
    rol z:R+6
    dec z:EB
    bra div64_r_normalize
 div64_r_normal:
    lda z:R+6
    ora #$0010
    sta z:R+6
 div64_r_ready:
    sec
    lda z:EA
    sbc z:EB
    clc
    adc #1023
    sta z:EA
    ; If numerator < denominator, double it and lower the result exponent
    lda z:L+6
    cmp z:R+6
    bcc div64_double_l
    bne div64_exponent
    lda z:L+4
    cmp z:R+4
    bcc div64_double_l
    bne div64_exponent
    lda z:L+2
    cmp z:R+2
    bcc div64_double_l
    bne div64_exponent
    lda z:L
    cmp z:R
    bcc div64_double_l
    bne div64_exponent
    ; Equal normalized significands divide exactly to a power of two
    lda z:EA
    bmi div64_exponent
    beq div64_exponent
    cmp #2047
    bcs div64_exponent
    asl a
    asl a
    asl a
    asl a
    ora z:SG
    sta z:L+6
    stz z:L
    stz z:L+2
    stz z:L+4
    plx
    rts
 div64_double_l:
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    dec z:EA
 div64_exponent:
    lda z:EA
    bmi div64_tiny
    cmp #2047
    jcs div64_overflow
    bra div64_compute
 div64_tiny:
    ; Normalized values below exponent -52 are less than half a minimum
    ; subnormal and must round to zero
    cmp #$ffcc
    jcc div64_tiny_result
 div64_compute:
    stz z:Q
    stz z:Q+2
    stz z:Q+4
    stz z:Q+6
    lda z:R
    ora z:R+2
    ora z:R+4
    bne div64_full
    lda z:R+6
    cmp #$0010
    jeq div64_scale_significand
    lda z:L
    ora z:L+2
    ora z:L+4
    bne div64_full
    cpx #0
    bne div64_word_soft
    ; Cancel 2^48 to leave a byte divisor. The first hardware dividend
    ; includes seven fractional bits, then each step supplies eight
    lda z:L+6
    .repeat 7
        asl a
    .endrepeat
    ldx #6
 div64_byte_digit:
    jsr .loword(div64_hardware)
    sep #$20
.a8
    lda f:$004214
    sta z:Q,x
    rep #$20
.a16
    lda f:$004216
    dex
    bmi :+
    xba
    bra div64_byte_digit
:
    sta z:L+6
    jmp .loword(div64_remainder)
 div64_hardware:
    sta f:$004204
    sep #$20
.a8
    lda z:R+6
    sta f:$004206
    rep #$20
.a16
    nop
    nop
    rts
 div64_word_soft:
    quotient_words div64_word_digits
    jmp .loword(div64_remainder)
 div64_full:
    quotient_words div64_digit
    bra div64_remainder
 div64_word_digits:
    lda z:L+6
 div64_word_digit:
    cmp z:R+6
    bcc :+
    sbc z:R+6
:
    rol z:Q
    asl a
    dex
    bne div64_word_digit
    sta z:L+6
    rts
 div64_digit:
    lda z:L+6
 div64_compare_high:
    cmp z:R+6
    bcc div64_no_digit
    bne div64_save_high
    sta z:L+6
    lda z:L+4
    cmp z:R+4
    bcc div64_reload_high
    bne div64_subtract
    lda z:L+2
    cmp z:R+2
    bcc div64_reload_high
    bne div64_subtract
    lda z:L
    cmp z:R
    bcs div64_subtract
 div64_reload_high:
    lda z:L+6
    bra div64_no_digit
 div64_save_high:
    sta z:L+6
 div64_subtract:
    lda z:L
    sbc z:R
    sta z:L
    lda z:L+2
    sbc z:R+2
    sta z:L+2
    lda z:L+4
    sbc z:R+4
    sta z:L+4
    lda z:L+6
    sbc z:R+6
 div64_no_digit:
    ; Comparison or subtraction leaves the next quotient bit in carry
    ; The most significant remainder word stays in A between digits
    rol z:Q
    asl z:L
    rol z:L+2
    rol z:L+4
    rol a
    dex
    bne div64_compare_high
    sta z:L+6
    rts
 div64_remainder:
    ; Remaining nonzero division remainder is sticky
    lda z:L
    ora z:L+2
    ora z:L+4
    ora z:L+6
    beq :+
    lda z:Q
    ora #1
    sta z:Q
:
 div64_scale:
    lda z:EA
    bmi div64_subnormal
    bne div64_round
    bra div64_subnormal

 div64_scale_significand:
    ; Division by a power of two retains the exact significand. Append
    ; guard/round/sticky bits for the common normal and subnormal packer
    .repeat 4, I
        lda z:L+I*2
        sta z:Q+I*2
    .endrepeat
    .repeat 3
        asl z:Q
        rol z:Q+2
        rol z:Q+4
        rol z:Q+6
    .endrepeat
    bra div64_scale
 div64_subnormal:
    eor #$ffff
    clc
    adc #2                ; 1 - exponent
    tax
    stz z:EA
 div64_denormal_words:
    cpx #16
    bcc div64_denormal_bits
    lda z:Q
    beq :+
    lda #1
:
    sta z:L                ; division remainder is no longer needed
    lda z:Q+2
    ora z:L
    sta z:Q
    lda z:Q+4
    sta z:Q+2
    lda z:Q+6
    sta z:Q+4
    stz z:Q+6
    txa
    sec
    sbc #16
    tax
    beq div64_round
    bra div64_denormal_words
 div64_denormal_bits:
 div64_denormal_shift:
    lsr z:Q+6
    ror z:Q+4
    ror z:Q+2
    ror z:Q
    bcc :+
    lda z:Q
    ora #1
    sta z:Q
:
    dex
    bne div64_denormal_shift
 div64_round:
    ldx z:SG
    lda z:Q
    and #7
    sta z:EB
    lda z:Q
    jsr .loword(__fp_round_increment)
    bcc div64_pack
    clc
    lda z:Q
    adc #8
    sta z:Q
    lda z:Q+2
    adc #0
    sta z:Q+2
    lda z:Q+4
    adc #0
    sta z:Q+4
    lda z:Q+6
    adc #0
    sta z:Q+6
    bit #$0100
    beq div64_pack
    lsr z:Q+6
    ror z:Q+4
    ror z:Q+2
    ror z:Q
    inc z:EA
    lda z:EA
    cmp #2047
    jcs div64_overflow
 div64_pack:
    lda z:EA
    bne :+
    lda z:Q+6
    bit #$0080
    beq :+
    inc z:EA
:
    ldx #3
:   lsr z:Q+6
    ror z:Q+4
    ror z:Q+2
    ror z:Q
    dex
    bne :-
    lda z:Q
    sta z:L
    lda z:Q+2
    sta z:L+2
    lda z:Q+4
    sta z:L+4
    lda z:Q+6
    and #$000f
    sta z:L+6
    lda z:EA
    asl a
    asl a
    asl a
    asl a
    ora z:L+6
    ora z:SG
    sta z:L+6
    lda z:EB
    beq :+
    lda z:EA
    beq :++
    lda #$0010
    jsr .loword(__fp_raise)
:
    plx
    rts
:
    lda #$0018
    jsr .loword(__fp_raise)
    plx
    rts
 div64_overflow:
    ldx z:SG
    jsr .loword(__fp_overflow)
    plx
    rts
div64_tiny_result:
    ldx z:SG
    jsr .loword(__fp_tiny)
    plx
    rts
div64_lhs_nan:
    lda z:L+6
    bit #$0008
    beq div64_invalid
    lda z:EB
    cmp #2047
    bne div64_nan
    lda z:R+6
    and #$000f
    ora z:R+4
    ora z:R+2
    ora z:R
    beq div64_nan
div64_rhs_nan:
    lda z:R+6
    bit #$0008
    bne div64_nan
div64_invalid:
    lda #1
    jsr .loword(__fp_raise)
div64_nan:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$7ff8
    sta z:L+6
    plx
    rts
 div64_zero:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda z:SG
    sta z:L+6
    plx
    rts
 div64_inf:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda z:SG
    ora #$7ff0
    sta z:L+6
    plx
    rts
