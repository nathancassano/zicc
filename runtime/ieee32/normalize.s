; Normalize finite nonzero multiplicands/divisors, including subnormal inputs
.setcpu "65816"
.importzp __arith_lhs
.a16
.i16
ea = __arith_lhs+8
eb = __arith_lhs+10
ma = __arith_lhs+14
mb = __arith_lhs+18

.segment "CODE"
.export ieee32_normalize_ab
ieee32_normalize_ab:
    lda z:ma+1                   ; bit 23 is the sign of this word
    bmi normalize_b
    ; A zero high word allows an exact byte shift towards bit 23
    ; Nonzero finite inputs are guaranteed by both callers
    lda z:ma+2
    bne normalize_ab_bit
    lda z:ma+1
    sta z:ma+2
    lda z:ma
    xba
    and #$ff00
    sta z:ma
    lda z:ea
    sec
    sbc #8
    sta z:ea
    bra ieee32_normalize_ab
normalize_ab_bit:
    asl z:ma
    rol z:ma+2
    dec z:ea
    lda z:ma+2
    bit #$80
    beq normalize_ab_bit
normalize_b:
    lda z:mb+1                   ; bit 23 is the sign of this word
    bmi normalize_done
    ; A zero high word allows an exact byte shift towards bit 23
    ; Nonzero finite inputs are guaranteed by both callers
    lda z:mb+2
    bne normalize_b_bit
    lda z:mb+1
    sta z:mb+2
    lda z:mb
    xba
    and #$ff00
    sta z:mb
    lda z:eb
    sec
    sbc #8
    sta z:eb
    bra normalize_b
normalize_b_bit:
    asl z:mb
    rol z:mb+2
    dec z:eb
    lda z:mb+2
    bit #$80
    beq normalize_b_bit
normalize_done:
    rts
