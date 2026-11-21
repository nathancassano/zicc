.setcpu "65816"
.a16
.i16
.export _labs
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

.segment "CODE"
_labs:
    lda 5+LIBC_RETURN_EXTRA,s
    tax
    bmi labs_negative
    lda 3+LIBC_RETURN_EXTRA,s
    rts
labs_negative:
    sec
    lda #0
    sbc 3+LIBC_RETURN_EXTRA,s
    pha
    txa
    eor #$ffff
    adc #0
    tax
    pla
    rts
