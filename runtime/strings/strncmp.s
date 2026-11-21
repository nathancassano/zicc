.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _strncmp
.include "common.inc"
.segment "CODE"
_strncmp:
    enter
    argument __dp_scratch,21
    argument __dp_scratch+4,25
    lda 29+LIBC_RETURN_EXTRA,s
    tax
    ; A16 count flags survive SEP. With at most 65535 reads, Y never wraps
    sep #$20
    .a8
    beq @equal
@loop:
    lda [__dp_scratch],y
    cmp [__dp_scratch+4],y
    bne @different
    cmp #0
    beq @equal
    iny
    dex
    bne @loop
@equal:
    rep #$20
    .a16
    lda #0
    bra @done
@different:
    rep #$20
    .a16
    lda #1
    bcs @done
    lda #$FFFF
@done:
    leave
