; Near destination in X, padded far source at 3/5,S. Void return
; Native A16/X16, D=0, DBR=$7E; preserve Y/D/DBR. Scratch +0-+3
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _decimal__dec_copy
.segment "CODE"
_decimal__dec_copy:
    phy
    lda 5,s
    sta z:__dp_scratch
    lda 7,s
    sta z:__dp_scratch+2
    ldy #0
    sep #$20
.a8
@byte:
    lda [__dp_scratch],y
    beq @end
    sta a:$0000,x
    inx
    iny
    bne @byte
    inc z:__dp_scratch+2
    bra @byte
@end:
    sta a:$0000,x
    rep #$20
.a16
    ply
    rts
__size_decimal__dec_copy = * - _decimal__dec_copy
