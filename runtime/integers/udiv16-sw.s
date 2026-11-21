.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export udiv16_software
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
udiv16_software:
    ; C division by zero remains undefined; retain the deterministic result
    lda z:R
    bne @large
    lda z:L
    sta z:T
    lda #$FFFF
    sta z:L
    rts
@large:
    cmp #$0100
    beq @byte_boundary
    lda z:L
    cmp z:R
    bcc @zero_quotient
    bit z:R
    bpl @restore
    ; A divisor with bit 15 set has at most one quotient bit
    sbc z:R
    sta z:T
    lda #1
    sta z:L
    rts
@zero_quotient:
    sta z:T
    stz z:L
    lda #0
    rts
@byte_boundary:
    lda z:L
    and #$00FF
    sta z:T
    lda z:L
    xba
    and #$00FF
    sta z:L
    rts
@restore:
    ; R>=256 proves a byte quotient for every word dividend. Consume its
    ; high byte as the initial remainder, then shift only eight low bits
    ; The consumed prefix fits a word, so ROL A cannot lose a 17th bit
    phx
    lda z:L
    xba
    and #$00FF
    sta z:T
    lda z:L
    xba
    and #$FF00
    sta z:L
    lda z:T
    ldx #8
    asl z:L
@bit:
    rol a
    cmp z:R
    bcc @skip
    sbc z:R
@skip:
    ; Carry holds the quotient bit. Rotating it in also fetches the
    ; next dividend bit for the following remainder shift
    rol z:L
    dex
    bne @bit
    sta z:T
    lda z:L
    plx
    rts
