.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __ucmp32
.export __scmp32
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__scmp32:
    lda z:L+2
    eor z:R+2
    bpl @unsigned
    lda z:L+2
    bmi @less
    lda #1
    rts
@less:
    lda #$FFFF
    rts
@unsigned:
    jmp .loword(__ucmp32)
