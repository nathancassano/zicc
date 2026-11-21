; Search one byte at a time with the far source bank in DBR and its
; offset in X. Use the active bank for the result, including after a wrap
.setcpu "65816"
.a16
.i16
.export _strchr
.include "common.inc"
.segment "CODE"
_strchr:
    phb
    and #$00ff
    pha
    lda 6+LIBC_RETURN_EXTRA,s
    tax
    sep #$20
    .a8
    lda 8+LIBC_RETURN_EXTRA,s
    pha
    plb
@loop:
    lda a:$0000,x
    beq @end
    cmp 1,s
    beq @found
    inx
    bne @loop
    phb
    pla
    inc a
    pha
    plb
    bra @loop
@end:
    cmp 1,s
    bne @null
@found:
    pla                         ; replace the search byte, keeping its zero high byte
    phb                         ; PLX returns this bank in X with a zero high byte
    rep #$20
    .a16
    txa
    plx
    plb
.if LIBC_RETURN_EXTRA
    rtl
.else
    rts
.endif
@null:
    rep #$20
    .a16
    pla
    lda #0
    tax
    plb
.if LIBC_RETURN_EXTRA
    rtl
.else
    rts
.endif
