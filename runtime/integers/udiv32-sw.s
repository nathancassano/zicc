.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export udiv32_software
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
udiv32_software:
    lda z:R+2
    beq :+
    jmp .loword(udiv32_wide_divisor)
:
    lda z:R
    beq @zero_divisor
    cmp #$0100
    bne udiv32_word
    ; Divide by 256 by separating the low byte from the other three
    lda z:L
    and #$00FF
    sta z:T
    stz z:T+2
    lda z:L+1
    sta z:L
    lda z:L+2
    xba
    and #$00FF
    sta z:L+2
    tax
    lda z:L
    rts
@zero_divisor:
    ; Preserve the previous restoring loop's deterministic zero case
    lda z:L
    sta z:T
    lda z:L+2
    sta z:T+2
    lda #$FFFF
    sta z:L
    sta z:L+2
    tax
    rts

udiv32_word:
    ; Consume one dividend word at a time with the remainder in A
    ; X visits the high word (+2) and low word (+0), or just the low word
    phy
    lda z:L+2
    cmp z:R
    bcc @short
    lda #0
    ldx #2
    bra @word
@short:
    stz z:L+2
    ldx #0
@word:
    ldy #16
@bit:
    asl z:L,x
    rol a
    bcs @subtract           ; a shifted-out 17th bit implies A >= R
    cmp z:R
    bcc @next
@subtract:
    sbc z:R
    inc z:L,x
@next:
    dey
    bne @bit
    dex
    dex
    bpl @word
    sta z:T
    stz z:T+2
    ply
    bra udiv32_result

udiv32_wide_divisor:
    ; A long divisor bounds the quotient to one word
    lda z:L+2
    cmp z:R+2
    bcc @zero_quotient
    bne @enough
    lda z:L
    cmp z:R
    bcc @zero_quotient
@enough:
    bit z:R+2
    bmi @one_quotient
    lda z:L+2
    sta z:T
    stz z:L+2
    ldx #16
    lda #0
@bit:
    asl z:L
    rol z:T
    rol a                   ; the divisor is below $80000000 here
    cmp z:R+2
    bcc @next
    bne @subtract_high
    lda z:T
    cmp z:R
    bcc @reload_high
    sbc z:R
    sta z:T
    lda #0
    bra @accept
@reload_high:
    lda z:R+2
    bra @next
@subtract_high:
    sta z:T+2
    lda z:T
    sbc z:R
    sta z:T
    lda z:T+2
    sbc z:R+2
@accept:
    inc z:L
@next:
    dex
    bne @bit
    sta z:T+2
    bra udiv32_result
@zero_quotient:
    lda z:L
    sta z:T
    lda z:L+2
    sta z:T+2
    lda #0
    bra @short_result
@one_quotient:
    sec
    lda z:L
    sbc z:R
    sta z:T
    lda z:L+2
    sbc z:R+2
    sta z:T+2
    lda #1
@short_result:
    sta z:L
    stz z:L+2
    ldx #0
    rts
udiv32_result:
    lda z:L
    ldx z:L+2
    rts
