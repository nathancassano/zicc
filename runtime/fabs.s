; IEEE binary64 absolute value clears only the sign bit
.setcpu "65816"
.a16
.i16
.ifdef ZICC_BINARY64
.export _fabs
.importzp __arith_lhs
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

.segment "CODE"
_fabs:
    lda 3+LIBC_RETURN_EXTRA,s
    sta z:__arith_lhs
    lda 5+LIBC_RETURN_EXTRA,s
    sta z:__arith_lhs+2
    lda 7+LIBC_RETURN_EXTRA,s
    sta z:__arith_lhs+4
    lda 9+LIBC_RETURN_EXTRA,s
    and #$7fff
    sta z:__arith_lhs+6
    rts
.endif
