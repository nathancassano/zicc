; Internal far output pointer in A/X; native A16/X16, D=0, DBR=$7E
; The existing raw formatter writes a private near stack buffer. Copy only the
; completed string into bank-$7F storage; no ordinary frame runs with DBR=$7F
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _dec_format_spec
.import _decimal__dec_format_raw_spec, _decimal__dec_output
.segment "CODE"
_dec_format_spec:
    sta z:__dp_scratch
    phy
    tsc
    sec
    sbc #80
    tcs
    tay
    lda a:89,y
    pha
    lda z:__dp_scratch
    pha
    lda a:87,y
    pha
    lda a:85,y
    pha
    tya
    inc a
    tax
    jsr .loword(_decimal__dec_format_raw_spec)
    plx
    plx
    plx
    plx
    ldx #0
    sep #$20
.a8
@copy:
    lda a:1,y
    sta f:_decimal__dec_output,x
    beq @copied
    iny
    inx
    bra @copy
@copied:
    rep #$20
.a16
    tsc
    clc
    adc #80
    tcs
    ply
    lda #.loword(_decimal__dec_output)
    ldx #.bankbyte(_decimal__dec_output)
    rts
__size_dec_format_spec = * - _dec_format_spec
