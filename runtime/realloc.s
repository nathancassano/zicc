.setcpu "65816"
.a16
.i16
.export _realloc
.import _malloc, _free
.segment "CODE"

; Pointer in X, requested size in A. Preserve the old block on failure
_realloc:
    cpx #0
    bne realloc_existing
    tax
    jmp .loword(_malloc)
realloc_existing:
    cmp #0
    bne realloc_size
    jsr .loword(_free)
    lda #0
    rts
realloc_size:
    pha
    dex
    dex
    lda a:0,x
    inx
    inx
    and #$fffe
    dec a
    dec a
    cmp 1,s
    bcc realloc_grow
    pla
    txa
    rts
realloc_grow:
    phy
    phx
    pha
    lda 7,s
    tax
    jsr .loword(_malloc)
    cmp #0
    beq realloc_finish
    tay
    pha
    lda 5,s
    tax
    lda 3,s
    dec a
    mvn #$7e, #$7e
    lda 5,s
    tax
    jsr .loword(_free)
    pla
realloc_finish:
    plx
    plx
    ply
    plx
    rts
