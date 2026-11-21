; IEEE binary64 addition/subtraction: round to nearest, ties to even,
; gradual underflow. Inputs at arithmetic scratch +0..7 and +8..15;
; result at +0..7. Scratch +8..+27 and A/X/flags are clobbered
; Y/D/DBR are preserved. Like binary32, this routine returns a fixed
; quiet NaN for NaN inputs and invalid operations
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __fp_round_increment, __fp_round_mode, __fp_overflow, __fp_raise
.export __dadd, __dsub
L = __arith_lhs
R = __arith_lhs+8
EA = __arith_lhs+16
EB = __arith_lhs+18
SA = __arith_lhs+20
SB = __arith_lhs+22
MODE = __arith_lhs+24
TEMP = __arith_lhs+26
.segment "CODE"
__dadd:
    stz z:MODE
    bra add64_enter
__dsub:
    lda #$8000
    sta z:MODE
add64_enter:
    lda z:L+6
    and #$8000
    sta z:SA
    lda z:R+6
    eor z:MODE
    and #$8000
    sta z:SB
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    sta z:EA
    lda z:R+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    sta z:EB
    lda z:EA
    cmp #2047
    bne add64_check_b
    lda z:L+6
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    jne add64_lhs_nan
add64_check_b:
    lda z:EB
    cmp #2047
    bne add64_infinities
    lda z:R+6
    and #$000f
    ora z:R+4
    ora z:R+2
    ora z:R
    jne add64_rhs_nan
add64_infinities:
    lda z:EA
    cmp #2047
    bne add64_right_inf
    lda z:EB
    cmp #2047
    bne add64_infinity
    lda z:SA
    eor z:SB
    jne add64_invalid
    bra add64_infinity
add64_right_inf:
    lda z:EB
    cmp #2047
    bne add64_finite
    lda z:SB
    sta z:SA
add64_infinity:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda z:SA
    ora #$7ff0
    sta z:L+6
    rts
add64_finite:
    ; Unpack the 53-bit significands and reserve three low rounding bits
    lda z:L+6
    and #$000f
    ldx z:EA
    bne :+
    inc z:EA
    bra :++
:   ora #$0010
:   sta z:L+6
    lda z:R+6
    and #$000f
    ldx z:EB
    bne :+
    inc z:EB
    bra :++
:   ora #$0010
:   sta z:R+6
    ldx #3
:   asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    asl z:R
    rol z:R+2
    rol z:R+4
    rol z:R+6
    dex
    bne :-
    ; Put the larger exponent in L before alignment
    lda z:EA
    cmp z:EB
    bcs add64_aligned_order
    lda z:EA
    ldx z:EB
    stx z:EA
    sta z:EB
    lda z:SA
    ldx z:SB
    stx z:SA
    sta z:SB
    jsr .loword(add64_swap)
add64_aligned_order:
    lda z:EA
    sec
    sbc z:EB
    beq add64_operate
    cmp #64
    bcc add64_shift_count
    lda z:R
    ora z:R+2
    ora z:R+4
    ora z:R+6
    beq add64_operate
    lda #1
    sta z:R
    stz z:R+2
    stz z:R+4
    stz z:R+6
    bra add64_operate
add64_shift_count:
    tax
add64_align_words:
    cpx #16
    bcc add64_align
    ; Shift a whole word and jam its nonzero bits into the new low bit
    lda z:R
    beq :+
    lda #1
:
    sta z:TEMP
    lda z:R+2
    ora z:TEMP
    sta z:R
    lda z:R+4
    sta z:R+2
    lda z:R+6
    sta z:R+4
    stz z:R+6
    txa
    sec
    sbc #16
    tax
    beq add64_operate
    bra add64_align_words
add64_align:
    lsr z:R+6
    ror z:R+4
    ror z:R+2
    ror z:R
    bcc :+
    lda z:R
    ora #1
    sta z:R
:   dex
    bne add64_align
add64_operate:
    lda z:SA
    eor z:SB
    bne add64_subtract
    clc
    lda z:L
    adc z:R
    sta z:L
    lda z:L+2
    adc z:R+2
    sta z:L+2
    lda z:L+4
    adc z:R+4
    sta z:L+4
    lda z:L+6
    adc z:R+6
    sta z:L+6
    bit #$0100
    jeq add64_round
    ; The addition carried into bit 56; shift right with sticky
    jsr .loword(add64_shift_l)
    inc z:EA
    jmp .loword(add64_round)
add64_subtract:
    ; Compare magnitudes and subtract the smaller from the larger
    lda z:L+6
    cmp z:R+6
    bcc add64_reverse
    bne add64_difference
    lda z:L+4
    cmp z:R+4
    bcc add64_reverse
    bne add64_difference
    lda z:L+2
    cmp z:R+2
    bcc add64_reverse
    bne add64_difference
    lda z:L
    cmp z:R
    bcc add64_reverse
    bne add64_difference
    ; Exact cancellation takes the negative sign only in downward mode
    stz z:L
    stz z:L+2
    stz z:L+4
    stz z:L+6
    lda f:__fp_round_mode
    cmp #1
    bne :+
    lda #$8000
    sta z:L+6
:
    rts
add64_reverse:
    jsr .loword(add64_swap)
    lda z:SB
    sta z:SA
add64_difference:
    sec
    lda z:L
    sbc z:R
    sta z:L
    lda z:L+2
    sbc z:R+2
    sta z:L+2
    lda z:L+4
    sbc z:R+4
    sta z:L+4
    lda z:L+6
    sbc z:R+6
    sta z:L+6
add64_normalize:
    lda z:L+6
    bit #$0080
    bne add64_round
    lda z:EA
    cmp #1
    beq add64_round
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    dec z:EA
    bra add64_normalize
add64_round:
    lda z:L
    bit #7
    beq :+
    lda #$0010
    jsr .loword(__fp_raise)
:
    ldx z:SA
    lda z:L
    jsr .loword(__fp_round_increment)
    bcc add64_pack
    clc
    lda z:L
    adc #8
    sta z:L
    lda z:L+2
    adc #0
    sta z:L+2
    lda z:L+4
    adc #0
    sta z:L+4
    lda z:L+6
    adc #0
    sta z:L+6
    bit #$0100
    beq add64_pack
    jsr .loword(add64_shift_l)
    inc z:EA
add64_pack:
    lda z:EA
    cmp #2047
    jcs add64_overflow
    ; Exponent one with no hidden bit is encoded as subnormal exponent zero
    cmp #1
    bne :+
    lda z:L+6
    bit #$0080
    bne :+
    stz z:EA
:
    ldx #3
:   lsr z:L+6
    ror z:L+4
    ror z:L+2
    ror z:L
    dex
    bne :-
    lda z:L+6
    and #$000f
    sta z:TEMP
    lda z:EA
    asl a
    asl a
    asl a
    asl a
    ora z:TEMP
    ora z:SA
    sta z:L+6
    rts
add64_overflow:
    ldx z:SA
    jsr .loword(__fp_overflow)
    rts
add64_lhs_nan:
    lda z:L+6
    bit #$0008
    beq add64_invalid
    ; A quiet left NaN can coexist with a signaling right NaN
    lda z:EB
    cmp #2047
    bne add64_nan
    lda z:R+6
    and #$000f
    ora z:R+4
    ora z:R+2
    ora z:R
    beq add64_nan
add64_rhs_nan:
    lda z:R+6
    bit #$0008
    bne add64_nan
add64_invalid:
    lda #1
    jsr .loword(__fp_raise)
add64_nan:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$7ff8
    sta z:L+6
    rts
; Internal routines preserve Y, D and DBR
add64_shift_l:
    lsr z:L+6
    ror z:L+4
    ror z:L+2
    ror z:L
    bcc :+
    lda z:L
    ora #1
    sta z:L
:
    rts
add64_swap:
    lda z:L
    ldx z:R
    sta z:R
    stx z:L
    lda z:L+2
    ldx z:R+2
    sta z:R+2
    stx z:L+2
    lda z:L+4
    ldx z:R+4
    sta z:R+4
    stx z:L+4
    lda z:L+6
    ldx z:R+6
    sta z:R+6
    stx z:L+6
    rts
