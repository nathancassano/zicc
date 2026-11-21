.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _memchr
.include "common.inc"
.segment "CODE"
_memchr:
    enter
    argument __dp_scratch,21
    lda z:__dp_scratch+8
    and #$FF
    sta z:__dp_scratch+8
    lda 25+LIBC_RETURN_EXTRA,s
    sta z:__dp_scratch+10
@loop:
    lda z:__dp_scratch+10
    beq @null
    byte __dp_scratch
    cmp z:__dp_scratch+8
    beq @found
    next __dp_scratch
    dec z:__dp_scratch+10
    bra @loop
@null:
    lda #0
    tax
    leave
@found:
    lda z:__dp_scratch
    ldx z:__dp_scratch+2
    leave
