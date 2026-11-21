; Independent ABI/scratch probe for the hand-written string routines
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _libc_preserve
.import _strcpy, _strcmp
.segment "BSS"
buffer: .res 8
.segment "RODATA"
text: .asciiz "probe"
.segment "CODE"
_libc_preserve:
    phy
    ldy #$1357
    lda #$2468
    sta z:__dp_scratch
    sta z:__dp_scratch+2
    sta z:__dp_scratch+4
    sta z:__dp_scratch+6
    pea .bankbyte(text)
    pea .loword(text)
    ldx #.loword(buffer)
    jsr .loword(_strcpy)
    plx
    plx
    cpy #$1357
    bne @bad
    lda z:__dp_scratch
    cmp #$2468
    bne @bad
    lda z:__dp_scratch+2
    cmp #$2468
    bne @bad
    pea .bankbyte(text)
    pea .loword(text)
    pea $007E
    pea .loword(buffer)
    jsr .loword(_strcmp)
    plx
    plx
    plx
    plx
    cmp #0
    bne @bad
    cpy #$1357
    bne @bad
    lda z:__dp_scratch
    cmp #$2468
    bne @bad
    lda z:__dp_scratch+2
    cmp #$2468
    bne @bad
    lda z:__dp_scratch+4
    cmp #$2468
    bne @bad
    lda z:__dp_scratch+6
    cmp #$2468
    bne @bad
    lda #0
    ply
    rts
@bad:
    lda #99
    ply
    rts
