; Near writable destination, arbitrary 24-bit source (including ROM)
; Preserve the reserved DP words locally, including across nested interrupts
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _strcpy
.segment "CODE"
_strcpy:
    phy
    phx                         ; Original destination
    pei (__dp_scratch)
    pei (__dp_scratch+2)
    lda 11,s                    ; Source low word above saved state and return
    sta z:__dp_scratch
    lda 13,s
    and #$00FF
    sta z:__dp_scratch+2
    ldy #0
    sep #$20
.a8
@copy:
    lda [__dp_scratch],y                 ; Long indexing carries across source banks
    sta a:$0000,x
    beq @done
    inx
    iny
    bra @copy
@done:
    rep #$20
.a16
    pla
    sta z:__dp_scratch+2
    pla
    sta z:__dp_scratch
    pla                         ; Return original destination
    ply
    rts
