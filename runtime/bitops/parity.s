; 16-bit operands arrive in X; wider operands are little-endian stack words
; All entry points return an int in A, preserving Y, D, and DBR
.setcpu "65816"
.a16
.i16
.export _parity, _parityl, _parityll, ___builtin_parity, ___builtin_parityl, ___builtin_parityll
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

.segment "CODE"
_parity:
___builtin_parity:
    txa
    bra parity_word
_parityl:
___builtin_parityl:
    lda 3+LIBC_RETURN_EXTRA,s
    eor 5+LIBC_RETURN_EXTRA,s
    bra parity_word
_parityll:
___builtin_parityll:
    lda 3+LIBC_RETURN_EXTRA,s
    eor 5+LIBC_RETURN_EXTRA,s
    eor 7+LIBC_RETURN_EXTRA,s
    eor 9+LIBC_RETURN_EXTRA,s
parity_word:
    pha
    xba
    eor 1,s
    sta 1,s
    .repeat 4
        lsr a
    .endrepeat
    eor 1,s
    sta 1,s
    lsr a
    lsr a
    eor 1,s
    sta 1,s
    lsr a
    eor 1,s
    plx
    and #1
    rts
