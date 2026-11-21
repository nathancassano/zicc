; IEEE binary32 comparison kernel
; Compare code: -1 less, 0 equal, +1 greater, +2 unordered
.setcpu "65816"
.importzp __arith_lhs, __arith_rhs
.a16
.i16
al = __arith_lhs
ah = __arith_lhs+2
bl = __arith_rhs
bh = __arith_rhs+2

.segment "CODE"
.export ieee_fcmp32_core
; Return zero for equality, nonzero otherwise. Preserve the full comparator
; for cases that can contain signed zeros or NaNs
.export __fcmp32_equal
__fcmp32_equal:
    lda z:ah
    cmp z:bh
    bne unequal_high
    asl a                        ; unsigned magnitude with the sign shifted out
    cmp #$ff00
    bcs ieee_fcmp32_core
    lda z:al
    eor z:bl
    ldx #0
    rts
unequal_high:
    ; Distinct encodings with different high words can compare equal only
    ; for the two zeros. A NaN already has a nonzero magnitude
    eor z:bh
    asl a
    bne unequal_return
    lda z:ah
    asl a
    ora z:al
    ora z:bl
unequal_return:
    ldx #0
    rts

ieee_fcmp32_core:
    ldx #0                       ; all result codes fit the low word
    ; NaNs return the unordered code before comparing signs or magnitude
    lda z:ah
    asl a                        ; unsigned magnitude with the sign shifted out
    cmp #$ff00
    bcc cmp_b
    bne cmp_unordered
    lda z:al
    bne cmp_unordered
cmp_b:
    lda z:bh
    asl a                        ; unsigned magnitude with the sign shifted out
    cmp #$ff00
    bcc cmp_ordered
    bne cmp_unordered
    lda z:bl
    bne cmp_unordered
cmp_ordered:
    lda z:ah
    eor z:bh
    bmi cmp_sign
    lda z:ah
    cmp z:bh
    bcc cmp_low
    bne cmp_high
    lda z:al
    cmp z:bl
    bcc cmp_low
    bne cmp_high
cmp_equal:
    lda #0
    rts
cmp_sign:
    ; Only opposite-sign values need the signed-zero equality check
    lda z:ah
    ora z:bh
    asl a
    ora z:al
    ora z:bl
    beq cmp_equal
    lda z:ah
    bmi cmp_minus
    bra cmp_plus
cmp_low:
    lda z:ah
    bmi cmp_plus
cmp_minus:
    lda #$ffff
    rts
cmp_high:
    lda z:ah
    bmi cmp_minus
cmp_plus:
    lda #1
    rts
cmp_unordered:
    lda #2
    rts
