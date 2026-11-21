; 32-bit integer-to-binary32 conversions. Input __arith_lhs, output A/X;
; Y/D/DBR preserved. Round integer -> float to nearest/even
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __sfloat32, __ufloat32
L = __arith_lhs
SGN = __arith_lhs+8
E = __arith_lhs+10
.segment "CODE"
__sfloat32:
    lda z:L+2
    and #$8000
    sta z:SGN
    beq float_magnitude
    sec
    lda #0
    sbc z:L
    sta z:L
    lda #0
    sbc z:L+2
    sta z:L+2
    bra float_magnitude
__ufloat32:
    stz z:SGN
float_magnitude:
    ldx #158
    lda z:L+2
    bne float_test_byte
    ldx #142
    lda z:L
    beq conversion_zero
    stz z:L
float_test_byte:
    bmi float_normalized
    cmp #$0100
    bcs float_normalize
    ; Move eight bits at once, carrying the top byte of L into A
    xba
    sta z:E
    lda z:L
    xba
    and #$00ff
    ora z:E
    pha
    lda z:L
    xba
    and #$ff00
    sta z:L
    txa
    sec
    sbc #8
    tax
    pla
    bmi float_normalized
float_normalize:
    dex
    asl z:L
    rol a
    bpl float_normalize
float_normalized:
    sta z:L+2
    stx z:E
    lda z:L
    and #$00ff
    cmp #$0080
    bcc float_pack
    bne float_round_up
    lda z:L
    bit #$0100
    beq float_pack
float_round_up:
    clc
    lda z:L
    adc #$0100
    sta z:L
    lda z:L+2
    adc #0
    sta z:L+2
    bcc float_pack
    inc z:E
float_pack:
    lda z:L
    xba
    and #$00ff
    sta z:L
    lda z:L+2
    xba
    and #$ff00
    ora z:L
    sta z:L
    lda z:L+2
    xba
    and #$007f
    sta z:L+2
    lda z:E
    xba
    lsr
    ora z:SGN
    ora z:L+2
    tax
    lda z:L
    rts
conversion_zero:
    lda #0
    tax
    rts
