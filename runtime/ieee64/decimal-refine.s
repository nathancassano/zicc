; Refine a nonnegative binary64 estimate against exact source decimal digits
; Inputs in arithmetic scratch: +0..7 estimate (finite or +infinity),
; +8..11 padded far pointer to first significant digit, +12..15 padded far
; end pointer, +16..19 signed 32-bit decimal-point exponent. Input digits
; may contain a decimal point. Return correctly rounded binary64 in +0..7
; X/A/flags and arithmetic scratch clobbered; Y/D/DBR preserved. Native
; A16/X16, D=0, DBR=$7E. The decimal workspace is shared. The caller handles
; lexical parsing, sign, zero, and errno. The seed need only be nonnegative;
; a near seed keeps the midpoint correction loop short
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __ieee64_decimal_scaled, __ieee64_decimal_compare
.import __fp_round_mode, __fp_raise
.export __ieee64_decimal_refine, __ieee64_decimal_refine_signed
CAND = 1
FIRST = 9
END = 13
EXP = 17
MID = 21
SIGN = 29
FRAME = 30
.segment "CODE"
__ieee64_decimal_refine:
    lda #$ffff              ; internal nearest-only estimate correction
__ieee64_decimal_refine_signed:
    tax
    phy
    tsc
    sec
    sbc #FRAME
    tcs
    tay
    txa
    sta a:SIGN,y
    .repeat 4, I
    lda z:__arith_lhs+I*2
    sta a:CAND+I*2,y
    .endrepeat
    .repeat 2, I
    lda z:__arith_lhs+8+I*2
    sta a:FIRST+I*2,y
    lda z:__arith_lhs+12+I*2
    sta a:END+I*2,y
    lda z:__arith_lhs+16+I*2
    sta a:EXP+I*2,y
    .endrepeat
@again:
    ; Infinity has no upper boundary; its lower boundary is the overflow
    ; midpoint between the maximum finite value and infinity
    lda a:CAND+6,y
    cmp #$7ff0
    beq @lower
    .repeat 4, I
    lda a:CAND+I*2,y
    sta a:MID+I*2,y
    .endrepeat
    jsr .loword(@compare_midpoint)
    bmi @lower
    bne @increase
    lda a:CAND,y
    and #1
    bne @increase
@lower:
    lda a:CAND,y
    ora a:CAND+2,y
    ora a:CAND+4,y
    ora a:CAND+6,y
    jeq @finish
    sec
    lda a:CAND,y
    sbc #1
    sta a:MID,y
    .repeat 3, I
    lda a:CAND+2+I*2,y
    sbc #0
    sta a:MID+2+I*2,y
    .endrepeat
    jsr .loword(@compare_midpoint)
    bmi @decrease
    bne @finish
    lda a:CAND,y
    and #1
    beq @finish
@decrease:
    sec
    lda a:CAND,y
    sbc #1
    sta a:CAND,y
    .repeat 3, I
    lda a:CAND+2+I*2,y
    sbc #0
    sta a:CAND+2+I*2,y
    .endrepeat
    jmp .loword(@again)
@increase:
    clc
    lda a:CAND,y
    adc #1
    sta a:CAND,y
    .repeat 3, I
    lda a:CAND+2+I*2,y
    adc #0
    sta a:CAND+2+I*2,y
    .endrepeat
    jmp .loword(@again)
@finish:
    lda a:SIGN,y
    cmp #$ffff
    jeq @done
    ; Start with the nearest candidate. For directed modes, an exact
    ; comparison with the candidate selects one adjacent encoding at most
    lda a:CAND+6,y
    cmp #$7ff0
    jeq @infinite_candidate
    ora a:CAND+4,y
    ora a:CAND+2,y
    ora a:CAND,y
    beq @above_candidate
    .repeat 4, I
    lda a:CAND+I*2,y
    sta a:MID+I*2,y
    .endrepeat
    ldx #0
    jsr .loword(@compare_boundary)
    jeq @done
    bmi @below_candidate
@above_candidate:
    jsr .loword(@magnitude_mode)
    cmp #2
    jne @inexact
    clc
    lda a:CAND,y
    adc #1
    sta a:CAND,y
    .repeat 3, I
    lda a:CAND+2+I*2,y
    adc #0
    sta a:CAND+2+I*2,y
    .endrepeat
    jmp .loword(@inexact)
@infinite_candidate:
    jsr .loword(@magnitude_mode)
    cmp #1
    jne @inexact
    ; When rounding toward smaller magnitude, overflow occurs only if the
    ; exact input reaches 2^1024. The infinity encoding unpacks to that
    ; finite boundary in the exact comparison below
    .repeat 4, I
    lda a:CAND+I*2,y
    sta a:MID+I*2,y
    .endrepeat
    ldx #0
    jsr .loword(@compare_boundary)
    bmi @below_candidate
    lda #$0014
    jsr .loword(__fp_raise)
@below_candidate:
    jsr .loword(@magnitude_mode)
    cmp #1
    bne @inexact
    sec
    lda a:CAND,y
    sbc #1
    sta a:CAND,y
    .repeat 3, I
    lda a:CAND+2+I*2,y
    sbc #0
    sta a:CAND+2+I*2,y
    .endrepeat
@inexact:
    lda a:CAND+6,y
    and #$7ff0
    beq @tiny
    cmp #$7ff0
    beq @overflow
    lda #$0010
    bra @raise
@tiny:
    lda #$0018
    bra @raise
@overflow:
    lda #$0014
@raise:
    jsr .loword(__fp_raise)
@done:
    .repeat 4, I
    lda a:CAND+I*2,y
    sta z:__arith_lhs+I*2
    .endrepeat
    tya
    clc
    adc #FRAME
    tcs
    ply
    rts

; Return nearest (0), smaller magnitude (1), or larger magnitude (2)
@magnitude_mode:
    lda f:__fp_round_mode
    beq @mode_done
    cmp #3
    beq @smaller
    ldx a:SIGN,y
    beq @mode_done
    eor #3
@mode_done:
    rts
@smaller:
    lda #1
    rts

; Compare input with the midpoint immediately above MID's bit pattern
@compare_midpoint:
    ldx #1
@compare_boundary:
    .repeat 3, I
    lda a:MID+I*2,y
    sta z:__arith_lhs+I*2
    .endrepeat
    lda a:MID+6,y
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    bne :+
    inc a                    ; subnormals use exponent field 1
    bra @subnormal
:
    pha
    lda a:MID+6,y
    and #$000f
    ora #$0010              ; implicit leading significand bit
    sta z:__arith_lhs+6
    pla
    bra @mid_power
@subnormal:
    pha
    lda a:MID+6,y
    and #$000f
    sta z:__arith_lhs+6
    pla
@mid_power:
    sec
    cpx #1
    bne @exact_power
    sec
    sbc #1076
    pha
    asl z:__arith_lhs
    rol z:__arith_lhs+2
    rol z:__arith_lhs+4
    rol z:__arith_lhs+6
    inc z:__arith_lhs
    pla
    bra @compare
@exact_power:
    sec
    sbc #1075
@compare:
    jsr .loword(__ieee64_decimal_scaled)
    lda a:EXP+2,y
    pha
    lda a:EXP,y
    pha
    lda a:END+2,y
    pha
    lda a:END,y
    pha
    lda a:FIRST+2,y
    pha
    lda a:FIRST,y
    pha
    jsr .loword(__ieee64_decimal_compare)
    tax
    tsc
    clc
    adc #12
    tcs
    txa
    rts
