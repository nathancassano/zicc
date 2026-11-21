.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _strrchr
.include "common.inc"
.segment "CODE"
_strrchr:
    enter
    argument __dp_scratch,21
    lda z:__dp_scratch+8
    and #$FF
    sta z:__dp_scratch+8
    stz z:__dp_scratch+12
    stz z:__dp_scratch+14
@loop:
    byte __dp_scratch
    cmp z:__dp_scratch+8
    bne @continue
    lda z:__dp_scratch
    sta z:__dp_scratch+12
    lda z:__dp_scratch+2
    sta z:__dp_scratch+14
@continue:
    byte __dp_scratch
    beq @done
    next __dp_scratch
    bra @loop
@done:
    lda z:__dp_scratch+12
    ldx z:__dp_scratch+14
    leave
