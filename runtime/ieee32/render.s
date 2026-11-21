; Same entry as C render: near output p in X; far digits at 3,S, then
; signed words n/e/spec/precision/alt at 7/9/11/13/15,S. Return near p in A
; Native A16/X16, D=0, DBR=$7E; preserve Y/D/DBR, stack and argument homes
; A/X/flags and the shared workspace are call-clobbered. Private cursors use scratch offsets 0-17
; Scientific output retains the C exponent helper's X=p, A=e, stack upper ABI
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _decimal__render
.import _decimal__exponent
.segment "CODE"
_decimal__render:
    phy
    lda 5,s
    sta z:__dp_scratch                  ; Full far digit pointer, including bank carry
    lda 7,s
    sta z:__dp_scratch+2
    lda 9,s
    sta z:__dp_scratch+4                  ; n
    lda 11,s
    sta z:__dp_scratch+6                  ; e
    lda 15,s
    sta z:__dp_scratch+8                  ; precision
    lda 17,s
    sta z:__dp_scratch+10                  ; alt (any nonzero word)
    lda 13,s
    sta z:__dp_scratch+14                  ; spec
    stz z:__dp_scratch+12                  ; upper
    sec
    sbc #$0041
    cmp #26
    bcs @folded
    inc z:__dp_scratch+12
    lda z:__dp_scratch+14
    ora #$0020
    sta z:__dp_scratch+14
@folded:
    lda z:__dp_scratch+14
    cmp #$0067
    bne @choose
    lda z:__dp_scratch+10
    bne @trimmed
@trim:
    lda z:__dp_scratch+4
    bmi @trimmed
    cmp #2
    bcc @trimmed
    tay
    dey
    sep #$20
.a8
    lda [__dp_scratch],y
    cmp #$30
    rep #$20
.a16
    bne @trimmed
    dec z:__dp_scratch+4
    bra @trim
@trimmed:
    lda z:__dp_scratch+6
    bpl @compare_precision
    cmp #$FFFC
    bcc @general_scientific
@compare_precision:
    lda z:__dp_scratch+6
    sec
    sbc z:__dp_scratch+8
    bvc :+
    eor #$8000
:
    bmi @general_fixed
@general_scientific:
    lda z:__dp_scratch+10
    beq :+
    lda z:__dp_scratch+8
    bra :++
:
    lda z:__dp_scratch+4
:
    dec a
    sta z:__dp_scratch+8
    jmp @scientific
@general_fixed:
    lda z:__dp_scratch+10
    beq :+
    lda z:__dp_scratch+8
    bra :++
:
    lda z:__dp_scratch+4
:
    sec
    sbc z:__dp_scratch+6
    dec a
    bpl :+
    lda #0
:
    sta z:__dp_scratch+8
    bra @fixed
@choose:
    cmp #$0065
    jeq @scientific
@fixed:
    lda z:__dp_scratch+4
    bpl :+
    stz z:__dp_scratch+4                 ; Unsigned index<n also rejects negative indexes
:
    lda z:__dp_scratch+6
    bmi @leading_zero
    ldy #0
    sep #$20
.a8
@integer:
    cpy z:__dp_scratch+4
    bcs @integer_zero
    lda [__dp_scratch],y
    bra @integer_store
@integer_zero:
    lda #$30
@integer_store:
    sta a:$0000,x
    inx
    cpy z:__dp_scratch+6
    beq @integer_done
    iny
    bra @integer
@leading_zero:
    sep #$20
.a8
    lda #$30
    sta a:$0000,x
    inx
@integer_done:
    rep #$20
.a16
    lda z:__dp_scratch+8
    ora z:__dp_scratch+10
    beq @done
    sep #$20
.a8
    lda #$2E
    sta a:$0000,x
    inx
    rep #$20
.a16
    lda z:__dp_scratch+8
    beq @done
    bmi @done
    clc
    adc z:__dp_scratch+6
    inc a
    sta z:__dp_scratch+16                 ; Exclusive fractional index limit, modulo 16 bits
    lda z:__dp_scratch+6
    inc a
    tay
    sep #$20
.a8
@fraction:
    cpy z:__dp_scratch+4
    bcs @fraction_zero
    lda [__dp_scratch],y
    bra @fraction_store
@fraction_zero:
    lda #$30
@fraction_store:
    sta a:$0000,x
    inx
    iny
    cpy z:__dp_scratch+16
    bne @fraction
    rep #$20
.a16
@done:
    txa
    ply
    rts
@scientific:
    lda z:__dp_scratch+4
    bpl :+
    stz z:__dp_scratch+4
:
    sep #$20
.a8
    lda [__dp_scratch]
    sta a:$0000,x
    inx
    rep #$20
.a16
    lda z:__dp_scratch+8
    ora z:__dp_scratch+10
    beq @exponent
    sep #$20
.a8
    lda #$2E
    sta a:$0000,x
    inx
    rep #$20
.a16
    lda z:__dp_scratch+8
    beq @exponent
    bmi @exponent
    inc a
    sta z:__dp_scratch+16
    ldy #1
    sep #$20
.a8
@mantissa:
    cpy z:__dp_scratch+4
    bcs @mantissa_zero
    lda [__dp_scratch],y
    bra @mantissa_store
@mantissa_zero:
    lda #$30
@mantissa_store:
    sta a:$0000,x
    inx
    iny
    cpy z:__dp_scratch+16
    bne @mantissa
    rep #$20
.a16
@exponent:
    lda z:__dp_scratch+12
    pha
    lda z:__dp_scratch+6
    jsr .loword(_decimal__exponent)
    tax
    pla
    txa
    ply
    rts
__size_decimal__render = * - _decimal__render
