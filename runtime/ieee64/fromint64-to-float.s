; Signed/unsigned 64-bit integer to binary32, round-to-nearest ties-to-even
; Input: __arith_lhs+0..7. Result: low 32 bits of __arith_lhs
; A/flags and scratch +0..+13 clobbered; X/Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.import __fp_round_increment, __fp_raise
.export __sfloat32_64, __ufloat32_64
L=__arith_lhs
SIGN=__arith_lhs+8
EXP=__arith_lhs+10
TEMP=__arith_lhs+12
.segment "CODE"
__sfloat32_64:
    lda z:L+6
    bpl __ufloat32_64
    lda #$8000
    sta z:SIGN
    sec
    lda #0
    sbc z:L
    sta z:L
    lda #0
    sbc z:L+2
    sta z:L+2
    lda #0
    sbc z:L+4
    sta z:L+4
    lda #0
    sbc z:L+6
    sta z:L+6
    bra convert
__ufloat32_64:
    stz z:SIGN
convert:
    lda z:L
    ora z:L+2
    ora z:L+4
    ora z:L+6
    bne @nonzero
    stz z:L
    stz z:L+2
    rts
@nonzero:
    lda #190
    sta z:EXP
@words:
    lda z:L+6
    bne @normalize
    lda z:L+4
    sta z:L+6
    lda z:L+2
    sta z:L+4
    lda z:L
    sta z:L+2
    stz z:L
    lda z:EXP
    sec
    sbc #16
    sta z:EXP
    bra @words
@normalize:
    lda z:L+6
    bmi @round
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    dec z:EXP
    bra @normalize
@round:
    ; The low 40 bits are discarded, including guard and sticky bits
    lda z:L+4
    and #$007f
    ora z:L
    ora z:L+2
    beq :+
    lda #1
:
    sta z:TEMP
    lda z:L+4
    and #$0180
    .repeat 5
    lsr a
    .endrepeat
    ora z:TEMP
    bit #7
    beq @pack
    pha
    lda #$0010
    jsr .loword(__fp_raise)
    pla
    phx
    ldx z:SIGN
    jsr .loword(__fp_round_increment)
    plx
    bcc @pack
    lda z:L+4
    clc
    adc #$0100
    sta z:L+4
    lda z:L+6
    adc #0
    sta z:L+6
    bcc @pack
    lda #$8000
    sta z:L+6
    stz z:L+4
    inc z:EXP
@pack:
    lda z:L+4
    xba
    and #$00ff
    sta z:TEMP
    lda z:L+6
    xba
    and #$ff00
    ora z:TEMP
    pha
    lda z:L+6
    xba
    and #$007f
    sta z:TEMP
    lda z:EXP
    .repeat 7
    asl a
    .endrepeat
    ora z:TEMP
    ora z:SIGN
    sta z:L+2
    pla
    sta z:L
    rts
