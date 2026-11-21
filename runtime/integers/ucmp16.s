.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __ucmp16
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__ucmp16:
    lda z:L
    cmp z:R
    beq @equal
    bcc @less
    lda #1
    rts
@equal:
    lda #0
    rts
@less:
    lda #$FFFF
    rts
