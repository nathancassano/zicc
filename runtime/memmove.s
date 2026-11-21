; Near destination in X; far source at 3,S; unsigned count at 7,S
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _memmove
.import _memcpy
.segment "CODE"
_memmove:
    lda 7,s
    beq @empty
    lda 5,s
    and #$00FF
    cmp #$7E
    beq @near
    ; Banks $00-$3F/$80-$BF mirror the first 8 KiB of bank $7E
    and #$007F
    cmp #$0040
    bcs @forward
    lda 3,s
    cmp #$2000
    bcs @forward
@near:
    txa
    sec
    sbc 3,s
    beq @forward
    bcc @forward
    cmp 7,s
    bcs @forward
    lda 5,s
    and #$00FF
    cmp #$7E
    bne @backward_far
    phy
    phx
    phb
    txa
    clc
    adc 12,s
    dec a
    tay                         ; Last destination byte
    lda 8,s
    clc
    adc 12,s
    dec a
    tax                         ; Last source byte
    lda 12,s
    dec a
    mvp #$7E, #$7E
    plb
    pla
    ply
    rts
@forward:
    jmp .loword(_memcpy)
@empty:
    txa
    rts
@backward_far:
    ; Preserve actual long-address semantics even across a low-RAM mirror's
    ; $2000 boundary, where the source stops mapping contiguous WRAM
    phy
    phx
    pei (__dp_scratch)
    pei (__dp_scratch+2)
    lda 11,s
    sta z:__dp_scratch
    lda 13,s
    and #$00FF
    sta z:__dp_scratch+2
    txa
    clc
    adc 15,s
    dec a
    tax
    lda 15,s
    dec a
    tay
@byte:
    sep #$20
.a8
    lda [__dp_scratch],y
    sta a:$0000,x
    rep #$20
.a16
    dex
    dey
    cpy #$FFFF
    bne @byte
    pla
    sta z:__dp_scratch+2
    pla
    sta z:__dp_scratch
    pla
    ply
    rts
