.setcpu "65816"
.importzp __arith_lhs
.a16
.i16
.segment "CODE"
.export ieee_ftest32_core
ieee_ftest32_core:
    lda __arith_lhs+2
    and #$7fff
    ora __arith_lhs
    rts
