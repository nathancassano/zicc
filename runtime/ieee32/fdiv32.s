.setcpu "65816"
.a16
.i16
.export __fdiv32
.import ieee_fdiv32_core
.segment "CODE"
__fdiv32:
    phy
    jsr .loword(ieee_fdiv32_core)
    ply
    rts
