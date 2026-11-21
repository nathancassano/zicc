; Padded far p/end at 3/7,S, signed long exponent at 11,S; signed word A result
; Native A16/X16, D=0, DBR=$7E; preserve Y/D/DBR. Scratch +0-+19
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export ___ieee_decimal_compare
.import _decimal__dec_digits, _decimal__dec_n, _decimal__dec_scale
.macro p_before yes,no
    lda z:__dp_scratch+2
    cmp z:__dp_scratch+6
    bcc yes
    bne no
    lda z:__dp_scratch
    cmp z:__dp_scratch+4
    bcc yes
    bra no
.endmacro
.macro advance_p
    inc z:__dp_scratch
    bne :+
    sep #$20
    inc z:__dp_scratch+2
    rep #$20
:
.endmacro
.segment "CODE"
___ieee_decimal_compare:
    phy
    lda 5,s
    sta z:__dp_scratch
    lda 7,s
    and #$00FF
    sta z:__dp_scratch+2
    lda 9,s
    sta z:__dp_scratch+4
    lda 11,s
    and #$00FF
    sta z:__dp_scratch+6
    lda 13,s
    sta z:__dp_scratch+16
    lda 15,s
    sta z:__dp_scratch+18
    lda f:_decimal__dec_n
    sta z:__dp_scratch+8
    sec
    sbc f:_decimal__dec_scale
    sta z:__dp_scratch+12
    lda #0
    bit z:__dp_scratch+12
    bpl :+
    dec a
:
    sta z:__dp_scratch+14
    lda z:__dp_scratch+18
    cmp z:__dp_scratch+14
    beq @low_exponent
    sec
    sbc z:__dp_scratch+14
    bvc :+
    eor #$8000
:
    jmi @less
    jmp @greater
@low_exponent:
    lda z:__dp_scratch+16
    cmp z:__dp_scratch+12
    jeq @digits
    jcc @less
    jmp @greater
@digits:
    lda z:__dp_scratch+8
    bpl :+
    stz z:__dp_scratch+8
:
    ldy #0
@next:
    p_before @skip_dots,@at_end
@at_end:
    cpy z:__dp_scratch+8
    jcs @equal
    bra @no_input
@skip_dots:
    sep #$20
.a8
    lda [__dp_scratch]
    cmp #$2E
    rep #$20
.a16
    bne @input
    advance_p
    p_before @skip_dots,@no_input
@input:
    and #$00FF
    sec
    sbc #$0030
    sta z:__dp_scratch+16
    advance_p
    bra @reference_digit
@no_input:
    stz z:__dp_scratch+16
@reference_digit:
    cpy z:__dp_scratch+8
    bcs @reference_zero
    tya
    eor #$FFFF
    clc
    adc z:__dp_scratch+8
    tax
    sep #$20
.a8
    lda f:_decimal__dec_digits,x
    rep #$20
.a16
    and #$00FF
    bra @compare
@reference_zero:
    lda #0
@compare:
    sta z:__dp_scratch+18
    lda z:__dp_scratch+16
    cmp z:__dp_scratch+18
    beq @same
    sec
    sbc z:__dp_scratch+18
    bvc :+
    eor #$8000
:
    bmi @less
    bra @greater
@same:
    cpy z:__dp_scratch+8
    bcs :+
    iny
:
    jmp @next
@less:
    lda #$FFFF
    ply
    rts
@greater:
    lda #1
    ply
    rts
@equal:
    lda #0
    ply
    rts
__size___ieee_decimal_compare = * - ___ieee_decimal_compare
