; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _ispunct
_ispunct:
    txa
    cmp #33
    bcc :+
    cmp #48
    bcc @yes
:
    cmp #58
    bcc :+
    cmp #65
    bcc @yes
:
    cmp #91
    bcc :+
    cmp #97
    bcc @yes
:
    cmp #123
    bcc :+
    cmp #127
    bcc @yes
:
    lda #0
    rts
@yes:
    lda #1
    rts
