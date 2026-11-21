; Shared macros for ASCII/C-locale string library
.macro enter
    phy
    pei (__dp_scratch)
    pei (__dp_scratch+2)
    pei (__dp_scratch+4)
    pei (__dp_scratch+6)
    pei (__dp_scratch+8)
    pei (__dp_scratch+10)
    pei (__dp_scratch+12)
    pei (__dp_scratch+14)
    stx z:__dp_scratch
    sta z:__dp_scratch+8
    ldy #0
.endmacro
.macro leave
    ply
    sty z:__dp_scratch+14
    ply
    sty z:__dp_scratch+12
    ply
    sty z:__dp_scratch+10
    ply
    sty z:__dp_scratch+8
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
.endmacro
; Mark caller-owned operands for the staged JSL/RTL ABI transformation
.macro argument pointer, offset, address_only
    lda offset+LIBC_RETURN_EXTRA,s
    sta z:pointer
    lda offset+2+LIBC_RETURN_EXTRA,s
    .ifblank address_only
        and #$00FF
    .endif
    sta z:pointer+2
.endmacro
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA=0
.endif
.macro next pointer
    inc z:pointer
    bne :+
    inc z:pointer+2
:
.endmacro
.macro byte pointer
    sep #$20
    .a8
    lda [pointer]
    rep #$20
    .a16
    and #$00FF
.endmacro
.macro put
    sep #$20
    .a8
    sta a:$0000,x
    rep #$20
    .a16
.endmacro
