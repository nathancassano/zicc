; ASCII C locale; word input in X, word result in A. Y/D/DBR preserved
.setcpu "65816"
.a16
.i16
.segment "CODE"
.export _iscntrl
_iscntrl:
    txa
    cmp #0
    bcc :+
    cmp #32
    bcc @yes
:
    cmp #127
    bcc :+
    cmp #128
    bcc @yes
:
    lda #0
    rts
@yes:
    lda #1
    rts
