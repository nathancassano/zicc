; Binary64 exponential. _exp takes an eight-byte stack argument and returns
; in __arith_lhs+0..7; __dexp uses that slot for input/output. Range reduction
; uses a split ln(2) and a binary64 polynomial. Subnormal scaling rounds to
; nearest, ties to even. The polynomial targets small-ULP accuracy rather than
; correct rounding. A/X/flags and arithmetic scratch are clobbered; Y/D/DBR
; are preserved. Native A16/X16, D=0, DBR=$7E
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __dadd, __dsub, __dmul, __fix64_32, __sfloat64_32
.export _exp, __dexp
L=__arith_lhs
V=1
P=9
U=17
N=25
T=33
E=41
INDEX=43
STICKY=45
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
_exp:
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
    jsr .loword(__dexp)
    rts
__dexp:
    phy
    tsc
    sec
    sbc #FRAME
    tcs
    tay
    lda z:L+6
    and #$7ff0
    cmp #$7ff0
    bne @finite
    lda z:L+6
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    jne @nan
    lda z:L+6
    jmi @zero
    jmp .loword(@infinity)
@finite:
    lda z:L+6
    and #$7fff
    cmp #$4090              ; |x| >= 1024 safely exceeds output range
    bcc @reduce
    lda z:L+6
    jmi @zero
    jmp .loword(@infinity)
@reduce:
    .repeat 4, I
    lda z:L+I*2
    sta a:V+I*2,y
    .endrepeat
    constant U,$82fe,$652b,$1547,$3ff7 ; 1/ln(2)
    binary __dmul,T,V,U
    lda a:T+6,y
    bpl @positive_round
    constant U,$0000,$0000,$0000,$bfe0
    bra @round_integer
@positive_round:
    constant U,$0000,$0000,$0000,$3fe0
@round_integer:
    binary __dadd,T,T,U
    .repeat 4, I
    lda a:T+I*2,y
    sta z:L+I*2
    .endrepeat
    jsr .loword(__fix64_32)
    lda z:L
    sta a:E,y
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
    ; r = (x - n*ln2_hi) - n*ln2_lo
    constant U,$0000,$fee0,$2e42,$3fe6
    binary __dmul,T,N,U
    binary __dsub,V,V,T
    constant U,$3c76,$3579,$39ef,$3dea
    binary __dmul,T,N,U
    binary __dsub,V,V,T
    constant P,$7c9d,$a8c0,$3974,$3da9 ; 1/14!
    lda #0
    sta a:INDEX,y
@series:
    binary __dmul,P,P,V
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
    cmp #104
    jne @series
    binary __dmul,P,P,V
    constant U,$0000,$0000,$0000,$3ff0
    binary __dadd,P,P,U
    .repeat 4, I
    lda a:P+I*2,y
    sta z:L+I*2
    .endrepeat
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    clc
    adc a:E,y
    bmi @subnormal
    beq @subnormal
    cmp #2047
    jcs @infinity
    .repeat 4
    asl a
    .endrepeat
    sta z:L+8
    lda z:L+6
    and #$000f
    ora z:L+8
    sta z:L+6
    jmp .loword(@done)
@subnormal:
    ; Shift the 53-bit significand by 1-biased_exponent, preserving a guard
    ; bit and sticky bits for gradual underflow and the normal boundary
    eor #$ffff
    inc a
    inc a
    cmp #54
    jcs @zero
    tax
    lda z:L+6
    and #$000f
    ora #$0010
    sta z:L+6
    lda #0
    sta a:STICKY,y
@shift:
    lsr z:L+6
    ror z:L+4
    ror z:L+2
    ror z:L
    dex
    beq @guard
    bcc @shift
    lda #1
    sta a:STICKY,y
    bra @shift
@guard:
    bcc @done
    lda a:STICKY,y
    bne @round_up
    lda z:L
    and #1
    beq @done
@round_up:
    inc z:L
    bne @done
    inc z:L+2
    bne @done
    inc z:L+4
    bne @done
    inc z:L+6
    bra @done
@nan:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$7ff8
    sta z:L+6
    bra @done
@infinity:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$7ff0
    sta z:L+6
    bra @done
@zero:
    stz z:L
    stz z:L+2
    stz z:L+4
    stz z:L+6
@done:
    tya
    clc
    adc #FRAME
    tcs
    ply
    rts
.segment "RODATA"
; 1/13!, 1/12!, ..., 1/1!, rounded to binary64
coefficients:
    .word $6d09,$13a8,$1246,$3de6
    .word $d898,$eff8,$eed8,$3e21
    .word $44e4,$67f5,$e645,$3e5a
    .word $9f5c,$b778,$7e4f,$3e92
    .word $c734,$a556,$1de3,$3ec7
    .word $a01a,$1a01,$01a0,$3efa
    .word $a01a,$1a01,$01a0,$3f2a
    .word $6c17,$16c1,$c16c,$3f56
    .word $1111,$1111,$1111,$3f81
    .word $5555,$5555,$5555,$3fa5
    .word $5555,$5555,$5555,$3fc5
    .word $0000,$0000,$0000,$3fe0
    .word $0000,$0000,$0000,$3ff0
