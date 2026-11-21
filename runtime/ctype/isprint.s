; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _isprint
_isprint:
    txa
    cmp #32
    bcc :+
    cmp #127
    bcc @yes
:
    lda #0
    rts
@yes:
    lda #1
    rts
