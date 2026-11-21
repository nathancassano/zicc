.setcpu "65816"
.a16
.i16
.export __fsub32
.import ieee_fsub32_core
.segment "CODE"
__fsub32:
    jmp .loword(ieee_fsub32_core)
