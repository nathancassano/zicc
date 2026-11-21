; Independent stack/register/scratch probe, separate from C-generated callers
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _libc_new_preserve
.import _strlen,_strncpy,_strcat,_strncat,_strncmp,_memcmp,_strchr,_strrchr,_memchr
.import _strspn,_strcspn,_strpbrk,_strstr,_strtok,_strxfrm,_strcoll,_sprintf,_snprintf
.segment "BSS"
buffer: .res 64
saved_sp: .res 2
.segment "RODATA"
text: .asciiz "probe"
format: .asciiz "%d:%S"
.segment "CODE"
.macro require
    beq :+
    jmp failed
:
.endmacro
.macro seed
    tsc
    sta saved_sp
    ldy #$1357
    ldx #$001E
    lda #$2468
:
    sta z:__dp_scratch,x
    dex
    dex
    bpl :-
.endmacro
.macro verify
    cpy #$1357
    require
    tsc
    cmp saved_sp
    require
    tdc
    require
    php
    sep #$20
.a8
    pla
    and #$38
    rep #$20
.a16
    require
    sep #$20
.a8
    phb
    pla
    cmp #$7E
    rep #$20
.a16
    require
    ldx #$001E
:
    lda z:__dp_scratch,x
    cmp #$2468
    require
    dex
    dex
    bpl :-
.endmacro
.macro fartext
    pea .bankbyte(text)
    pea .loword(text)
.endmacro
_libc_new_preserve:
    phy
    seed
    fartext
    jsr .loword(_strlen)
    plx
    plx
    verify
    seed
    pea 3
    fartext
    ldx #.loword(buffer)
    jsr .loword(_strncpy)
    plx
    plx
    plx
    verify
    seed
    fartext
    ldx #.loword(buffer)
    jsr .loword(_strcat)
    plx
    plx
    verify
    seed
    pea 3
    fartext
    ldx #.loword(buffer)
    jsr .loword(_strncat)
    plx
    plx
    plx
    verify
    seed
    pea 3
    fartext
    fartext
    jsr .loword(_strncmp)
    plx
    plx
    plx
    plx
    plx
    verify
    seed
    pea 3
    fartext
    fartext
    jsr .loword(_memcmp)
    plx
    plx
    plx
    plx
    plx
    verify
    seed
    fartext
    lda #'r'
    jsr .loword(_strchr)
    plx
    plx
    verify
    seed
    fartext
    lda #'r'
    jsr .loword(_strrchr)
    plx
    plx
    verify
    seed
    pea 3
    fartext
    lda #'r'
    jsr .loword(_memchr)
    plx
    plx
    plx
    verify
    seed
    fartext
    fartext
    jsr .loword(_strspn)
    plx
    plx
    plx
    plx
    verify
    seed
    fartext
    fartext
    jsr .loword(_strcspn)
    plx
    plx
    plx
    plx
    verify
    seed
    fartext
    fartext
    jsr .loword(_strpbrk)
    plx
    plx
    plx
    plx
    verify
    seed
    fartext
    fartext
    jsr .loword(_strstr)
    plx
    plx
    plx
    plx
    verify
    seed
    fartext
    ldx #.loword(buffer)
    jsr .loword(_strtok)
    plx
    plx
    verify
    seed
    pea 3
    fartext
    ldx #.loword(buffer)
    jsr .loword(_strxfrm)
    plx
    plx
    plx
    verify
    seed
    fartext
    fartext
    jsr .loword(_strcoll)
    plx
    plx
    plx
    plx
    verify
    seed
    fartext
    pea 17
    pea .bankbyte(format)
    pea .loword(format)
    ldx #.loword(buffer)
    jsr .loword(_sprintf)
    plx
    plx
    plx
    plx
    plx
    verify
    seed
    fartext
    pea 17
    pea .bankbyte(format)
    pea .loword(format)
    ldx #.loword(buffer)
    lda #64
    jsr .loword(_snprintf)
    plx
    plx
    plx
    plx
    plx
    verify
    lda #0
    ply
    rts
failed:
    lda #99
    ply
    rts
