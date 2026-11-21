.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __fadd32, __fsub32, __fmul32, __fdiv32
.export _atanf
.ifndef ZICC_BINARY64
.export _atan
.endif
.include "common.inc"

.segment "CODE"
math_nan:
    constant V, $7fc00000
    finish V

.ifndef ZICC_BINARY64
_atan:
.endif
_atanf:
    enter
    lda V+2,s
    and #$8000
    sta SIGN,s
    lda V+2,s
    and #$7fff
    sta V+2,s
    cmp #$7f80
    bcc atan_finite
    jump_ne math_nan
    lda V,s
    jump_ne math_nan
atan_finite:
    lda #0
    sta MODE,s
    lda V+2,s
    cmp #$3f80
    bcc atan_small
    constant U, $3f800000
    binary __fdiv32, V, U, V
    lda #1
    sta MODE,s
atan_small:
    lda #0
    sta Q,s
    lda V+2,s
    cmp #$3ed4
    bcc atan_reduced
    constant U, $3f800000
    binary __fsub32, T, V, U
    binary __fadd32, U, V, U
    binary __fdiv32, V, T, U
    lda #1
    sta Q,s
atan_reduced:
    binary __fmul32, Z, V, V
    constant P, $bd579436 ; -1/19
    constant U, $3d70f0f1 ; 1/17
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $bd888889
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3d9d89d9
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $bdba2e8c
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3de38e39
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $be124925
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3e4ccccd
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $beaaaaab
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3f800000
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    binary __fmul32, V, P, V
    lda Q,s
    beq atan_quadrant
    constant U, $3f490fdb
    binary __fadd32, V, V, U
atan_quadrant:
    lda MODE,s
    beq atan_sign
    constant U, $3fc90fdb
    binary __fsub32, V, U, V
atan_sign:
    lda V+2,s
    eor SIGN,s
    sta V+2,s
    finish V
