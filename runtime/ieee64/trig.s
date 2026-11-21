; Binary64 sine and cosine. Range reduction uses 224 fractional bits of
; 2/pi and a 53-bit significand; the table stores one compact bit stream
; The polynomial targets small-ULP accuracy rather than correct rounding
; Native A16/X16, D=0, DBR=$7e; Y/D/DBR preserved
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __dadd, __dmul
.export _sin, _cos, __dsin, __dcos
L=__arith_lhs
V=1
Z=9
P=17
U=25
T=33
M=41
C=49
F=81
E=111
COUNT=113
INDEX=115
SIGN=117
MODE=119
Q=121
FSIGN=123
FRAME=124
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
.macro argument
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
.endmacro
.segment "CODE"
_sin:
    argument
    jsr .loword(__dsin)
    rts
_cos:
    argument
    jsr .loword(__dcos)
    rts
__dsin:
    lda #0
    bra trig_enter
__dcos:
    lda #1
trig_enter:
    phy
    pha
    tsc
    sec
    sbc #FRAME
    tcs
    tay
    lda FRAME+1,y
    sta a:MODE,y
    lda z:L+6
    and #$8000
    sta a:SIGN,y
    lda z:L+6
    and #$7fff
    sta z:L+6
    cmp #$7ff0
    jcs trig_nan
    .repeat 4, I
    lda z:L+I*2
    sta a:V+I*2,y
    .endrepeat
    ; Values below 0.5 require no reduction
    lda a:V+6,y
    cmp #$3fe0
    jcc trig_direct
    and #$7ff0
    .repeat 4
    lsr a
    .endrepeat
    ; shift = 1408 - (unbiased exponent + 172) = 2259 - biased
    sta a:E,y
    lda #2259
    sec
    sbc a:E,y
    pha
    and #7
    sta a:COUNT,y
    pla
    lsr a
    lsr a
    lsr a
    tax
    .repeat 16, I
    lda f:two_over_pi+I*2,x
    sta a:C+I*2,y
    .endrepeat
    lda a:COUNT,y
    beq trig_table_ready
trig_table_shift:
    lda a:C+30,y
    lsr a
    sta a:C+30,y
    .repeat 15, I
    lda a:C+28-I*2,y
    ror a
    sta a:C+28-I*2,y
    .endrepeat
    lda a:COUNT,y
    dec a
    sta a:COUNT,y
    bne trig_table_shift
trig_table_ready:
    .repeat 3, I
    lda a:V+I*2,y
    sta a:M+I*2,y
    .endrepeat
    lda a:V+6,y
    and #$000f
    ora #$0010
    sta a:M+6,y
    lda #0
    .repeat 15, I
    sta a:F+I*2,y
    .endrepeat
    lda #53
    sta a:COUNT,y
trig_product:
    lda a:M+6,y
    lsr a
    sta a:M+6,y
    .repeat 3, I
    lda a:M+4-I*2,y
    ror a
    sta a:M+4-I*2,y
    .endrepeat
    jcc trig_noadd
    clc
    .repeat 15, I
    lda a:F+I*2,y
    adc a:C+I*2,y
    sta a:F+I*2,y
    .endrepeat
trig_noadd:
    lda a:C,y
    asl a
    sta a:C,y
    .repeat 14, I
    lda a:C+2+I*2,y
    rol a
    sta a:C+2+I*2,y
    .endrepeat
    lda a:COUNT,y
    dec a
    sta a:COUNT,y
    jne trig_product
    lda a:F+28,y
    and #3
    sta a:Q,y
    lda a:F+26,y
    jpl trig_positive
    lda a:Q,y
    inc a
    sta a:Q,y
    sec
    .repeat 14, I
    lda #0
    sbc a:F+I*2,y
    sta a:F+I*2,y
    .endrepeat
    lda #$8000
    bra trig_fraction_sign
trig_positive:
    lda #0
trig_fraction_sign:
    sta a:FSIGN,y
    lda #1022
    sta a:E,y
trig_normalize:
    lda a:F+26,y
    bmi trig_round
    lda a:F,y
    asl a
    sta a:F,y
    .repeat 13, I
    lda a:F+2+I*2,y
    rol a
    sta a:F+2+I*2,y
    .endrepeat
    lda a:E,y
    dec a
    sta a:E,y
    bra trig_normalize
trig_round:
    lda a:F+20,y
    and #$07ff
    cmp #$0400
    bcc trig_pack
    bne trig_increment
    lda #0
    .repeat 10, I
    ora a:F+I*2,y
    .endrepeat
    bne trig_increment
    lda a:F+20,y
    bit #$0800
    beq trig_pack
trig_increment:
    lda a:F+20,y
    clc
    adc #$0800
    sta a:F+20,y
    .repeat 3, I
    lda a:F+22+I*2,y
    adc #0
    sta a:F+22+I*2,y
    .endrepeat
    bcc trig_pack
    lda #$8000
    sta a:F+26,y
    lda a:E,y
    inc a
    sta a:E,y
trig_pack:
    .repeat 3, I
    lda a:F+20+I*2,y
    .repeat 11
    lsr a
    .endrepeat
    sta a:T,y
    lda a:F+22+I*2,y
    .repeat 5
    asl a
    .endrepeat
    ora a:T,y
    sta a:V+I*2,y
    .endrepeat
    lda a:F+26,y
    .repeat 11
    lsr a
    .endrepeat
    and #$000f
    sta a:T,y
    lda a:E,y
    .repeat 4
    asl a
    .endrepeat
    ora a:T,y
    ora a:FSIGN,y
    sta a:V+6,y
    ; pi/2 split into a nearest binary64 and its residual
    constant U,$2d18,$5444,$21fb,$3ff9
    binary __dmul,P,V,U
    constant U,$c234,$1a62,$a626,$3c91
    binary __dmul,T,V,U
    binary __dadd,V,P,T
    bra trig_quadrant
trig_direct:
    lda #0
    sta a:Q,y
trig_quadrant:
    lda a:Q,y
    clc
    adc a:MODE,y
    sta a:Q,y
    binary __dmul,Z,V,V
    lda a:Q,y
    and #1
    jne trig_cosine
    ; sin(r) = r * (1 + r^2 * (...)), through degree 17
    constant P,$ad4a,$7030,$52c7,$3ce9
    lda #0
    sta a:INDEX,y
    ldx #0
    bra trig_series
trig_cosine:
    constant P,$7d97,$63b9,$8278,$bca6
    lda #56
    sta a:INDEX,y
trig_series:
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
    cmp #56
    beq trig_series_done
    cmp #120
    jne trig_series
trig_series_done:
    binary __dmul,P,P,Z
    constant U,$0000,$0000,$0000,$3ff0
    binary __dadd,P,P,U
    lda a:Q,y
    and #1
    bne trig_result
    binary __dmul,P,P,V
trig_result:
    .repeat 3, I
    lda a:P+I*2,y
    sta z:L+I*2
    .endrepeat
    lda a:Q,y
    and #2
    beq :+
    lda #$8000
:
    sta a:T,y
    lda a:MODE,y
    bne :+
    lda a:T,y
    eor a:SIGN,y
    sta a:T,y
:
    lda a:P+6,y
    eor a:T,y
    sta z:L+6
    bra trig_done
trig_nan:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$7ff8
    sta z:L+6
trig_done:
    tya
    clc
    adc #FRAME+2
    tcs
    ply
    rts
.segment "RODATA"
coefficients:
    ; sin coefficients, 1/15! through -1/3!
    .word $b81f,$e733,$e7f3,$bd6a
    .word $6d09,$13a8,$1246,$3de6
    .word $44e4,$67f5,$e645,$be5a
    .word $c734,$a556,$1de3,$3ec7
    .word $a01a,$1a01,$01a0,$bf2a
    .word $1111,$1111,$1111,$3f81
    .word $5555,$5555,$5555,$bfc5
    ; cos coefficients, 1/16! through -1/2!
    .word $b81f,$e733,$e7f3,$3d2a
    .word $7c9d,$a8c0,$3974,$bda9
    .word $d898,$eff8,$eed8,$3e21
    .word $9f5c,$b778,$7e4f,$be92
    .word $a01a,$1a01,$01a0,$3efa
    .word $6c17,$16c1,$c16c,$bf56
    .word $5555,$5555,$5555,$3fa5
    .word $0000,$0000,$0000,$bfe0
two_over_pi:
.include "trig-two-over-pi.inc"
