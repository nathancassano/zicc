; Near output in X, signed exponent in A, upper word at 3,S; near result in A
; Native A16/X16, D=0, DBR=$7E; preserve Y/D/DBR. Arithmetic scratch clobbered
.setcpu "65816"
.a16
.i16
.export _decimal__exponent
.import __udiv16
.importzp __arith_lhs, __arith_rhs
.segment "CODE"
_decimal__exponent:
    phy
    pha
    txy
    lda 7,s
    beq @lower
    lda #$0045
    bra @letter
@lower:
    lda #$0065
@letter:
    sep #$20
.a8
    sta a:$0000,y
    iny
    rep #$20
.a16
    pla
    bpl @positive
    eor #$FFFF
    inc a
    sta z:__arith_lhs
    lda #$002D
    bra @sign
@positive:
    sta z:__arith_lhs
    lda #$002B
@sign:
    sep #$20
.a8
    sta a:$0000,y
    iny
    rep #$20
.a16
    ldx #0
@digit:
    phx
    lda #10
    sta z:__arith_rhs
    jsr .loword(__udiv16)
    plx
    ; __udiv16 leaves the quotient in L and the remainder in L+8
    lda z:__arith_lhs+8
    clc
    adc #$0030
    sep #$20
.a8
    pha
    rep #$20
.a16
    inx
    lda z:__arith_lhs
    bne @digit
    cpx #2
    bcs @emit
    sep #$20
.a8
    lda #$30
    pha
    rep #$20
.a16
    inx
@emit:
    sep #$20
.a8
@byte:
    pla
    sta a:$0000,y
    iny
    dex
    bne @byte
    rep #$20
.a16
    tya
    ply
    rts
__size_decimal__exponent = * - _decimal__exponent
