; Shared power-of-two scaling macro for ldexp/ldexpf
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

BITS = __arith_lhs
SIGN = BITS+8
SCALE = BITS+10
STICKY = BITS+12
ROUND = BITS+14

.macro scale_float words, exponent_shift, exponent_mask, fraction_mask, precision, wide
    .local positive, save_scale, finite, special, normalize, subnormal
    .local shift_count, shift_more, guard_bit, rounding, increment, report, tiny
    .local overflow, attach_sign, done

    ; Clamping outside either format's entire exponent span avoids signed wrap
    cmp #$8000
    bcc positive
    cmp #.loword(-4096)
    bcs save_scale
    lda #.loword(-4096)
    bra save_scale
positive:
    cmp #4096
    bcc save_scale
    lda #4096
save_scale:
    sta z:SCALE
    .if wide
        phx
    .endif
    .repeat words, i
        lda 3+LIBC_RETURN_EXTRA+2*wide+2*i,s
        sta z:BITS+2*i
    .endrepeat
    and #$8000
    sta z:SIGN
    lda z:BITS+2*(words-1)
    and #exponent_mask
    cmp #exponent_mask
    jeq special
    .repeat exponent_shift
        lsr a
    .endrepeat
    tax
    lda z:BITS+2*(words-1)
    and #fraction_mask
    sta z:BITS+2*(words-1)
    cpx #0
    bne finite
    .repeat words-1, i
        ora z:BITS+2*i
    .endrepeat
    jeq attach_sign
    ldx #1
normalize:
    asl z:BITS
    .repeat words-1, i
        rol z:BITS+2*(i+1)
    .endrepeat
    dex
    lda z:BITS+2*(words-1)
    bit #(fraction_mask+1)
    beq normalize
    and #fraction_mask
    sta z:BITS+2*(words-1)
finite:
    txa
    clc
    adc z:SCALE
    bmi subnormal
    beq subnormal
    cmp #(exponent_mask >> exponent_shift)
    jcs overflow
    .repeat exponent_shift
        asl a
    .endrepeat
    ora z:BITS+2*(words-1)
    sta z:BITS+2*(words-1)
    jmp .loword(attach_sign)

subnormal:
    eor #$ffff
    inc a
    inc a
    cmp #(precision+1)
    bcc shift_count
    lda #(precision+1)
shift_count:
    tax
    lda z:BITS+2*(words-1)
    ora #(fraction_mask+1)
    sta z:BITS+2*(words-1)
    stz z:STICKY
shift_more:
    lsr z:BITS+2*(words-1)
    .repeat words-1, i
        ror z:BITS+2*(words-2-i)
    .endrepeat
    dex
    beq guard_bit
    bcc shift_more
    inc z:STICKY
    bra shift_more
guard_bit:
    ; Round once from the last discarded bit and the sticky tail
    lda #0
    rol a
    asl a
    asl a
    ldx z:STICKY
    beq :+
    ora #1
:
    cmp #0
    jeq attach_sign
    sta z:ROUND
    lda z:BITS
    and #1
    .repeat 3
        asl a
    .endrepeat
    ora z:ROUND
    .if wide
        ldx z:SIGN
        .if LIBC_RETURN_EXTRA
            jsl __fp_round_increment
        .else
            jsr .loword(__fp_round_increment)
        .endif
        bcc report
    .else
        cmp #12
        bcs increment
        and #7
        cmp #5
        bcc report
    .endif
increment:
    sec
    .repeat words, i
        lda z:BITS+2*i
        adc #0
        sta z:BITS+2*i
    .endrepeat
report:
    lda z:BITS+2*(words-1)
    bit #(fraction_mask+1)
    beq tiny
    .if wide
        lda #$0010
        .if LIBC_RETURN_EXTRA
            jsl __fp_raise
        .else
            jsr .loword(__fp_raise)
        .endif
    .endif
    bra attach_sign
tiny:
    lda #34
    sta a:.loword(_errno)
    .if wide
        lda #$0018
        .if LIBC_RETURN_EXTRA
            jsl __fp_raise
        .else
            jsr .loword(__fp_raise)
        .endif
    .endif
    bra attach_sign

overflow:
    lda #34
    sta a:.loword(_errno)
    .if wide
        ldx z:SIGN
        .if LIBC_RETURN_EXTRA
            jsl __fp_overflow
        .else
            jsr .loword(__fp_overflow)
        .endif
        bra done
    .else
        stz z:BITS
        lda #exponent_mask
        sta z:BITS+2
        bra attach_sign
    .endif

special:
    lda z:BITS+2*(words-1)
    and #fraction_mask
    .repeat words-1, i
        ora z:BITS+2*i
    .endrepeat
    beq done
    lda z:BITS+2*(words-1)
    bit #((fraction_mask+1)/2)
    bne done
    ora #((fraction_mask+1)/2)
    sta z:BITS+2*(words-1)
    .if wide
        lda #1
        .if LIBC_RETURN_EXTRA
            jsl __fp_raise
        .else
            jsr .loword(__fp_raise)
        .endif
    .endif
    bra done
attach_sign:
    lda z:BITS+2*(words-1)
    ora z:SIGN
    sta z:BITS+2*(words-1)
done:
    .if wide
        plx
    .else
        ldx z:BITS+2
        lda z:BITS
    .endif
.if LIBC_RETURN_EXTRA
    rtl
.else
    rts
.endif
.endmacro
