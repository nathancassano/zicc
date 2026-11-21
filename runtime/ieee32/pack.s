; IEEE binary32 round-to-nearest/ties-to-even packer and special returns
.setcpu "65816"
.importzp __arith_lhs
.a16
.i16
ea = __arith_lhs+8
sg = __arith_lhs+12
ma = __arith_lhs+14
tmp = __arith_lhs+22

.segment "CODE"
.export ieee32_pack, ieee32_infinity, ieee32_zero

; ma has 24 significant bits and 3 rounding bits; ea is biased exponent
ieee32_pack:
    lda z:ea
    dec a
    bpl pack_normal
    ; Negate ea-1 for the subnormal shift count
    eor #$ffff
    inc a
    tax
    jsr .loword(shift_a)
    lda #1
    sta z:ea
pack_normal:
    ; Round iff the guard bit and at least one sticky or retained odd bit are set
    lda z:ma
    bit #4
    beq pack_truncate
    bit #$000b
    beq pack_truncate
    clc
    adc #8
    sta z:ma
    bcc pack_truncate
    inc z:ma+2
pack_truncate:
    lda z:ma+2
    lsr
    ror z:ma
    lsr
    ror z:ma
    lsr
    ror z:ma
    bit #$0100
    beq pack_no_carry
    lsr
    ror z:ma
    inc z:ea
pack_no_carry:
    ldx z:ea
    cpx #255
    bcs ieee32_infinity
    bit #$0080
    bne pack_exp
    ldx #0
pack_exp:
    and #$007f
    ora z:sg
    sta z:tmp
    txa                         ; 0..254: high byte is zero
    xba
    lsr
    ora z:tmp
    tax
    lda z:ma
    rts

ieee32_infinity:
    lda z:sg
    ora #$7f80
    tax
    lda #0
    rts

ieee32_zero:
    ldx z:sg
    lda #0
    rts

shift_a:
    cpx #0
    beq shift_a_done
    cpx #32
    bcc shift_a_word
    lda z:ma
    ora z:ma+2
    beq shift_a_zero
    lda #1
shift_a_zero:
    sta z:ma
    stz z:ma+2
    rts
shift_a_word:
    ; A discarded word contributes only its sticky nonzero bit
    cpx #16
    bcc shift_a_byte
    lda z:ma
    beq shift_a_word_exact
    lda z:ma+2
    ora #1
    bra shift_a_word_store
shift_a_word_exact:
    lda z:ma+2
shift_a_word_store:
    sta z:ma
    stz z:ma+2
    txa
    and #15                      ; remaining shift count
    tax
shift_a_byte:
    cpx #8
    bcc shift_a_tail
    ; The middle word already spans the two surviving source bytes
    lda z:ma
    and #$00ff
    beq shift_a_byte_exact
    lda z:ma+1
    ora #1
    bra shift_a_byte_join
shift_a_byte_exact:
    lda z:ma+1
shift_a_byte_join:
    sta z:ma
    lda z:ma+2
    xba
    and #$00ff
    sta z:ma+2
    txa
    and #7                      ; remaining shift count
    tax
shift_a_tail:
    dex
    bmi shift_a_done
    bne shift_a_multiple
    lsr z:ma+2
    ror z:ma
    bcc shift_a_done
    lda z:ma
    ora #1
    sta z:ma
    rts
shift_a_multiple:
    inx
    lda z:ma
shift_a_loop:
    lsr z:ma+2
    ror a
    bcc shift_a_even
    ora #1
shift_a_even:
    dex
    bne shift_a_loop
    sta z:ma
shift_a_done:
    rts
