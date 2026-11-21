.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export _sqrtf
.ifndef ZICC_BINARY64
.export _sqrt
.endif
.include "common.inc"
SQ_ROOT = __arith_lhs
SQ_REM = __arith_lhs+4
SQ_N = __arith_lhs+8
SQ_TRIAL = __arith_lhs+14

.segment "CODE"
.ifndef ZICC_BINARY64
_sqrt:
.endif
_sqrtf:
    ; Classify using the caller's input. Only finite positive values need
    ; exponent and iteration storage; X retains the raw high word
    lda 5+MATH_RETURN_EXTRA,s
    tax
    beq sqrt_low_word
    bmi sqrt_negative
    cmp #$7f80
    bcc sqrt_finite
    bne sqrt_nan
    lda 3+MATH_RETURN_EXTRA,s
    beq sqrt_return               ; positive infinity
sqrt_nan:
    lda #0
    ldx #$7fc0
sqrt_return:
.if MATH_RETURN_EXTRA
    rtl
.else
    rts
.endif
sqrt_negative:
    cpx #$8000
    bne sqrt_nan
    lda 3+MATH_RETURN_EXTRA,s
    bne sqrt_nan
    bra sqrt_return               ; preserve negative zero in X
sqrt_low_word:
    lda 3+MATH_RETURN_EXTRA,s
    beq sqrt_return               ; positive zero
sqrt_finite:
    tsc
    sec
    sbc #FRAME
    tcs
    lda FRAME+3+MATH_RETURN_EXTRA,s
    sta z:SQ_ROOT
    txa
    and #$007f
    sta z:SQ_ROOT+2
    txa
    .repeat 7
        lsr a
    .endrepeat
    beq sqrt_subnormal
    sec
    sbc #127
    pha
    lda z:SQ_ROOT+2
    ora #$0080
    sta z:SQ_ROOT+2
    pla
    bra sqrt_exponent
sqrt_subnormal:
    lda #.loword(-126)
sqrt_normalize:
    asl z:SQ_ROOT
    rol z:SQ_ROOT+2
    dec a
    ldx z:SQ_ROOT+2
    cpx #$0080
    bcc sqrt_normalize
sqrt_exponent:
    bit #1
    beq :+
    asl z:SQ_ROOT
    rol z:SQ_ROOT+2
:
    cmp #$8000
    ror a
    clc
    adc #127
    xba
    lsr a
    sta E,s
    ; The radicand is significand << 23, including the parity bit above
    ; Consume its 48 bits two at a time and retain the exact remainder
    stz z:SQ_N
    lda z:SQ_ROOT
    sta z:SQ_N+2
    lda z:SQ_ROOT+2
    .repeat 7
        asl z:SQ_N+2
        rol a
    .endrepeat
    sta z:SQ_N+4
    stz z:SQ_ROOT
    stz z:SQ_ROOT+2
    stz z:SQ_REM
    stz z:SQ_REM+2
    ldx #24
sqrt_digit:
    .repeat 2
        asl z:SQ_N
        rol z:SQ_N+2
        rol z:SQ_N+4
        rol z:SQ_REM
        rol z:SQ_REM+2
    .endrepeat
    asl z:SQ_ROOT
    rol z:SQ_ROOT+2
    lda z:SQ_ROOT
    asl a
    ora #1
    sta z:SQ_TRIAL
    lda z:SQ_ROOT+2
    rol a
    sta z:SQ_TRIAL+2
    lda z:SQ_REM+2
    cmp z:SQ_TRIAL+2
    bcc sqrt_next
    bne sqrt_subtract
    lda z:SQ_REM
    cmp z:SQ_TRIAL
    bcc sqrt_next
sqrt_subtract:
    lda z:SQ_REM
    sbc z:SQ_TRIAL
    sta z:SQ_REM
    lda z:SQ_REM+2
    sbc z:SQ_TRIAL+2
    sta z:SQ_REM+2
    inc z:SQ_ROOT
sqrt_next:
    dex
    bne sqrt_digit
    ; sqrt(N) is above the halfway point exactly when N-root^2 > root
    lda z:SQ_REM+2
    cmp z:SQ_ROOT+2
    bcc sqrt_pack
    bne sqrt_round
    lda z:SQ_REM
    cmp z:SQ_ROOT
    bcc sqrt_pack
    beq sqrt_pack
sqrt_round:
    inc z:SQ_ROOT
    bne sqrt_pack
    inc z:SQ_ROOT+2
sqrt_pack:
    lda z:SQ_ROOT
    sta Z,s
    lda z:SQ_ROOT+2
    cmp #$0100
    bcc :+
    lda E,s
    clc
    adc #$0080
    bra :++
:
    and #$007f
    ora E,s
:
    sta Z+2,s
    finish Z
