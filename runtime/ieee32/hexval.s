; Signed word input in X, signed word result in A. Preserve Y/D/DBR
; Native A16/X16, D=0, DBR=$7E. A/X/flags are call-clobbered
.setcpu "65816"
.a16
.i16
.export _decimal__hexval
.segment "CODE"
_decimal__hexval:
    txa
    sec
    sbc #$0030
    cmp #10
    bcc @done
    txa
    ora #$0020
    sec
    sbc #$0061
    cmp #6
    bcs @invalid
    clc
    adc #10
@done:
    rts
@invalid:
    lda #$FFFF
    rts
__size_decimal__hexval = * - _decimal__hexval
