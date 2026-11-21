.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __ushr32
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__ushr32:
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
    stz z:L+2
    cpx #0
    beq @large_done
@large_shift:
    lsr a
    dex
    bne @large_shift
@large_done:
    sta z:L
    ldx #0
    rts
@large_byte:
    and #7
    tax
    lda z:L+2
    xba
    and #$00FF
    bra @large_loaded
@byte:
    and #7
    tax
    lda z:L+1
    sta z:L
    lda z:L+2
    xba
    and #$00FF
    bra @small_loaded
@small:
    tax
    lda z:L+2
@small_loaded:
    cpx #0
    beq @done
@shift:
    lsr a
    ror z:L
    dex
    bne @shift
@done:
    sta z:L+2
    tax
    lda z:L
    rts
