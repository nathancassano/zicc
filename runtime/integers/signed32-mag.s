.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export signed32_magnitudes
L=__arith_lhs
R=__arith_rhs
SIGN=__arith_lhs+12
.segment "CODE"
signed32_magnitudes:
    lda z:L+2
    eor z:R+2
    sta z:SIGN
    lda z:L+2
    bpl @left_positive
    sec
    lda #0
    sbc z:L
    sta z:L
    lda #0
    sbc z:L+2
    sta z:L+2
@left_positive:
    lda z:R+2
    bpl @right_positive
    sec
    lda #0
    sbc z:R
    sta z:R
    lda #0
    sbc z:R+2
    sta z:R+2
@right_positive:
    rts
