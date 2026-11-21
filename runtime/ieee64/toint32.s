; Convert IEEE binary64 to a 32-bit integer, truncating toward zero
; Input is scratch +0..7, result is scratch +0..3. Invalid and out-of-range
; C conversions are undefined; this routine returns zero for exponents outside
; [0,31]. A/flags and scratch +8..+13 are clobbered, X/Y/D/DBR preserved
; Both entries share the implementation: for every defined unsigned input
; the truncated value is nonnegative, so signed magnitude handling is valid
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __fp_raise
.export __fix64_32, __ufix64_32
L = __arith_lhs
SG = __arith_lhs+8
LO = __arith_lhs+10
HI = __arith_lhs+12
.segment "CODE"
__fix64_32:
    phx
    lda #0
    bra fix32_convert
__ufix64_32:
    phx
    lda #1
fix32_convert:
    sta z:SG
    lda z:L+6
    and #$8000
    ora z:SG
    sta z:SG
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    cmp #1023
    jcc @small
    cmp #1055
    jcs @invalid_zero
    ; X = 31 - unbiased exponent. The high 32 bits of the 53-bit
    ; significand suffice because the discarded low bits cannot affect
    ; truncation for any representable 32-bit result
    eor #$ffff
    clc
    adc #1055
    tax
    lda z:L+4
    and #$001f
    xba
    asl a
    asl a
    asl a
    sta z:LO
    lda z:L+2
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    ora z:LO
    sta z:LO
    lda z:L+6
    and #$000f
    ora #$0010
    xba
    asl a
    asl a
    asl a
    sta z:HI
    lda z:L+4
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    ora z:HI
    sta z:HI
    lda z:L+2
    and #$001f
    ora z:L
    beq :+
    lda z:SG
    ora #2
    sta z:SG
:
    cpx #0
    beq @sign
@shift:
    lsr z:HI
    ror z:LO
    bcc :+
    lda z:SG
    ora #2
    sta z:SG
:
    dex
    bne @shift
@sign:
    lda z:SG
    bit #1
    beq @signed
    bmi @invalid
    bra @check_inexact
@signed:
    lda z:HI
    bpl @check_inexact
    lda z:SG
    bpl @invalid
    lda z:HI
    and #$7fff
    ora z:LO
    beq @check_inexact
@invalid:
    lda #1
    jsr .loword(__fp_raise)
    bra @apply_sign
@check_inexact:
    lda z:SG
    bit #2
    beq @apply_sign
    lda #$0010
    jsr .loword(__fp_raise)
@apply_sign:
    lda z:SG
    bpl @store
    sec
    lda #0
    sbc z:LO
    sta z:LO
    lda #0
    sbc z:HI
    sta z:HI
@store:
    lda z:LO
    sta z:L
    lda z:HI
    sta z:L+2
    plx
    rts
@small:
    lda z:L+6
    and #$7fff
    ora z:L
    ora z:L+2
    ora z:L+4
    beq @zero
    lda #$0010
    bra @raise_zero
@invalid_zero:
    lda #1
@raise_zero:
    jsr .loword(__fp_raise)
@zero:
    stz z:L
    stz z:L+2
    plx
    rts
