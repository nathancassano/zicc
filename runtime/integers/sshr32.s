.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __sshr32
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__sshr32:
    lda z:R
    and #31
    cmp #8
    bcc @small
    cmp #16
    bcc @byte
    and #15
    cmp #8
    bcs @large_byte
    tax
    lda z:L+2
@large_loaded:
    cpx #0
    beq @large_done
@large_shift:
    cmp #$8000
    ror a
    dex
    bne @large_shift
@large_done:
    sta z:L
    ldx #0
    cmp #$8000
    bcc :+
    ldx #$FFFF
:
    stx z:L+2
    rts
@large_byte:
    and #7
    tax
    lda z:L+2
    xba
    and #$00FF
    eor #$0080
    sec
    sbc #$0080
    bra @large_loaded
@byte:
    and #7
    tax
    lda z:L+1
    sta z:L
    lda z:L+2
    xba
    and #$00FF
    eor #$0080
    sec
    sbc #$0080
    bra @small_loaded
@small:
    tax
    lda z:L+2
@small_loaded:
    cpx #0
    beq @done
@shift:
    cmp #$8000
    ror a
    ror z:L
    dex
    bne @shift
@done:
    sta z:L+2
    tax
    lda z:L
    rts
