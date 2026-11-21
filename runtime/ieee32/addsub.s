; IEEE binary32 addition and subtraction kernels
.setcpu "65816"
.importzp __arith_lhs, __arith_rhs
.import unpack_checked, ieee32_pack, ieee32_right_a, ieee32_invalid
.macro far_beq target
    bne :+
    jmp .loword(target)
:
.endmacro
.macro far_bne target
    beq :+
    jmp .loword(target)
:
.endmacro
.a16
.i16
ea = __arith_lhs+8
eb = __arith_lhs+10
sg = __arith_lhs+12
ma = __arith_lhs+14
mb = __arith_lhs+18
tmp = __arith_lhs+22
sa = __arith_lhs+30
sb = __arith_lhs+28
al = __arith_lhs
ah = __arith_lhs+2
bl = __arith_rhs
bh = __arith_rhs+2

.segment "CODE"
.export ieee_fsub32_core, ieee_fadd32_core
ieee_fsub32_core:
    lda z:bh
    eor #$8000
    sta z:bh
ieee_fadd32_core:
    jsr .loword(unpack_checked)
    lda z:ea
    cmp #255
    bne add_binf
    lda z:eb
    cmp #255
    far_bne return_a
    lda z:sa
    cmp z:sb
    beq :+
    jmp .loword(ieee32_invalid)
:
    jmp .loword(return_a)
add_binf:
    lda z:eb
    cmp #255
    far_beq return_b
    ; Larger magnitude goes first, so subtraction is always nonnegative
    ; Shift away the sign bit; unsigned order of all magnitude bits is preserved
    lda z:ah
    asl a
    sta z:tmp
    txa                         ; unpack_checked leaves the raw rhs high word in X
    asl a
    cmp z:tmp
    bcc add_ordered
    bne add_swap
    lda z:bl
    cmp z:al
    bcc add_ordered
    bne add_swap
    txa
    cmp z:ah
    bne add_swap
    and #$7f80
    beq add_double_subnormal
    cmp #$7f00
    bcs add_swap
    ; Equal normal operands can double exactly without aligning significands
    lda z:ah
    clc
    adc #$0080
    tax
    lda z:al
    rts
add_double_subnormal:
    ; Both raw words match. For signed zero, X already carries the sign
    ; and the zero fraction in A is the complete low-word result
    lda z:ma
    ora z:ma+2
    beq add_return
    ; Add the unsigned fraction to the original signed high word
    ; The doubled subnormal can carry into exponent bit zero
    asl z:ma
    lda z:ah
    adc z:ma+2
    tax
    lda z:ma
add_return:
    rts
add_swap:
    lda z:ma
    ldx z:mb
    sta z:mb
    stx z:ma
    lda z:ma+2
    ldx z:mb+2
    sta z:mb+2
    stx z:ma+2
    lda z:ea
    ldx z:eb
    sta z:eb
    stx z:ea
    lda z:sb                      ; sign of the larger magnitude
    sta z:sa
add_ordered:
    lda z:ma
    asl a
    rol z:ma+2
    asl a
    rol z:ma+2
    asl a
    rol z:ma+2
    sta z:ma
    lda z:mb
    asl a
    rol z:mb+2
    asl a
    rol z:mb+2
    asl a
    rol z:mb+2
    sta z:mb
    lda z:ea
    sec
    sbc z:eb
    tax
    beq add_aligned
    jsr .loword(shift_b)
add_aligned:
    ldx z:sa
    lda z:sg                      ; unpack saved the XOR of both signs
    stx z:sg
    bne add_subtract
    clc
    lda z:ma
    adc z:mb
    sta z:ma
    lda z:ma+2
    adc z:mb+2
    sta z:ma+2
    bit #$0800
    bne :+
    jmp .loword(ieee32_pack)
:
    jsr .loword(ieee32_right_a)
    inc z:ea
    jmp .loword(ieee32_pack)
add_subtract:
    sec
    lda z:ma
    sbc z:mb
    sta z:ma
    lda z:ma+2
    sbc z:mb+2
    sta z:ma+2
    ora z:ma
    bne add_normalize
    ; Exact opposite-sign cancellation is always positive zero in RNE
    lda #0
    tax
    rts
add_normalize:
    lda z:ma+2
    bit #$0400
    bne add_pack
    bit #$03f8
    bne add_normalize_tail
    lda z:ea
    cmp #1
    beq add_pack
    ; Eight left shifts are safe only below bit 19 and above exponent 8
    ; Keep exponent 1 as the floor so subnormal cancellation stays exact
    cmp #9
    bcc add_normalize_bit
    lda z:ma+2
    cmp #8
    bcs add_normalize_bit
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
    bra add_normalize
add_normalize_tail:
    lda z:ea
    cmp #1
    beq add_pack
add_normalize_bit:
    asl z:ma
    rol z:ma+2
    dec z:ea
    lda z:ma+2
    bit #$0400
    bne add_pack
    bra add_normalize_tail
add_pack:
    jmp .loword(ieee32_pack)

return_a:
    lda z:al
    ldx z:ah
    rts
return_b:
    lda z:bl
    ldx z:bh
    rts

shift_b:
    cpx #32
    bcc shift_b_word
    lda z:mb
    ora z:mb+2
    beq shift_b_zero
    lda #1
shift_b_zero:
    sta z:mb
    stz z:mb+2
    rts
shift_b_word:
    ; A discarded word contributes only its sticky nonzero bit
    cpx #16
    bcc shift_b_byte
    lda z:mb
    beq shift_b_word_exact
    lda z:mb+2
    ora #1
    bra shift_b_word_store
shift_b_word_exact:
    lda z:mb+2
shift_b_word_store:
    sta z:mb
    stz z:mb+2
    txa
    and #15                      ; remaining shift count
    tax
shift_b_byte:
    cpx #8
    bcc shift_b_tail
    ; The middle word already spans the two surviving source bytes
    lda z:mb
    and #$00ff
    beq shift_b_byte_exact
    lda z:mb+1
    ora #1
    bra shift_b_byte_join
shift_b_byte_exact:
    lda z:mb+1
shift_b_byte_join:
    sta z:mb
    lda z:mb+2
    xba
    and #$00ff
    sta z:mb+2
    txa
    and #7                      ; remaining shift count
    tax
shift_b_tail:
    dex
    bmi shift_b_done
    bne shift_b_multiple
    lsr z:mb+2
    ror z:mb
    bcc shift_b_done
    lda z:mb
    ora #1
    sta z:mb
    rts
shift_b_multiple:
    inx
    lda z:mb
shift_b_loop:
    lsr z:mb+2
    ror a
    bcc shift_b_even
    ora #1
shift_b_even:
    dex
    bne shift_b_loop
    sta z:mb
shift_b_done:
    rts
