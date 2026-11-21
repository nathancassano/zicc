; 16-bit operands arrive in X; wider operands are little-endian stack words
; All entry points return an int in A, preserving Y, D, and DBR
.setcpu "65816"
.a16
.i16
.export _ffs, _ffsl, _ffsll, ___builtin_ffs, ___builtin_ffsl, ___builtin_ffsll
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

.segment "CODE"
.macro scan_words words
    .repeat words, i
        lda 3+LIBC_RETURN_EXTRA+2*i,s
        beq :+
        ldx #(16*i)
        bra first_set
:
    .endrepeat
    lda #0
    rts
.endmacro

_ffs:
___builtin_ffs:
    txa
    beq ffs_zero
    ldx #0
first_set:
    inx
    lsr a
    bcc first_set
    txa
    rts
ffs_zero:
    rts
_ffsl:
___builtin_ffsl:
    scan_words 2
_ffsll:
___builtin_ffsll:
    scan_words 4
