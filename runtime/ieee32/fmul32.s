.setcpu "65816"
.a16
.i16
.export __fmul32
.import ieee_fmul32_core
.segment "CODE"
__fmul32:
    phy
    jsr .loword(ieee_fmul32_core)
    ply
    rts
