; Signed/unsigned 64-bit comparison. L at scratch +0, R at +8
; A is -1, 0, or 1. X/Y/D/DBR and both operands are preserved
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __scmp64, __ucmp64
L = __arith_lhs
R = __arith_lhs+8
.segment "CODE"
__scmp64:
    lda z:L+6
    eor z:R+6
    bpl __ucmp64
    lda z:L+6
    bmi compare64_less
    bra compare64_greater
__ucmp64:
    lda z:L+6
    cmp z:R+6
    bcc compare64_less
    bne compare64_greater
    lda z:L+4
    cmp z:R+4
    bcc compare64_less
    bne compare64_greater
    lda z:L+2
    cmp z:R+2
    bcc compare64_less
    bne compare64_greater
    lda z:L
    cmp z:R
    bcc compare64_less
    bne compare64_greater
    lda #0
    rts
compare64_less:
    lda #$ffff
    rts
compare64_greater:
    lda #1
    rts
