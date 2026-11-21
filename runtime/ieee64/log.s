; Binary64 natural logarithm. _log takes an eight-byte stack argument and
; returns in __arith_lhs+0..7; __dlog uses that slot for input and output
; Native A16/X16, D=0, DBR=$7E. Y/D/DBR preserved; A/X/flags and arithmetic
; scratch clobbered. A reduced atanh series uses binary64 arithmetic; this
; implementation targets a small-ULP approximation, not correct rounding
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __dadd, __dsub, __dmul, __ddiv, __sfloat64_32
.export _log, __dlog
L=__arith_lhs
V=1
Z=9
P=17
U=25
N=33
E=41
INDEX=43
FRAME=44
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
_log:
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
    jsr .loword(__dlog)
    rts
__dlog:
    phy
    tsc
    sec
    sbc #FRAME
    tcs
    tay
    lda z:L+6
    and #$7fff
    ora z:L+4
    ora z:L+2
    ora z:L
    jeq @minus_infinity
    lda z:L+6
    jmi @nan
    and #$7ff0
    cmp #$7ff0
    bne @finite
    lda z:L+6
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    jeq @done               ; positive infinity
    jmp .loword(@nan)
@finite:
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    beq @subnormal
    sec
    sbc #1023
    sta a:E,y
    bra @normalized
@subnormal:
    lda #$fc02              ; -1022
    sta a:E,y
@normalize:
    lda z:L+6
    and #$0010
    bne @normalized
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    lda a:E,y
    dec a
    sta a:E,y
    bra @normalize
@normalized:
    .repeat 3, I
    lda z:L+I*2
    sta a:V+I*2,y
    .endrepeat
    lda z:L+6
    and #$000f
    ora #$3ff0
    cmp #$3ff8             ; reduce m to [0.75,1.5)
    bcc :+
    sec
    sbc #$0010
    pha
    lda a:E,y
    inc a
    sta a:E,y
    pla
:
    sta a:V+6,y
    constant U,$0000,$0000,$0000,$3ff0
    binary __dsub,P,V,U
    binary __dadd,U,V,U
    binary __ddiv,V,P,U   ; z = (m-1)/(m+1)
    binary __dmul,Z,V,V
    constant P,$2f68,$bda1,$f684,$3fa2 ; 1/27
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
    cmp #96
    jne @series
    binary __dmul,P,P,Z
    constant U,$0000,$0000,$0000,$3ff0
    binary __dadd,P,P,U
    binary __dmul,P,P,V
    constant U,$0000,$0000,$0000,$4000
    binary __dmul,P,P,U
    lda a:E,y
    jeq @result_p
    sta z:L
    bpl :+
    lda #$ffff
    bra :++
:
    lda #0
:
    sta z:L+2
    jsr .loword(__sfloat64_32)
    .repeat 4, I
    lda z:L+I*2
    sta a:N+I*2,y
    .endrepeat
    ; ln(2) = hi + lo. Combining the low part with log(m) first avoids
    ; losing its contribution when the exponent is large
    constant U,$3c76,$3579,$39ef,$3dea
    binary __dmul,V,N,U
    binary __dadd,P,P,V
    constant U,$0000,$fee0,$2e42,$3fe6
    binary __dmul,N,N,U
    binary __dadd,P,N,P
@result_p:
    .repeat 4, I
    lda a:P+I*2,y
    sta z:L+I*2
    .endrepeat
    jmp .loword(@done)
@minus_infinity:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$fff0
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
; 1/25, 1/23, ..., 1/3, each rounded to binary64
coefficients:
    .word $147b,$47ae,$7ae1,$3fa4
    .word $2164,$590b,$42c8,$3fa6
    .word $8618,$1861,$6186,$3fa8
    .word $af28,$bca1,$f286,$3faa
    .word $1e1e,$1e1e,$1e1e,$3fae
    .word $1111,$1111,$1111,$3fb1
    .word $3b14,$13b1,$b13b,$3fb3
    .word $1746,$745d,$45d1,$3fb7
    .word $c71c,$1c71,$71c7,$3fbc
    .word $2492,$9249,$4924,$3fc2
    .word $999a,$9999,$9999,$3fc9
    .word $5555,$5555,$5555,$3fd5
