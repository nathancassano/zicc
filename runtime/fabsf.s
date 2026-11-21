; IEEE binary32 absolute value clears only the sign bit
.setcpu "65816"
.a16
.i16
.export _fabsf
.ifndef ZICC_BINARY64
.export _fabs
.endif
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

.segment "CODE"
.ifndef ZICC_BINARY64
_fabs:
.endif
_fabsf:
    lda 5+LIBC_RETURN_EXTRA,s
    and #$7fff
    tax
    lda 3+LIBC_RETURN_EXTRA,s
    rts
