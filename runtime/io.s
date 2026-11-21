.setcpu "65816"
.a16
.i16
.export _fgets, ___stdin
.export stdin_expression
.segment "BSS"
___stdin: .res 2
.segment "RODATA"
stdin_expression:
    .incbin "build/input.bin"
    .byte 0
.segment "CODE"
_fgets:
    phy
    pha                         ; Capacity
    phx                         ; Original destination
    lda 9,s
    cmp #.loword(___stdin)
    bne @failure
    lda 3,s
    beq @failure
    bmi @failure
    ldy #0
@next:
    lda 3,s
    cmp #1
    beq @terminate
    dec a
    sta 3,s
    phx
    tyx
    lda f:stdin_expression,x
    plx
    and #$00FF
    beq @terminate
    sep #$20
    .a8
    sta a:$0000,x
    rep #$20
    .a16
    inx
    iny
    cmp #10
    bne @next
@terminate:
    sep #$20
    .a8
    stz a:$0000,x
    rep #$20
    .a16
    lda 1,s
    bra @done
@failure:
    lda #0
@done:
    plx
    plx
    ply
    rts
