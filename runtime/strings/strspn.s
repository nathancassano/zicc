.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _strspn, _strcspn, _strpbrk
.include "common.inc"
.segment "CODE"
; Membership loop shared by span and search functions. No external calls
_strspn:
    enter
    lda #0
    bra span_setup
_strcspn:
    enter
    lda #1
    bra span_setup
_strpbrk:
    enter
    lda #2
span_setup:
    sta z:__dp_scratch+10
    argument __dp_scratch,21
    argument __dp_scratch+4,25
    stz z:__dp_scratch+12
@outer:
    byte __dp_scratch
    beq @end
    sta z:__dp_scratch+8
    ldy #0
@inner:
    sep #$20
    .a8
    lda [__dp_scratch+4],y
    rep #$20
    .a16
    and #$FF
    beq @absent
    cmp z:__dp_scratch+8
    beq @present
    iny
    bra @inner
@absent:
    lda z:__dp_scratch+10
    beq @end
    bra @advance
@present:
    lda z:__dp_scratch+10
    bne @end
@advance:
    next __dp_scratch
    inc z:__dp_scratch+12
    bra @outer
@end:
    lda z:__dp_scratch+10
    cmp #2
    bne @count
    byte __dp_scratch
    beq @null
    lda z:__dp_scratch
    ldx z:__dp_scratch+2
    leave
@null:
    lda #0
    tax
    leave
@count:
    lda z:__dp_scratch+12
    leave
