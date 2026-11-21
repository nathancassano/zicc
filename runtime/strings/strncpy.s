.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _strncpy
.include "common.inc"
.segment "CODE"
_strncpy:
    enter
    argument __dp_scratch+4,21
    lda 25+LIBC_RETURN_EXTRA,s
    sta z:__dp_scratch+8
    ldx z:__dp_scratch
    lda #0
    sta z:__dp_scratch+10
@loop:
    lda z:__dp_scratch+8
    beq @done
    lda z:__dp_scratch+10
    bne @zero
    byte __dp_scratch+4
    beq @mark
    next __dp_scratch+4
    bra @write
@mark:
    inc z:__dp_scratch+10
@zero:
    lda #0
@write:
    put
    inx
    dec z:__dp_scratch+8
    bra @loop
@done:
    lda z:__dp_scratch
    leave
