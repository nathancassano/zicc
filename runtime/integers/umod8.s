.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.import udiv16_hardware
.export __umod8
L=__arith_lhs
.segment "CODE"
__umod8:
    lda z:L
    jsr .loword(udiv16_hardware)
    lda f:$004216
    rts
