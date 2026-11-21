; Binary64 comparison, native A/X/Y 16-bit. L and R are little-endian
; operands at arithmetic scratch +0 and +8. Return A = -1, 0, 1 or 2
; for less, equal, greater or unordered. X/Y/D/DBR and inputs are preserved
; The unordered result matches the existing binary32 comparison contract
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __dcmp, __dcmp_signal
.import __fp_raise
L = __arith_lhs
R = __arith_lhs+8
.segment "CODE"
__dcmp_signal:
    jsr .loword(__dcmp)
    cmp #2
    bne @return
    lda #1
    jsr .loword(__fp_raise)
    lda #2
@return:
    rts
__dcmp:
    lda z:L+6
    and #$7fff
    cmp #$7ff0
    bcc @check_right
    bne @unordered
    lda z:L
    ora z:L+2
    ora z:L+4
    bne @unordered
@check_right:
    lda z:R+6
    and #$7fff
    cmp #$7ff0
    bcc @ordered
    bne @unordered
    lda z:R
    ora z:R+2
    ora z:R+4
    bne @unordered
@ordered:
    lda z:L+6
    eor z:R+6
    bmi @different_sign
    lda z:L+6
    cmp z:R+6
    bcc @low
    bne @high
    lda z:L+4
    cmp z:R+4
    bcc @low
    bne @high
    lda z:L+2
    cmp z:R+2
    bcc @low
    bne @high
    lda z:L
    cmp z:R
    bcc @low
    bne @high
@equal:
    lda #0
    rts
@different_sign:
    ; Only opposite signs need an explicit check for equal zero magnitudes
    lda z:L+6
    ora z:R+6
    and #$7fff
    ora z:L
    ora z:L+2
    ora z:L+4
    ora z:R
    ora z:R+2
    ora z:R+4
    beq @equal
    lda z:L+6
    bmi @minus
    bra @plus
@low:
    lda z:L+6
    bmi @plus
@minus:
    lda #$ffff
    rts
@high:
    lda z:L+6
    bmi @minus
@plus:
    lda #1
    rts
@unordered:
    lda z:L+6
    and #$7ff8
    cmp #$7ff0
    bne @check_signaling_right
    lda z:L+6
    and #7
    ora z:L+4
    ora z:L+2
    ora z:L
    bne @invalid
@check_signaling_right:
    lda z:R+6
    and #$7ff8
    cmp #$7ff0
    bne @return_unordered
    lda z:R+6
    and #7
    ora z:R+4
    ora z:R+2
    ora z:R
    beq @return_unordered
@invalid:
    lda #1
    jsr .loword(__fp_raise)
@return_unordered:
    lda #2
    rts
