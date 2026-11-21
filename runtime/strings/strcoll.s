.setcpu "65816"
.a16
.i16
.export _strcoll
.import _strcmp
.segment "CODE"
_strcoll:
    jmp .loword(_strcmp)
