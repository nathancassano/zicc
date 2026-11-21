; Exact power-of-two scaling (binary64). The exponent arrives in A, with x on the stack
.setcpu "65816"
.macpack longbranch
.a16
.i16
.ifdef ZICC_BINARY64
.importzp __arith_lhs
.import _errno
.import __fp_round_increment, __fp_raise, __fp_overflow
.export _ldexp
.include "ldexp-common.inc"

.segment "CODE"
_ldexp:
    scale_float 4, 4, $7ff0, $000f, 53, 1
.endif
