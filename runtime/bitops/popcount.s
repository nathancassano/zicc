; 16-bit operands arrive in X; wider operands are little-endian stack words
; All entry points return an int in A, preserving Y, D, and DBR
.setcpu "65816"
.a16
.i16
.export _popcount, _popcountl, _popcountll, ___builtin_popcount, ___builtin_popcountl, ___builtin_popcountll
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

.segment "CODE"
_popcount:
___builtin_popcount:
    txa
    ldx #0
    jsr .loword(count_word)
    txa
    rts
.macro pop_words words
    ldx #0
    .repeat words, i
        lda 3+LIBC_RETURN_EXTRA+2*i,s
        jsr .loword(count_word)
    .endrepeat
    txa
    rts
.endmacro
_popcountl:
___builtin_popcountl:
    pop_words 2
_popcountll:
___builtin_popcountll:
    pop_words 4
count_word:
    cmp #0
    beq @done
@loop:
    lsr a
    bcc :+
    inx
:
    cmp #0
    bne @loop
@done:
    rts
