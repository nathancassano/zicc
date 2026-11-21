.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _strtok
.include "common.inc"
.segment "BSS"
token_cursor: .res 2
.segment "CODE"
_strtok:
    enter
    argument __dp_scratch+4,21
    ldx z:__dp_scratch
    bne @begin
    ldx token_cursor
    beq @null
@begin:
    stz z:__dp_scratch+12
@outer:
    sep #$20
    .a8
    lda a:$0000,x
    rep #$20
    .a16
    and #$FF
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
    beq @ordinary
    cmp z:__dp_scratch+8
    beq @delimiter
    iny
    bra @inner
@ordinary:
    lda z:__dp_scratch+12
    bne @next
    stx z:__dp_scratch+12
@next:
    inx
    bra @outer
@delimiter:
    lda z:__dp_scratch+12
    beq @next
    lda #0
    put
    inx
    stx token_cursor
    lda z:__dp_scratch+12
    leave
@end:
    stz token_cursor
    lda z:__dp_scratch+12
    leave
@null:
    lda #0
    leave
