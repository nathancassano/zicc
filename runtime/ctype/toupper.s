; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _toupper
_toupper:
    txa
    cmp #97
    bcc @done
    cmp #123
    bcs @done
    and #$FFDF
@done:
    rts
