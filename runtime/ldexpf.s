; Exact power-of-two scaling (binary32). The exponent arrives in A, with x on the stack
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import _errno
.export _ldexpf
.ifndef ZICC_BINARY64
.export _ldexp
.endif
.include "ldexp-common.inc"

.segment "CODE"
.ifndef ZICC_BINARY64
_ldexp:
.endif
_ldexpf:
    scale_float 2, 7, $7f80, $007f, 24, 0
