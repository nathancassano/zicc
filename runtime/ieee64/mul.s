; IEEE binary64 multiplication. Round to nearest, ties to even, with
; gradual underflow. Operands: arithmetic scratch +0..7 and +8..15;
; result: +0..7. Scratch +8..+25 and A/flags are clobbered. X/Y/D/DBR
; preserved. Uses a 16-byte stack product
; NaN inputs and invalid operations return the same quiet NaN
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __fp_round_increment, __fp_raise, __fp_overflow, __fp_tiny
.export __dmul, __dmul_soft
L = __arith_lhs
R = __arith_lhs+8
EA = __arith_lhs+16
EB = __arith_lhs+18
SG = __arith_lhs+20
GUARD = __arith_lhs+22
STICKY = __arith_lhs+24
.segment "CODE"
__dmul_soft:
    phx
    ldx #1
    bra :+
__dmul:
    phx
    ldx #0
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
    bne mul64_check_b
    lda z:L+6
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    jne mul64_lhs_nan
mul64_check_b:
    lda z:EB
    cmp #2047
    bne mul64_special
    lda z:R+6
    and #$000f
    ora z:R+4
    ora z:R+2
    ora z:R
    jne mul64_rhs_nan
mul64_special:
    ; Identify zeros before treating either infinity
    lda z:L+6
    and #$7fff
    ora z:L+4
    ora z:L+2
    ora z:L
    bne mul64_l_nonzero
    lda z:EB
    cmp #2047
    jeq mul64_invalid
    jmp .loword(mul64_zero)
mul64_l_nonzero:
    lda z:R+6
    and #$7fff
    ora z:R+4
    ora z:R+2
    ora z:R
    bne mul64_r_nonzero
    lda z:EA
    cmp #2047
    jeq mul64_invalid
    jmp .loword(mul64_zero)
mul64_r_nonzero:
    lda z:EA
    cmp #2047
    jeq mul64_inf
    lda z:EB
    cmp #2047
    jeq mul64_inf
    ; Restore the hidden bits, normalizing subnormal input significands
    lda z:L+6
    and #$000f
    sta z:L+6
    lda z:EA
    bne mul64_l_normal
    inc z:EA
mul64_l_words:
    ; A word shift is safe only when it cannot pass the hidden bit at 52
    lda z:L+6
    bne mul64_l_normalize
    lda z:L+4
    cmp #$0010
    bcs mul64_l_normalize
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
    bra mul64_l_words
mul64_l_normalize:
    lda z:L+6
    bit #$0010
    bne mul64_l_ready
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    dec z:EA
    bra mul64_l_normalize
mul64_l_normal:
    lda z:L+6
    ora #$0010
    sta z:L+6
mul64_l_ready:
    lda z:R+6
    and #$000f
    sta z:R+6
    lda z:EB
    bne mul64_r_normal
    inc z:EB
mul64_r_words:
    lda z:R+6
    bne mul64_r_normalize
    lda z:R+4
    cmp #$0010
    bcs mul64_r_normalize
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
    bra mul64_r_words
mul64_r_normalize:
    lda z:R+6
    bit #$0010
    bne mul64_r_ready
    asl z:R
    rol z:R+2
    rol z:R+4
    rol z:R+6
    dec z:EB
    bra mul64_r_normalize
mul64_r_normal:
    lda z:R+6
    ora #$0010
    sta z:R+6
mul64_r_ready:
    clc
    lda z:EA
    adc z:EB
    sec
    sbc #1023
    sta z:EA
    ; The significand product can increase this exponent by at most one
    ; Bypass the product when overflow or underflow is already certain
    bmi :+
    cmp #2047
    jcs mul64_overflow
    bra :++
:
    cmp #$ffcb             ; -53 may still round up after normalization
    jcc mul64_tiny
:
    ; The hardware path accumulates the 53x53 product one byte column
    ; at a time. Software interrupts use a separate entry because the
    ; S-CPU multiplier can be live when the interrupt occurs
    tsc
    sec
    sbc #16
    tcs
    cpx #0
    jne mul64_software
    lda z:L
    ora z:L+2
    ora z:L+4
    ora z:R
    ora z:R+2
    ora z:R+4
    bne mul64_columns
; Both significands have only their high byte set
mul64_high_bytes:
    lda #0
    .repeat 6, WORD
        sta WORD*2+1,s
    .endrepeat
    sta 15,s
    sep #$20
.a8
    lda z:L+6
    sta f:$004202
    lda z:R+6
    sta f:$004203
    rep #$20
.a16
    clc
    lda f:$004216
    sta 13,s
    jmp .loword(mul64_normalize)

mul64_columns:
    ; Fixed byte offsets avoid indexing or saving registers for each cell
    ; GUARD holds the low sum and X counts carries out of that word
    stz z:GUARD
    .repeat 13, COL
        ldx #0
        .repeat 7, I
            .if (COL >= I) .and (COL-I < 7)
                sep #$20
                .a8
                lda z:L+I
                sta f:$004202
                lda z:R+COL-I
                sta f:$004203
                rep #$20
                .a16
                clc
                lda f:$004216
                adc z:GUARD
                sta z:GUARD
                bcc :+
                inx
:
            .endif
        .endrepeat
        lda z:GUARD
        ; Each store overlaps the next column. The final one retains both
        ; bytes of the sum. It contains the product of two five-bit bytes
        ; plus the carry from the previous column
        sta COL+1,s
        .if COL < 12
            xba
            and #$00ff
            sta z:GUARD
            txa
            xba
            ora z:GUARD
            sta z:GUARD
        .endif
    .endrepeat
    lda #0
    sta 15,s
    jmp .loword(mul64_normalize)
mul64_software:
    lda z:R
    sta 1,s
    lda z:R+2
    sta 3,s
    lda z:R+4
    sta 5,s
    lda z:R+6
    sta 7,s
    lda #0
    sta 9,s
    sta 11,s
    sta 13,s
    sta 15,s
    ldx #64
mul64_product:
    lda 1,s
    bit #1
    beq mul64_product_shift
    clc
    lda 9,s
    adc z:L
    sta 9,s
    lda 11,s
    adc z:L+2
    sta 11,s
    lda 13,s
    adc z:L+4
    sta 13,s
    lda 15,s
    adc z:L+6
    sta 15,s
mul64_product_shift:
    lda 15,s
    lsr a
    sta 15,s
    lda 13,s
    ror a
    sta 13,s
    lda 11,s
    ror a
    sta 11,s
    lda 9,s
    ror a
    sta 9,s
    lda 7,s
    ror a
    sta 7,s
    lda 5,s
    ror a
    sta 5,s
    lda 3,s
    ror a
    sta 3,s
    lda 1,s
    ror a
    sta 1,s
    dex
    bne mul64_product
mul64_normalize:
    ; The highest product bit is 104 or 105. Position it at bit 52
    ldx #52
    lda 13,s
    bit #$0200
    beq :+
    inx
    inc z:EA
:
    lda z:EA
    bmi mul64_underflow
    beq mul64_underflow
    cmp #2047
    jcs mul64_stack_inf
    bra mul64_round_setup
mul64_underflow:
    ; Exponents below -52 cannot round to a nonzero binary64 value
    beq :+
    cmp #$ffcc
    bcs :+
    jmp .loword(mul64_stack_zero)
:
    eor #$ffff
    clc
    adc #2                 ; 1 - exponent
    sta z:EB
    txa
    clc
    adc z:EB
    tax
    stz z:EA
mul64_round_setup:
    stz z:GUARD
    stz z:STICKY
mul64_shift_words:
    ; Keep at least one bit shift so the last discarded bit is guard
    cpx #17
    bcc mul64_round_shift
    lda z:STICKY
    ora 1,s
    sta z:STICKY
    lda 3,s
    sta 1,s
    lda 5,s
    sta 3,s
    lda 7,s
    sta 5,s
    lda 9,s
    sta 7,s
    lda 11,s
    sta 9,s
    lda 13,s
    sta 11,s
    lda 15,s
    sta 13,s
    lda #0
    sta 15,s
    txa
    sec
    sbc #16
    tax
    bra mul64_shift_words
mul64_round_shift:
    lda z:STICKY
    ora z:GUARD
    sta z:STICKY
    lda 15,s
    lsr a
    sta 15,s
    lda 13,s
    ror a
    sta 13,s
    lda 11,s
    ror a
    sta 11,s
    lda 9,s
    ror a
    sta 9,s
    lda 7,s
    ror a
    sta 7,s
    lda 5,s
    ror a
    sta 5,s
    lda 3,s
    ror a
    sta 3,s
    lda 1,s
    ror a
    sta 1,s
    lda #0
    adc #0
    sta z:GUARD
    dex
    bne mul64_round_shift
    ldx z:STICKY
    lda 1,s
    and #1
    asl a
    ora z:GUARD
    asl a
    asl a
    cpx #0
    beq :+
    ora #1
:
    ldx z:SG
    jsr .loword(__fp_round_increment)
    bcc mul64_pack
    clc
    lda 1,s
    adc #1
    sta 1,s
    lda 3,s
    adc #0
    sta 3,s
    lda 5,s
    adc #0
    sta 5,s
    lda 7,s
    adc #0
    sta 7,s
    bit #$0020
    beq mul64_pack
    ; Rounding carried the 53-bit significand to 2.0
    lda #0
    sta 1,s
    sta 3,s
    sta 5,s
    lda #$0010
    sta 7,s
    inc z:EA
    lda z:EA
    cmp #2047
    jcs mul64_stack_inf
mul64_pack:
    lda 1,s
    sta z:L
    lda 3,s
    sta z:L+2
    lda 5,s
    sta z:L+4
    lda 7,s
    and #$000f
    sta z:L+6
    lda z:EA
    bne :+
    ; Rounding a subnormal may have produced the minimum normal
    lda 7,s
    bit #$0010
    beq :+
    inc z:EA
:
    lda z:EA
    asl a
    asl a
    asl a
    asl a
    ora z:L+6
    ora z:SG
    sta z:L+6
    lda z:GUARD
    ora z:STICKY
    beq mul64_release
    lda z:EA
    beq :+
    lda #$0010
    bra :++
:
    lda #$0018
:
    jsr .loword(__fp_raise)
    bra mul64_release
mul64_stack_zero:
    ldx z:SG
    jsr .loword(__fp_tiny)
    bra mul64_release
mul64_stack_inf:
    ldx z:SG
    jsr .loword(__fp_overflow)
    bra mul64_release
mul64_release:
    tsc
    clc
    adc #16
    tcs
    plx
    rts
mul64_overflow:
    ldx z:SG
    jsr .loword(__fp_overflow)
    plx
    rts
mul64_tiny:
    ldx z:SG
    jsr .loword(__fp_tiny)
    plx
    rts
mul64_lhs_nan:
    lda z:L+6
    bit #$0008
    beq mul64_invalid
    lda z:EB
    cmp #2047
    bne mul64_nan
    lda z:R+6
    and #$000f
    ora z:R+4
    ora z:R+2
    ora z:R
    beq mul64_nan
mul64_rhs_nan:
    lda z:R+6
    bit #$0008
    bne mul64_nan
mul64_invalid:
    lda #1
    jsr .loword(__fp_raise)
mul64_nan:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$7ff8
    sta z:L+6
    plx
    rts
mul64_zero:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda z:SG
    sta z:L+6
    plx
    rts
mul64_inf:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda z:SG
    ora #$7ff0
    sta z:L+6
    plx
    rts
