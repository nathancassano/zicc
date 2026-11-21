; 16-bit operands arrive in X; wider operands are little-endian stack words
; All entry points return an int in A, preserving Y, D, and DBR
.setcpu "65816"
.a16
.i16
.export _clz, _clzl, _clzll, ___builtin_clz, ___builtin_clzl, ___builtin_clzll
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

.segment "CODE"
.macro scan_words words
    .repeat words, i
        lda 3+LIBC_RETURN_EXTRA+2*(words-1-i),s
        beq :+
        ldx #(16*i)
        bra count_leading
:
    .endrepeat
    lda #(16*words)
    rts
.endmacro

_clz:
___builtin_clz:
    txa
    bne :+
    lda #16
    rts
:
    ldx #0
    bra count_leading
_clzl:
___builtin_clzl:
    scan_words 2
_clzll:
___builtin_clzll:
    scan_words 4
count_leading:
    asl a
    bcs :+
    inx
    bra count_leading
:
    txa
    rts
