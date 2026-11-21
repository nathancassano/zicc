; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _isgraph
_isgraph:
    txa
    cmp #33
    bcc :+
    cmp #127
    bcc @yes
:
    lda #0
    rts
@yes:
    lda #1
    rts
