; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _isalnum
_isalnum:
    txa
    cmp #48
    bcc :+
    cmp #58
    bcc @yes
:
    cmp #65
    bcc :+
    cmp #91
    bcc @yes
:
    cmp #97
    bcc :+
    cmp #123
    bcc @yes
:
    lda #0
    rts
@yes:
    lda #1
    rts
