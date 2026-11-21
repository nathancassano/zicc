; Convert IEEE binary64 to signed/unsigned 64-bit integer, truncating toward
; zero. Input/result scratch +0..7; scratch +8 and A/flags clobbered;
; X/Y/D/DBR preserved. Out-of-range conversions are undefined in C;
; exponents outside [0,63] produce zero. Native A/X/Y 16-bit mode
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __fp_raise
.export __fix64_64, __ufix64_64
L = __arith_lhs
SG = __arith_lhs+8
.segment "CODE"
__fix64_64:
    phx
    lda #0
    bra fix64_convert
__ufix64_64:
    phx
    lda #1
fix64_convert:
    sta z:SG
    lda z:L+6
    and #$8000
    ora z:SG
    sta z:SG
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    cmp #1023
    jcc @small
    cmp #1087
    jcs @invalid_zero
    ; X is the right shift needed after placing the hidden bit at bit 63
    eor #$ffff
    clc
    adc #1087
    tax
    lda z:L+6
    and #$000f
    ora #$0010
    sta z:L+6
    ; Place the 53-bit significand in the high 53 bits of the word
    phy
    ldy #11
:   asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    dey
    bne :-
    ply
@words:
    cpx #16
    bcc @bits
    lda z:L
    beq :+
    lda z:SG
    ora #2
    sta z:SG
:
    lda z:L+2
    sta z:L
    lda z:L+4
    sta z:L+2
    lda z:L+6
    sta z:L+4
    stz z:L+6
    txa
    sec
    sbc #16
    tax
    bra @words
@bits:
    cpx #0
    beq @sign
@shift:
    lsr z:L+6
    ror z:L+4
    ror z:L+2
    ror z:L
    bcc :+
    lda z:SG
    ora #2
    sta z:SG
:
    dex
    bne @shift
@sign:
    lda z:SG
    bit #1
    beq @signed
    bmi @invalid
    bra @check_inexact
@signed:
    lda z:L+6
    bpl @check_inexact
    lda z:SG
    bpl @invalid
    lda z:L+6
    and #$7fff
    ora z:L
    ora z:L+2
    ora z:L+4
    beq @check_inexact
@invalid:
    lda #1
    jsr .loword(__fp_raise)
    bra @apply_sign
@check_inexact:
    lda z:SG
    bit #2
    beq @apply_sign
    lda #$0010
    jsr .loword(__fp_raise)
@apply_sign:
    lda z:SG
    bpl @done
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
@done:
    plx
    rts
@small:
    lda z:L+6
    and #$7fff
    ora z:L
    ora z:L+2
    ora z:L+4
    beq @zero
    lda #$0010
    bra @raise_zero
@invalid_zero:
    lda #1
@raise_zero:
    jsr .loword(__fp_raise)
@zero:
    stz z:L
    stz z:L+2
    stz z:L+4
    stz z:L+6
    plx
    rts
