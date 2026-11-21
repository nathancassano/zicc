.setcpu "65816"
.a16
.i16
.export __fadd32
.import ieee_fadd32_core
.segment "CODE"
__fadd32:
    jmp .loword(ieee_fadd32_core)
