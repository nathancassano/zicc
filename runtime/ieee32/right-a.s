.setcpu "65816"
.importzp __arith_lhs
.a16
.i16
ma = __arith_lhs+14

.segment "CODE"
.export ieee32_right_a
ieee32_right_a:
    lsr z:ma+2
    ror z:ma
    bcc right_a_done
    lda z:ma
    ora #1                      ; preserve discarded nonzero tail
    sta z:ma
right_a_done:
    rts
