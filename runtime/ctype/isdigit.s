; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _isdigit
_isdigit:
    txa
    cmp #48
    bcc :+
    cmp #58
    bcc @yes
:
    lda #0
    rts
@yes:
    lda #1
    rts
