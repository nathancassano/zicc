; Binary32-to-32-bit-integer conversion. Input __arith_lhs, output A/X;
; Y/D/DBR preserved. Truncate toward zero; out-of-range returns zero
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __fix32
L = __arith_lhs
SGN = __arith_lhs+8
E = __arith_lhs+10
.segment "CODE"
__fix32:
    lda z:L+2
    and #$8000
    sta z:SGN
    lda z:L+2
    and #$7f80
    xba
    asl
    adc #0
    cmp #127
    bcc conversion_zero
    cmp #159
    bcc fix_in_range
conversion_zero:
    lda #0
    tax
    rts
fix_in_range:
    sec
    sbc #150
    sta z:E
    lda z:L+2
    and #$007f
    ora #$0080
    sta z:L+2
    lda z:E
    bmi fix_right
    beq fix_sign
    tax
fix_left_loop:
    asl z:L
    rol z:L+2
    dex
    bne fix_left_loop
    bra fix_sign
fix_right:
    eor #$ffff
    inc
    cmp #16
    bcc fix_right_byte
    sec
    sbc #16
    tax
    ; Only the high significand word survives. Shift its remaining bits
    ; in A instead of rotating a zero high word through direct page
    lda z:L+2
    cpx #0
    beq fix_right_word_done
fix_right_word_loop:
    lsr a
    dex
    bne fix_right_word_loop
fix_right_word_done:
    sta z:L
    stz z:L+2
    bra fix_sign
fix_right_byte:
    cmp #8
    bcc fix_right_bits
    sec
    sbc #8
    tax
    lda z:L
    xba
    and #$00ff
    sta z:L
    lda z:L+2
    xba
    pha
    and #$ff00
    ora z:L
    sta z:L
    pla
    and #$00ff
    sta z:L+2
    txa
fix_right_bits:
    tax
    beq fix_sign
fix_right_loop:
    lsr z:L+2
    ror z:L
    dex
    bne fix_right_loop
fix_sign:
    lda z:SGN
    beq fix_result
    sec
    lda #0
    sbc z:L
    sta z:L
    lda #0
    sbc z:L+2
    sta z:L+2
fix_result:
    ldx z:L+2
    lda z:L
    rts
