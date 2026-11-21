.setcpu "65816"
.a16
.i16
.export __fcmp32
.import ieee_fcmp32_core
.segment "CODE"
__fcmp32:
    jmp .loword(ieee_fcmp32_core)
