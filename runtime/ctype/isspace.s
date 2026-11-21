; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _isspace
_isspace:
    txa
    cmp #9
    bcc :+
    cmp #14
    bcc @yes
:
    cmp #32
    bcc :+
    cmp #33
    bcc @yes
:
    lda #0
    rts
@yes:
    lda #1
    rts
