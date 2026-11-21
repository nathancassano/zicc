; IEEE binary64 to binary32, round to nearest, ties to even. Input binary64
; at scratch +0..7; output binary32 at +0..3. Gradual underflow, overflow,
; signed zeros, infinities and quieted NaN payloads are handled. Scratch
; +8..+23 and A/flags are clobbered; X/Y/D/DBR are preserved
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __fp_round_increment, __fp_round_mode, __fp_raise
.export __ftrunc64_32
L = __arith_lhs
M = __arith_lhs+8
EX = __arith_lhs+16
SG = __arith_lhs+18
GUARD = __arith_lhs+20
STICKY = __arith_lhs+22
.segment "CODE"
__ftrunc64_32:
    phx
    lda z:L+6
    and #$8000
    sta z:SG
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    cmp #2047
    bne :+
    jmp .loword(@special)
:
    cmp #1151
    bcc :+
    jmp .loword(@overflow)
:
    cmp #873
    bcs :+
    jmp .loword(@tiny_or_zero)
:
    cmp #897
    bcc @subnormal
    sec
    sbc #896
    sta z:EX
    ldx #29
    bra @prepare
@subnormal:
    ; 29 plus the distance below the smallest normal float exponent
    eor #$ffff
    clc
    adc #927
    tax
    stz z:EX
@prepare:
    lda z:L
    sta z:M
    lda z:L+2
    sta z:M+2
    lda z:L+4
    sta z:M+4
    lda z:L+6
    and #$000f
    ora #$0010
    sta z:M+6
    stz z:GUARD
    ; Every path shifts at least 29 bits. Drop a whole word at once,
    ; retaining its nonzero state as sticky before the remaining bit shifts
    lda z:M
    sta z:STICKY
    lda z:M+2
    sta z:M
    lda z:M+4
    sta z:M+2
    lda z:M+6
    sta z:M+4
    stz z:M+6
    txa
    sec
    sbc #16
    tax
@shift:
    lda z:STICKY
    ora z:GUARD
    sta z:STICKY
    lsr z:M+6
    ror z:M+4
    ror z:M+2
    ror z:M
    lda #0
    adc #0
    sta z:GUARD
    dex
    bne @shift
    ldx z:STICKY
    lda z:M
    and #1
    asl a
    ora z:GUARD
    asl a
    asl a
    cpx #0
    beq :+
    ora #1
:
    ldx z:SG
    jsr .loword(__fp_round_increment)
    bcc @pack
    inc z:M
    bne @round_check
    inc z:M+2
@round_check:
    lda z:M+2
    bit #$0100
    beq @pack
    lsr z:M+2
    ror z:M
    inc z:EX
    lda z:EX
    cmp #255
    jcs @overflow
@pack:
    lda z:M
    sta z:L
    lda z:M+2
    and #$007f
    sta z:L+2
    lda z:EX
    beq @subnormal_pack
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    asl a
    ora z:L+2
    bra @rounded_sign
@subnormal_pack:
    ; Rounding may carry a subnormal into the smallest normal
    lda z:M+2
    and #$0080
    ora z:L+2
@rounded_sign:
    ora z:SG
    sta z:L+2
    lda z:STICKY
    ora z:GUARD
    beq @return
    lda z:L+2
    and #$7f80
    beq :+
    lda #$0010
    bra :++
:
    lda #$0018
:
    jsr .loword(__fp_raise)
    bra @return
@sign:
    ora z:SG
    sta z:L+2
@return:
    plx
    rts
@special:
    lda z:L+6
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    jeq @infinity
    lda z:L+6
    bit #$0008
    bne :+
    lda #1
    jsr .loword(__fp_raise)
:
    ; Retain the top 23 payload bits and force the binary32 quiet bit
    lda z:L+2
    and #$e000
    xba
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    sta z:M
    lda z:L+4
    asl a
    asl a
    asl a
    ora z:M
    sta z:L
    lda z:L+4
    xba
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    and #7
    sta z:M
    lda z:L+6
    and #$000f
    asl a
    asl a
    asl a
    ora z:M
    ora #$7fc0
    ora z:SG
    sta z:L+2
    plx
    rts
@infinity:
    stz z:L
    lda #$7f80
    jmp .loword(@sign)
@overflow:
    lda #$0014
    jsr .loword(__fp_raise)
    lda f:__fp_round_mode
    beq @infinity
    ldx z:SG
    lda #1
    jsr .loword(__fp_round_increment)
    bcs @infinity
    lda #$ffff
    sta z:L
    lda #$7f7f
    jmp .loword(@sign)
@tiny_or_zero:
    lda z:L+6
    and #$7fff
    ora z:L+4
    ora z:L+2
    ora z:L
    beq @zero
    lda #$0018
    jsr .loword(__fp_raise)
    ldx z:SG
    lda #1
    jsr .loword(__fp_round_increment)
    lda #0
    adc #0
    sta z:L
    lda #0
    jmp .loword(@sign)
@zero:
    stz z:L
    lda #0
    jmp .loword(@sign)
