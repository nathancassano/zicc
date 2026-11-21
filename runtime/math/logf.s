.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.import __fadd32, __fsub32, __fmul32, __fdiv32
.export _logf
.ifndef ZICC_BINARY64
.export _log
.endif
.include "common.inc"

.segment "CODE"
math_nan:
    constant V, $7fc00000
    finish V

.ifndef ZICC_BINARY64
_log:
.endif
_logf:
    enter
    lda V+2,s
    and #$7fff
    ora V,s
    bne log_nonzero
    constant V, $ff800000
    finish V
log_nonzero:
    lda V+2,s
    and #$8000
    jump_ne math_nan
    lda V+2,s
    cmp #$7f80
    bcc log_finite
    jump_ne math_nan
    lda V,s
    jump_ne math_nan
    finish V
log_finite:
    lda #0
    sta E,s
    lda V+2,s
    cmp #$0080
    bcs log_normal
    constant U, $4b800000
    binary __fmul32, V, V, U
    lda #$ffe8
    sta E,s
log_normal:
    lda V+2,s
    xba
    asl
    adc #0
    and #$00ff
    sec
    sbc #127
    clc
    adc E,s
    sta E,s
    lda V+2,s
    and #$007f
    ora #$3f80
    sta V+2,s
    cmp #$3fb5
    bcc log_reduced
    ; Keep |(m-1)/(m+1)| <= 0.172 for a short convergent series
    sec
    sbc #$0080
    sta V+2,s
    lda E,s
    inc
    sta E,s
log_reduced:
    constant U, $3f800000
    binary __fsub32, T, V, U
    binary __fadd32, U, V, U
    binary __fdiv32, V, T, U
    binary __fmul32, Z, V, V
    constant P, $3d9d89d9 ; 1/13
    constant U, $3dba2e8c ; 1/11
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3de38e39 ; 1/9
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3e124925 ; 1/7
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3e4ccccd ; 1/5
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3eaaaaab ; 1/3
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    constant U, $3f800000
    binary __fmul32, P, P, Z
    binary __fadd32, P, P, U
    binary __fmul32, P, P, V
    constant U, $40000000
    binary __fmul32, P, P, U
    exponent_float
    constant U, $3f317218
    binary __fmul32, N, N, U
    binary __fadd32, V, P, N
    finish V
