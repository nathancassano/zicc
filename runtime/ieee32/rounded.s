; Same entry as C rounded: signed keep in X, near digits in A, near length/exp
; pointers at 3/5,S. Void return. Native A16/X16, D=0, DBR=$7E
; Preserve Y/D/DBR and caller stack; A/X/flags and the shared workspace are call-clobbered
; Private state uses scratch offsets 0-15. The shared decimal digits are numeric, LSD first
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _decimal__rounded
.import _decimal__dec_digits, _decimal__dec_n, _decimal__dec_scale
.segment "CODE"
_decimal__rounded:
    sta z:__dp_scratch+2                  ; output
    stx z:__dp_scratch                  ; keep
    phy
    lda 5,s
    sta z:__dp_scratch+4                  ; length pointer
    lda 7,s
    sta z:__dp_scratch+6                  ; exponent pointer
    lda f:_decimal__dec_n
    sta z:__dp_scratch+8                  ; C caches n before writing through any pointer
    sec
    sbc f:_decimal__dec_scale
    dec a
    ldx z:__dp_scratch+6
    sta a:$0000,x
    lda z:__dp_scratch
    jmi @negative
    lda z:__dp_scratch+8
    bpl :+
    stz z:__dp_scratch+8                  ; Nonnegative i<n is false for negative n
:
    stz z:__dp_scratch+10                  ; round
    lda z:__dp_scratch
    cmp z:__dp_scratch+8
    bcs @decided
    lda z:__dp_scratch+8
    sec
    sbc z:__dp_scratch
    dec a
    tay
    sty z:__dp_scratch+12                  ; index of first discarded digit
    sep #$20
.a8
    phx
    tyx
    lda f:_decimal__dec_digits,x
    plx
    cmp #0
    cmp #5
    bcc @not_rounding
    bne @rounding
    ldy #0
@sticky:
    cpy z:__dp_scratch+12
    beq @tie
    phx
    tyx
    lda f:_decimal__dec_digits,x
    plx
    cmp #0
    bne @rounding              ; Remaining non-volatile reads cannot change it
    iny
    bra @sticky
@tie:
    rep #$20
.a16
    lda z:__dp_scratch
    beq @decided              ; An exact half rounds zero to even zero
    lda z:__dp_scratch+8
    sec
    sbc z:__dp_scratch
    tay
    sep #$20
.a8
    phx
    tyx
    lda f:_decimal__dec_digits,x
    plx
    cmp #0
    and #1
    beq @not_rounding
@rounding:
    lda #1
    sta z:__dp_scratch+10
@not_rounding:
    rep #$20
.a16
@decided:
    lda z:__dp_scratch
    bne @copy
    lda z:__dp_scratch+10
    clc
    adc #$0030
    ldx z:__dp_scratch+2
    sep #$20
.a8
    sta a:$0000,x
    rep #$20
.a16
    lda #1
    ldx z:__dp_scratch+4
    sta a:$0000,x
    lda z:__dp_scratch+10
    jne @increment_exp
    jmp @done
@copy:
    ldx z:__dp_scratch+4
    sta a:$0000,x             ; Preserve C's write order, including aliases
    ldx z:__dp_scratch+2
    lda z:__dp_scratch
    sec
    sbc z:__dp_scratch+8
    bcc @all_input
    sta z:__dp_scratch+12                  ; trailing zero count
    stz z:__dp_scratch+14                  ; lowest input index to copy
    lda z:__dp_scratch+8
    beq @pad
    bra @input_start
@all_input:
    stz z:__dp_scratch+12
    lda z:__dp_scratch+8
    sec
    sbc z:__dp_scratch
    sta z:__dp_scratch+14
@input_start:
    lda z:__dp_scratch+8
    dec a
    tay
    sep #$20
.a8
@input:
    phx
    tyx
    lda f:_decimal__dec_digits,x
    plx
    cmp #0
    clc
    adc #$30
    sta a:$0000,x
    inx
    cpy z:__dp_scratch+14
    beq @input_done
    dey
    bra @input
@input_done:
    rep #$20
.a16
@pad:
    ldy z:__dp_scratch+12
    beq @carry
    sep #$20
.a8
    lda #$30
@zero:
    sta a:$0000,x
    inx
    dey
    bne @zero
    rep #$20
.a16
@carry:
    lda z:__dp_scratch+10
    beq @done
    ldy z:__dp_scratch
    dey
    sep #$20
.a8
@nine:
    dex
    lda a:$0000,x
    cmp #$39
    bne @increment_digit
    lda #$30
    sta a:$0000,x
    cpy #0
    beq @all_nines
    dey
    bra @nine
@increment_digit:
    inc a
    sta a:$0000,x
    rep #$20
.a16
    bra @done
@all_nines:
.a8
    lda #$31
    sta a:$0000,x
    rep #$20
.a16
@increment_exp:
    ldx z:__dp_scratch+6
    lda a:$0000,x             ; Read after output/length writes, as C ++*exp does
    inc a
    sta a:$0000,x
@done:
    ply
    rts
@negative:
    ldx z:__dp_scratch+2
    sep #$20
.a8
    lda #$30
    sta a:$0000,x
    rep #$20
.a16
    lda #1
    ldx z:__dp_scratch+4
    sta a:$0000,x
    bra @done
__size_decimal__rounded = * - _decimal__rounded
