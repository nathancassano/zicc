; Independent ABI/scratch checks, plus nested calls during a real NMI
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _memory_preserve, __vector_nmi
.import _memcpy, _memset, _memmove
.segment "BSS"
saved_sp: .res 2
nmi_count: .res 2
nmi_in_block: .res 2
buffer: .res 32
nested: .res 32
.segment "RODATA"
text: .byte 1,2,3,4,5,6,7,8
.segment "CODE"
.macro require_equal
    beq :+
    jmp failed
:
.endmacro
.macro check
    .local scratch
    cmp #.loword(buffer)
    require_equal
    cpy #$1357
    require_equal
    tsc
    cmp a:.loword(saved_sp)
    require_equal
    tdc
    require_equal
    php
    sep #$20
.a8
    pla
    and #$38
    rep #$20
.a16
    require_equal
    sep #$20
.a8
    phb
    pla
    cmp #$7E
    rep #$20
.a16
    require_equal
    ldx #$001E
scratch:
    lda z:__dp_scratch,x
    cmp #$2468
    require_equal
    dex
    dex
    bpl scratch
.endmacro
_memory_preserve:
    phy
    tsc
    sta a:.loword(saved_sp)
    ldy #$1357
    ldx #$001E
    lda #$2468
@poison:
    sta z:__dp_scratch,x
    dex
    dex
    bpl @poison
    .repeat 3, count
        pea count
        lda #$12A5
        ldx #.loword(buffer)
        jsr .loword(_memset)
        plx
        check
        pea count
        pea .bankbyte(text)
        pea .loword(text)
        ldx #.loword(buffer)
        jsr .loword(_memcpy)
        plx
        plx
        plx
        check
    .endrepeat
    .repeat 2, extra
        pea 2+extra
        pea $007E
        pea $FFFE
        ldx #.loword(buffer)
        jsr .loword(_memcpy)
        plx
        plx
        plx
        check
    .endrepeat
    .repeat 2, direction
        pea 8
        pea $007E
        pea .loword(buffer+direction)
        ldx #.loword(buffer+1-direction)
        jsr .loword(_memmove)
        plx
        plx
        plx
        .if direction = 0
            dec a
        .endif
        check
    .endrepeat
    lda #$0201
    sta a:$0100
    lda #$0403
    sta a:$0102
    lda #$0605
    sta a:$0104
    lda #$0807
    sta a:$0106
    pea 8
    pea $0080
    pea $0100
    ldx #$0101
    jsr .loword(_memmove)
    plx
    plx
    plx
    cmp #$0101
    require_equal
    lda a:$0101
    cmp #$0201
    require_equal
    lda a:$0107
    cmp #$0807
    require_equal
    lda #.loword(buffer)
    check
    ; The raw far source is outside the linked WRAM spans
    ldx #0
    lda #$5AA5
@fill_source:
    sta f:$7F0000,x
    inx
    inx
    cpx #50000
    bne @fill_source
    sep #$20
.a8
    lda f:$004210
    lda #$80
    sta f:$004200
    rep #$20
.a16
    pea 50000
    pea $007F
    pea $0000
    ldx #$3000
    jsr .loword(_memcpy)
    plx
    plx
    plx
    cmp #$3000
    require_equal
    sep #$20
.a8
    lda #0
    sta f:$004200
    rep #$20
.a16
    lda #.loword(buffer)
    check
    lda a:.loword(nmi_in_block)
    bne :+
    jmp failed
:
    lda a:.loword(nested)
    cmp #$0101
    require_equal
    lda a:.loword(nested+1)
    cmp #$0201
    require_equal
    lda a:.loword(nested+7)
    cmp #$0807
    require_equal
    ldx #$3000
@copied:
    lda a:$0000,x
    cmp #$5AA5
    require_equal
    inx
    inx
    cpx #$F350
    bne @copied
    lda #0
    ply
    rts
failed:
    lda #99
    ply
    rts
__vector_nmi:
    jml nmi_body
nmi_body:
    rep #$30
    pha
    phx
    phy
    phb
    lda 11,s                    ; Hardware-saved PBR: bank $00 is the MVN thunk
    and #$00FF
    bne :+
    inc a:.loword(nmi_in_block)
:
    sep #$20
.a8
    lda #$7E
    pha
    plb
    lda f:$004210
    rep #$20
.a16
    inc a:.loword(nmi_count)
    pea 32
    lda #$AA
    ldx #.loword(nested)
    jsr .loword(_memset)
    plx
    pea 8
    pea .bankbyte(text)
    pea .loword(text)
    ldx #.loword(nested)
    jsr .loword(_memcpy)
    plx
    plx
    plx
    pea 8
    pea $007E
    pea .loword(nested)
    ldx #.loword(nested+1)
    jsr .loword(_memmove)
    plx
    plx
    plx
    plb
    ply
    plx
    pla
    rti
