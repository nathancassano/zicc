.setcpu "65816"
.a16
.i16
.export _abs
.segment "CODE"
_abs:
    txa
    bpl abs_done
    eor #$ffff
    inc a
abs_done:
    rts
