.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _strcat, _strncat
.include "common.inc"
.segment "CODE"
_strcat:
    enter
    lda #$FFFF
    sta z:__dp_scratch+8
    bra append_setup
_strncat:
    enter
    lda 25+LIBC_RETURN_EXTRA,s
    sta z:__dp_scratch+8
append_setup:
    argument __dp_scratch+4,21
    ldx z:__dp_scratch
@end:
    sep #$20
    .a8
    lda a:$0000,x
    rep #$20
    .a16
    and #$FF
    beq @copy
    inx
    bra @end
@copy:
    lda z:__dp_scratch+8
    beq @zero
    byte __dp_scratch+4
    beq @zero
    put
    inx
    next __dp_scratch+4
    dec z:__dp_scratch+8
    bra @copy
@zero:
    lda #0
    put
    lda z:__dp_scratch
    leave
