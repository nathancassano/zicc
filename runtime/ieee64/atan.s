; Binary64 atan. The public entry accepts an eight-byte stack argument;
; __datan consumes and returns __arith_lhs. Y/D/DBR are preserved
; Range reduction and a Taylor polynomial target a small-ULP approximation
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __dadd, __dsub, __dmul, __ddiv
.export _atan, __datan
L=__arith_lhs
V=1
Z=9
P=17
U=25
T=33
SIGN=41
MODE=43
INDEX=45
FRAME=46
.macro constant dest, w0, w1, w2, w3
    lda #w0
    sta a:dest,y
    lda #w1
    sta a:dest+2,y
    lda #w2
    sta a:dest+4,y
    lda #w3
    sta a:dest+6,y
.endmacro
.macro binary op, dest, left, right
    .repeat 4, I
    lda a:left+I*2,y
    sta z:L+I*2
    lda a:right+I*2,y
    sta z:L+8+I*2
    .endrepeat
    jsr .loword(op)
    .repeat 4, I
    lda z:L+I*2
    sta a:dest+I*2,y
    .endrepeat
.endmacro
.segment "CODE"
_atan:
    phy
    lda 5,s
    sta z:L
    lda 7,s
    sta z:L+2
    lda 9,s
    sta z:L+4
    lda 11,s
    sta z:L+6
    ply
    jsr .loword(__datan)
    rts
__datan:
    phy
    tsc
    sec
    sbc #FRAME
    tcs
    tay
    lda z:L+6
    and #$8000
    sta a:SIGN,y
    lda #0
    sta a:MODE,y
    lda z:L+6
    and #$7fff
    sta z:L+6
    cmp #$7ff0
    bcc @finite
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    jne @nan
    constant P,$2d18,$5444,$21fb,$3ff9
    jmp .loword(@result)
@finite:
    .repeat 4, I
    lda z:L+I*2
    sta a:V+I*2,y
    .endrepeat
    lda a:V+6,y
    cmp #$3ff0
    bcc @reduced_one
    bne @reciprocal
    lda a:V+4,y
    ora a:V+2,y
    ora a:V,y
    beq @reduced_one
@reciprocal:
    constant U,$0000,$0000,$0000,$3ff0
    binary __ddiv,V,U,V
    lda #1
    sta a:MODE,y
@reduced_one:
    lda a:V+6,y
    cmp #$3fdc
    jcc @polynomial
    bne @transform
    lda a:V+4,y
    ora a:V+2,y
    ora a:V,y
    jeq @polynomial
@transform:
    constant U,$0000,$0000,$0000,$3ff0
    binary __dsub,T,V,U
    binary __dadd,U,V,U
    binary __ddiv,V,T,U
    lda a:MODE,y
    ora #2
    sta a:MODE,y
@polynomial:
    binary __dmul,Z,V,V
    constant P,$0539,$a72f,$e5e0,$3f94
    lda #0
    sta a:INDEX,y
@series:
    binary __dmul,P,P,Z
    ldx a:INDEX,y
    .repeat 4, I
    lda f:coefficients+I*2,x
    sta a:U+I*2,y
    .endrepeat
    binary __dadd,P,P,U
    lda a:INDEX,y
    clc
    adc #8
    sta a:INDEX,y
    cmp #184
    jne @series
    binary __dmul,P,P,Z
    constant U,$0000,$0000,$0000,$3ff0
    binary __dadd,P,P,U
    binary __dmul,P,P,V
    lda a:MODE,y
    bit #2
    jeq @no_transform
    ; pi/4 = nearest binary64 plus its residual
    constant U,$c234,$1a62,$a626,$3c81
    binary __dadd,P,P,U
    constant U,$2d18,$5444,$21fb,$3fe9
    binary __dadd,P,U,P
@no_transform:
    lda a:MODE,y
    bit #1
    jeq @result
    constant U,$2d18,$5444,$21fb,$3ff9
    binary __dsub,P,U,P
    constant U,$c234,$1a62,$a626,$3c91
    binary __dadd,P,P,U
@result:
    .repeat 3, I
    lda a:P+I*2,y
    sta z:L+I*2
    .endrepeat
    lda a:P+6,y
    ora a:SIGN,y
    sta z:L+6
    bra @done
@nan:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$7ff8
    sta z:L+6
@done:
    tya
    clc
    adc #FRAME
    tcs
    ply
    rts
.segment "RODATA"
coefficients:
    .word $1057,$2b93,$c988,$bf95
    .word $6c17,$16c1,$c16c,$3f96
    .word $05f4,$417d,$d05f,$bf97
    .word $18fa,$8f9c,$f9c1,$3f98
    .word $a41a,$1a41,$41a4,$bf9a
    .word $bad0,$14c1,$acf9,$3f9b
    .word $d41d,$1d41,$41d4,$bf9d
    .word $1f08,$f07c,$07c1,$3f9f
    .word $1084,$0842,$8421,$bfa0
    .word $7b96,$611a,$a7b9,$3fa1
    .word $2f68,$bda1,$f684,$bfa2
    .word $147b,$47ae,$7ae1,$3fa4
    .word $2164,$590b,$42c8,$bfa6
    .word $8618,$1861,$6186,$3fa8
    .word $af28,$bca1,$f286,$bfaa
    .word $1e1e,$1e1e,$1e1e,$3fae
    .word $1111,$1111,$1111,$bfb1
    .word $3b14,$13b1,$b13b,$3fb3
    .word $1746,$745d,$45d1,$bfb7
    .word $c71c,$1c71,$71c7,$3fbc
    .word $2492,$9249,$4924,$bfc2
    .word $999a,$9999,$9999,$3fc9
    .word $5555,$5555,$5555,$bfd5
