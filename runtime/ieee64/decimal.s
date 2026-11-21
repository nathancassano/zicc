; Exact binary64 decimal expansion for formatting and conversion
; Input: IEEE binary64 bits in __arith_lhs+0..7.  Sign is ignored
; Return A=0 finite, 1 infinity, 2 NaN. For finite values the numeric
; decimal digits are little-endian in _ieee64_dec_digits, with count in
; _ieee64_dec_n and decimal scale in _ieee64_dec_scale.  The represented
; magnitude is integer(digits) * 10^(-scale). Zero has one zero digit and
; scale zero. A/X/flags and arithmetic scratch are clobbered; Y/D/DBR are
; preserved. Native A16/X16, D=0, DBR=$7E. Workspace is shared, like the
; existing decimal formatter, and this member is linked only on demand
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __udiv64
.export __ieee64_decimal, __ieee64_decimal_scaled
.export _ieee64_dec_digits, _ieee64_dec_n, _ieee64_dec_scale
L = __arith_lhs
R = __arith_lhs+8
REM = __arith_lhs+16
TEMP = __arith_lhs+26
EXP = __arith_lhs+28
.segment "RUNTIME_BSS"
.align 2
_ieee64_dec_digits: .res 800
_ieee64_dec_n: .res 2
_ieee64_dec_scale: .res 2
.assert _ieee64_dec_digits >= $7F0000 .and _ieee64_dec_scale+2 <= $800000, lderror, "binary64 decimal workspace exceeds bank $7F"
.segment "CODE"
; Exact unsigned integer in L times 2^A (signed exponent). The integer may
; contain all 64 bits; exponent is limited to -1075..971 so the 800-digit
; workspace is sufficient. Input and output ABI match __ieee64_decimal
; This entry also represents midpoints between adjacent binary64 values
__ieee64_decimal_scaled:
    phy
    sta z:EXP
    lda z:L
    ora z:L+2
    ora z:L+4
    ora z:L+6
    jeq zero
    jmp .loword(nonzero)
__ieee64_decimal:
    phy
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    cmp #2047
    jeq special
normal_or_subnormal:
    cmp #0
    beq subnormal
    sec
    sbc #1075
    sta z:EXP
    lda z:L+6
    and #$000f
    ora #$0010
    sta z:L+6
    bra nonzero
subnormal:
    lda #$fbce             ; -1074
    sta z:EXP
    lda z:L+6
    and #$000f
    sta z:L+6
    ora z:L+4
    ora z:L+2
    ora z:L
    jeq zero
nonzero:
    ; Cancel exact powers of two while the decimal scale is negative
cancel_words:
    lda z:EXP
    bpl cancel_done
    cmp #$fff1             ; -15
    bcs cancel_bits
    lda z:L
    bne cancel_bits
    lda z:L+2
    sta z:L
    lda z:L+4
    sta z:L+2
    lda z:L+6
    sta z:L+4
    stz z:L+6
    lda z:EXP
    clc
    adc #16
    sta z:EXP
    bra cancel_words
cancel_bits:
    lda z:EXP
    bpl cancel_done
    lda z:L
    and #1
    bne cancel_done
    lsr z:L+6
    ror z:L+4
    ror z:L+2
    ror z:L
    inc z:EXP
    bra cancel_bits
cancel_done:
    lda #0
    sta f:_ieee64_dec_n
    lda z:EXP
    bpl positive_scale
    eor #$ffff
    inc a
    bra store_scale
positive_scale:
    lda #0
store_scale:
    sta f:_ieee64_dec_scale
extract:
    lda #10
    sta z:R
    stz z:R+2
    stz z:R+4
    stz z:R+6
    jsr .loword(__udiv64)
    lda f:_ieee64_dec_n
    tax
    lda z:REM
    sep #$20
.a8
    sta f:_ieee64_dec_digits,x
    rep #$20
.a16
    lda f:_ieee64_dec_n
    inc a
    sta f:_ieee64_dec_n
    lda z:L
    ora z:L+2
    ora z:L+4
    ora z:L+6
    bne extract
    lda z:EXP
    jeq finish
    jmi negative_exp
double_loop:
    lda f:_ieee64_dec_n
    tay
    ldx #0
    clc
    sep #$20
.a8
double_digit:
    lda f:_ieee64_dec_digits,x
    rol a
    cmp #10
    bcc double_store
    sbc #10
double_store:
    sta f:_ieee64_dec_digits,x
    inx
    dey
    bne double_digit
    bcc double_no_append
    lda #1
    sta f:_ieee64_dec_digits,x
    rep #$20
.a16
    lda f:_ieee64_dec_n
    inc a
    sta f:_ieee64_dec_n
    bra double_next
double_no_append:
    rep #$20
.a16
double_next:
    dec z:EXP
    bne double_loop
    bra finish
negative_exp:
    eor #$ffff
    inc a
    sta z:EXP
five_loop:
    lda f:_ieee64_dec_n
    tay
    ldx #0
    sep #$20
.a8
    stz z:TEMP
five_digit:
    lda f:_ieee64_dec_digits,x
    lsr a
    sta z:TEMP+1
    lda z:TEMP
    bcc five_store
    clc
    adc #5
five_store:
    sta f:_ieee64_dec_digits,x
    lda z:TEMP+1
    sta z:TEMP
    inx
    dey
    bne five_digit
    lda z:TEMP
    beq five_no_append
    sta f:_ieee64_dec_digits,x
    rep #$20
.a16
    lda f:_ieee64_dec_n
    inc a
    sta f:_ieee64_dec_n
    bra five_next
five_no_append:
    rep #$20
.a16
five_next:
    dec z:EXP
    bne five_loop
finish:
    lda #0
    ply
    rts
zero:
    lda #1
    sta f:_ieee64_dec_n
    lda #0
    sta f:_ieee64_dec_scale
    sep #$20
.a8
    sta f:_ieee64_dec_digits
    rep #$20
.a16
    bra finish
special:
    lda z:L+6
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    beq infinity
    lda #2
    ply
    rts
infinity:
    lda #1
    ply
    rts
