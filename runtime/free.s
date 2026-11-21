; Release a near allocation and coalesce its physical neighbors
.setcpu "65816"
.a16
.i16
.export _free
.import __NEAR_LAST__
HEAP_BEGIN = .loword((__NEAR_LAST__ + 1) & $FFFFFE)
.segment "CODE"
_free:
    cpx #0
    beq @return
    dex
    dex
    lda a:$0000,x
    and #$FFFE
    sta a:$0000,x
    phy
    phx                         ; Released header at 1,S
    ldx #HEAP_BEGIN
    ldy #0                      ; Previous free block, if any
@find:
    txa
    cmp 1,s
    beq @found
    lda a:$0000,x
    bit #1
    bne @busy
    txy
    bra @advance
@busy:
    ldy #0
@advance:
    txa
    clc
    adc a:$0000,x
    and #$FFFE
    tax
    bra @find
@found:
    cpy #0
    beq @next
    lda a:$0000,x
    clc
    adc a:$0000,y
    sta a:$0000,y
    tyx
@next:
    txa
    clc
    adc a:$0000,x
    bcs @done                   ; No next block beyond $7E:FFFF
    tay
    lda a:$0000,y
    bit #1
    bne @done
    clc
    adc a:$0000,x
    sta a:$0000,x
@done:
    plx
    ply
@return:
    rts
