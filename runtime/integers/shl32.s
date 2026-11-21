.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __shl32
L=__arith_lhs
R=__arith_rhs
.segment "CODE"
__shl32:
    lda z:R
    and #31
    cmp #8
    bcc @small
    cmp #16
    bcc @byte
    ; The low source word is the entire surviving high word. Shift it in A
    and #15
    cmp #8
    bcs @large_byte
    tax
    lda z:L
@large_loaded:
    stz z:L
    cpx #0
    beq @large_done
@large_shift:
    asl a
    dex
    bne @large_shift
@large_done:
    sta z:L+2
    tax
    lda #0
    rts
@large_byte:
    and #7
    tax
    lda z:L
    xba
    and #$FF00
    bra @large_loaded
@byte:
    and #7
    tax
    lda z:L+1
    sta z:L+2
    lda z:L
    xba
    and #$FF00
    bra @small_loaded
@small:
    tax
    lda z:L
@small_loaded:
    cpx #0
    beq @done
@shift:
    asl a
    rol z:L+2
    dex
    bne @shift
@done:
    sta z:L
    ldx z:L+2
    rts
