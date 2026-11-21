.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __ucmp32
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__ucmp32:
    lda z:L+2
    cmp z:R+2
    bcc @less
    bne @greater
    lda z:L
    cmp z:R
    bcc @less
    bne @greater
    lda #0
    rts
@less:
    lda #$FFFF
    rts
@greater:
    lda #1
    rts
