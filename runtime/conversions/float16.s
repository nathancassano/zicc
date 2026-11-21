; Word-to-binary32 conversions. Input A, output A/X; Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __sfloat16, __ufloat16
L = __arith_lhs
SGN = __arith_lhs+8
.segment "CODE"
; Word arguments arrive in A and fit exactly in a binary32 significand
__sfloat16:
    cmp #0
    bmi word_float_negative
__ufloat16:
    cmp #32
    bcs word_float_unsigned_large
    asl a
    tax
    lda f:word_float_high,x
    tax
    lda #0
    rts
word_float_unsigned_large:
    stz z:SGN
word_float_magnitude:
    ldx #142
    cmp #$0100
    bcs word_float_test
    xba
    ldx #134
word_float_test:
    cmp #$8000
    bcs word_float_pack
word_float_shift:
    dex
    asl a
    bpl word_float_shift
word_float_pack:
    xba
    pha
    and #$007f
    sta z:L
    txa
    xba
    lsr a
    ora z:L
    ora z:SGN
    tax
    pla
    and #$ff00
    rts
word_float_negative:
    ldx #$8000
    stx z:SGN
    eor #$ffff
    inc a
    cmp #32
    bcs word_float_magnitude
word_float_small:
    asl a
    tax
    lda f:word_float_high,x
    ora #$8000
    tax
    lda #0
    rts

; Exact binary32 magnitudes 0 through 31 have zero low words
word_float_high:
    .word $0000, $3F80, $4000, $4040, $4080, $40A0, $40C0, $40E0
    .word $4100, $4110, $4120, $4130, $4140, $4150, $4160, $4170
    .word $4180, $4188, $4190, $4198, $41A0, $41A8, $41B0, $41B8
    .word $41C0, $41C8, $41D0, $41D8, $41E0, $41E8, $41F0, $41F8
