.setcpu "65816"
.a16
.i16
.export _calloc
.import _malloc
.importzp __arith_lhs
.segment "CODE"

; Count in X, element size in A. Reject a product wider than size_t
_calloc:
    cpx #0
    beq calloc_null
    cmp #0
    beq calloc_null
    stx z:__arith_lhs
    sta z:__arith_lhs+2
    lda #0
calloc_multiply:
    lsr z:__arith_lhs
    bcc calloc_shift
    clc
    adc z:__arith_lhs+2
    bcs calloc_null
calloc_shift:
    ldx z:__arith_lhs
    beq calloc_allocate
    asl z:__arith_lhs+2
    bcc calloc_multiply
calloc_null:
    lda #0
    rts
calloc_allocate:
    pha
    tax
    jsr .loword(_malloc)
    plx
    cmp #0
    beq calloc_done
    phy
    pha
    tay
    sep #$20
.a8
    lda #0
calloc_clear:
    sta a:0,y
    iny
    dex
    bne calloc_clear
    rep #$20
.a16
    pla
    ply
calloc_done:
    rts
