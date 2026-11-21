.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.import __mul16wide
.export __smul32wide
L = __arith_lhs
R = __arith_lhs+8
P = __arith_lhs+16
.segment "CODE"

; Signed 32-by-32 product. Stage the inputs outside the word helper's
; workspace, then accumulate two signed cross-products shifted by one word
O = __arith_lhs+24
.macro signed_long_words lo, ro, lsigned, rsigned
    lda z:O+lo
    sta z:L
    stz z:L+2
    .if lsigned
    bpl :+
    dec z:L+2
:
    .endif
    lda z:O+ro
    sta z:L+4
    stz z:L+6
    .if rsigned
    bpl :+
    dec z:L+6
:
    .endif
    jsr .loword(__mul16wide)
.endmacro
.macro add_signed_middle
    clc
    adc z:P+2
    sta z:P+2
    txa
    adc z:P+4
    sta z:P+4
    txa
    bmi :+
    lda #0
    bra :++
:
    lda #$FFFF
:
    adc z:P+6
    sta z:P+6
.endmacro
__smul32wide:
    lda z:L
    sta z:O
    lda z:L+2
    sta z:O+2
    lda z:R
    sta z:O+4
    lda z:R+2
    sta z:O+6
    signed_long_words 0,4,0,0
    sta z:P
    stx z:P+2
    lda z:O+2
    beq @clear_high
    lda z:O+6
    beq @clear_high
    signed_long_words 2,6,1,1
    sta z:P+4
    stx z:P+6
    bra @cross
@clear_high:
    stz z:P+4
    stz z:P+6
@cross:
    lda z:O+6
    beq @left_cross
    signed_long_words 0,6,0,1
    add_signed_middle
@left_cross:
    lda z:O+2
    beq @done
    signed_long_words 2,4,1,0
    add_signed_middle
@done:
    .repeat 4, I
    lda z:P+2*I
    sta z:L+2*I
    .endrepeat
    rts
