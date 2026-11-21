.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __scmp16
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__scmp16:
    lda z:L
    cmp z:R
    beq @equal
    sec
    sbc z:R
    bvc :+
    eor #$8000
:
    bmi @less
    lda #1
    rts
@equal:
    lda #0
    rts
@less:
    lda #$FFFF
    rts
