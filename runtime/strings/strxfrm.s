.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _strxfrm
.include "common.inc"
.segment "CODE"
; C locale transform is the identity. Return full length even if truncated
_strxfrm:
    enter
    argument __dp_scratch+4,21
    lda 25+LIBC_RETURN_EXTRA,s
    sta z:__dp_scratch+8
    stz z:__dp_scratch+12
    ldx z:__dp_scratch
@loop:
    byte __dp_scratch+4
    sta z:__dp_scratch+10
    lda z:__dp_scratch+8
    beq @skip
    lda z:__dp_scratch+10
    put
    inx
    dec z:__dp_scratch+8
@skip:
    lda z:__dp_scratch+10
    beq @done
    inc z:__dp_scratch+12
    next __dp_scratch+4
    bra @loop
@done:
    lda z:__dp_scratch+12
    leave
