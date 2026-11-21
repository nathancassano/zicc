.setcpu "65816"
.a16
.i16
.export _strlen
.include "common.inc"
.segment "CODE"
source = 7+LIBC_RETURN_EXTRA
_strlen:
    phy
    phd
    tsc
    tax                         ; restore S after any private wrap pointer
    tcd
    ldy #0
    sep #$20
    .a8
@loop:
    .repeat 4
        lda [source],y
        beq @done
        iny
    .endrepeat
    bne @loop
    ; Advance a private copy only after a full Y wrap
    rep #$20
    .a16
    txs
    lda z:source+2
    inc a
    pha
    pei (source)
    tsc
    sec
    sbc #source-1
    tcd
    sep #$20
    .a8
    bra @loop
@done:
    rep #$20
    .a16
    txs
    tya
    pld
    ply
    rts
