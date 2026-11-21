; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _tolower
_tolower:
    txa
    cmp #65
    bcc @done
    cmp #91
    bcs @done
    ora #$0020
@done:
    rts
