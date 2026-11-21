; Binary64 unary negation, native A/X/Y 16-bit. Operand/result is the
; eight bytes at arithmetic scratch +0. Flip only the sign bit, preserving
; zero signs, infinity and NaN payload bits. A/flags are clobbered;
; X/Y/D/DBR are preserved
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __dneg
.segment "CODE"
__dneg:
    lda z:__arith_lhs+6
    eor #$8000
    sta z:__arith_lhs+6
    rts
