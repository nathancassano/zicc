; Compare two far byte arrays. Y and the caller's direct page are preserved
.setcpu "65816"
.a16
.i16
.importzp __dp_scratch
.export _memcmp
.include "common.inc"
.segment "CODE"
_memcmp:
    phy
    pei (__dp_scratch)
    pei (__dp_scratch+2)
    pei (__dp_scratch+4)
    pei (__dp_scratch+6)
    argument __dp_scratch,13,address_only
    argument __dp_scratch+4,17,address_only
    lda 21+LIBC_RETURN_EXTRA,s
    tax
    beq @equal
    ldy #0
    sep #$20
    .a8
@loop:
    lda [__dp_scratch],y
    cmp [__dp_scratch+4],y
    bne @different
    iny
    dex
    bne @loop
    rep #$20
    .a16
@equal:
    lda #0
    bra @done
@different:
    rep #$20
    lda #1
    bcs @done
    lda #$ffff
@done:
    ply
    sty z:__dp_scratch+6
    ply
    sty z:__dp_scratch+4
    ply
    sty z:__dp_scratch+2
    ply
    sty z:__dp_scratch
    ply
.if LIBC_RETURN_EXTRA
    rtl
.else
    rts
.endif
