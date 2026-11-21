.setcpu "65816"
.a16
.i16
.export negate_result32
.segment "CODE"
negate_result32:
    eor #$FFFF
    clc
    adc #1
    pha
    txa
    eor #$FFFF
    adc #0
    tax
    pla
    rts
