; Convert signed/unsigned 64-bit integer to IEEE binary64, rounding to
; nearest, ties to even. Input/result: scratch +0..7. Scratch +8..+11
; and A/flags clobbered; X/Y/D/DBR preserved. Native A/X/Y 16-bit mode
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.import __fp_round_increment, __fp_raise
.export __sfloat64_64, __ufloat64_64
L = __arith_lhs
SG = __arith_lhs+8
EX = __arith_lhs+10
.segment "CODE"
__sfloat64_64:
    lda z:L+6
    bpl __ufloat64_64
    lda #$8000
    sta z:SG
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
    bra int64_to_double
__ufloat64_64:
    stz z:SG
int64_to_double:
    phx
    lda z:L
    ora z:L+2
    ora z:L+4
    ora z:L+6
    bne @nonzero
    plx
    rts
@nonzero:
    lda #1086             ; exponent of bit 63, biased by 1023
    sta z:EX
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
    lda z:EX
    sec
    sbc #16
    sta z:EX
    bra @words
@normalize:
    lda z:L+6
    bmi @round
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    dec z:EX
    bra @normalize
@round:
    ; Compress the eleven discarded bits to guard and sticky
    lda z:L
    bit #$07ff
    beq @shift
    lda #$0010
    jsr .loword(__fp_raise)
    lda z:L
    and #$0c00
    xba
    ldx z:L
    pha
    txa
    and #$03ff
    beq :+
    pla
    ora #1
    bra :++
:
    pla
:
    ldx z:SG
    jsr .loword(__fp_round_increment)
    bcc @shift
    clc
    lda z:L
    adc #$0800
    sta z:L
    lda z:L+2
    adc #0
    sta z:L+2
    lda z:L+4
    adc #0
    sta z:L+4
    lda z:L+6
    adc #0
    sta z:L+6
    bcc @shift
    ; A rounded significand of 2.0 becomes 1.0 with exponent +1
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$8000
    sta z:L+6
    inc z:EX
@shift:
    ldx #11
:   lsr z:L+6
    ror z:L+4
    ror z:L+2
    ror z:L
    dex
    bne :-
    lda z:L+6
    and #$000f
    sta z:L+6
    lda z:EX
    asl a
    asl a
    asl a
    asl a
    ora z:L+6
    ora z:SG
    sta z:L+6
    plx
    rts
