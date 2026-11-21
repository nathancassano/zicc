.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _strstr
.include "common.inc"
.segment "CODE"
_strstr:
    enter
    argument __dp_scratch,21
    argument __dp_scratch+4,25
@outer:
    ldy #0
@inner:
    sep #$20
    .a8
    lda [__dp_scratch+4],y
    rep #$20
    .a16
    and #$FF
    beq @found
    sta z:__dp_scratch+8
    sep #$20
    .a8
    lda [__dp_scratch],y
    rep #$20
    .a16
    and #$FF
    cmp z:__dp_scratch+8
    bne @mismatch
    iny
    bra @inner
@mismatch:
    byte __dp_scratch
    beq @null
    next __dp_scratch
    bra @outer
@null:
    lda #0
    tax
    leave
@found:
    lda z:__dp_scratch
    ldx z:__dp_scratch+2
    leave
