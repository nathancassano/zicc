.setcpu "65816"
.a16
.i16
.exportzp __dp_scratch, __arith_lhs, __arith_rhs
.segment "DP_SCRATCH": zeropage
__dp_scratch:
__arith_lhs: .res 4
__arith_rhs: .res 4
             .res 24
