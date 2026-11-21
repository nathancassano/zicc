; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _islower
_islower:
    txa
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
