; 64-bit modulo product. Native A/X 16-bit. L and R are 8-byte
; little-endian operands at scratch +0 and +8; result is returned in L
; The multiplier R and temporary +16..+23 are destroyed. A/X/flags are
; clobbered; Y, D and DBR are preserved
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __mul64, __mul64_soft, __smul64_word, __umul64_word
L = __arith_lhs
R = __arith_lhs+8
P = __arith_lhs+16
.segment "CODE"
.macro clear_product
    stz z:P
    stz z:P+2
    stz z:P+4
    stz z:P+6
.endmacro
.macro add_partial
    clc
    lda z:P
    adc z:L
    sta z:P
    lda z:P+2
    adc z:L+2
    sta z:P+2
    lda z:P+4
    adc z:L+4
    sta z:P+4
    lda z:P+6
    adc z:L+6
    sta z:P+6
.endmacro
.macro shift_multiplicand
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
.endmacro

__mul64:
    lda z:R+6
    ora z:R+4
    ora z:R+2
    bne @hardware
    lda z:R
    bra multiply64_word
@hardware:
    jmp .loword(multiply64_shift_words)
__mul64_soft:
    clear_product
    ldx #64
@loop:
    lda z:R
    bit #1
    beq @skip
    add_partial
@skip:
    lsr z:R+6
    ror z:R+4
    ror z:R+2
    ror z:R
    lda z:R
    ora z:R+2
    ora z:R+4
    ora z:R+6
    beq multiply64_result
    shift_multiplicand
    dex
    bne @loop
    bra multiply64_result

; Direct word entry receives the factor in A. Negation is modulo 2^64
__smul64_word:
    cmp #0
    bmi :+
    jmp .loword(__umul64_word)
:
    eor #$FFFF
    inc a
    jsr .loword(__umul64_word)
    sec
    lda #0
    sbc z:L
    sta z:L
    lda #0
    sbc z:L+2
    sta z:L+2
    lda #0
    sbc z:L+4
    sta z:L+4
    lda #0
    sbc z:L+6
    sta z:L+6
    rts
; Word multipliers fit in X throughout the software loop
multiply64_word:
    tax
    clear_product
@loop:
    txa
    lsr a
    tax
    bcc @skip
    add_partial
@skip:
    cpx #0
    beq multiply64_result
    shift_multiplicand
    bra @loop

multiply64_result:
    lda z:P
    sta z:L
    lda z:P+2
    sta z:L+2
    lda z:P+4
    sta z:L+4
    lda z:P+6
    sta z:L+6
    rts

; A one-bit factor needs only a shift, and zero needs no partial products
__umul64_word:
    tax
    beq @zero
    dec a
    sta z:R
    txa
    and z:R
    bne @generic
    txa
@shift:
    lsr a
    bcs @done
    shift_multiplicand
    bra @shift
@done:
    rts
@zero:
    stz z:L
    stz z:L+2
    stz z:L+4
    stz z:L+6
    rts
@generic:
    txa
    jmp .loword(multiply64_word)

multiply64_shift_words:
    ; An isolated 1 in an upper word only moves the surviving limbs
    cmp #1
    bne @columns
    lda z:R
    bne @columns
    lda z:R+6
    bne @shift48
    lda z:R+4
    bne @shift32
    lda z:L+4
    sta z:L+6
    lda z:L+2
    sta z:L+4
    lda z:L
    sta z:L+2
    stz z:L
    rts
@shift32:
    lda z:R+2
    bne @columns
    lda z:L+2
    sta z:L+6
    lda z:L
    sta z:L+4
    bra @clear_low
@shift48:
    lda z:R+4
    ora z:R+2
    bne @columns
    lda z:L
    sta z:L+6
    stz z:L+4
@clear_low:
    stz z:L+2
    stz z:L
    rts
@columns:

; Accumulate the low eight byte columns. Terms above column seven
; vanish modulo 2^64. Keep column, low sum and overflow on the stack
multiply64_columns:
    phy
    lda #0
    pha                     ; column at 5,s
    pha                     ; low sum at 3,s
    pha                     ; overflow at 1,s
@column:
    lda #0
    sta 1,s
    lda 5,s
    tay
    ldx #0
@cell:
    sep #$20
.a8
    lda z:L,x
    beq @zero
    sta f:$004202
    phx
    tyx
    lda z:R,x
    plx
    cmp #0
    beq @zero
    sta f:$004203
    rep #$20
.a16
    clc
    lda f:$004216
    adc 3,s
    sta 3,s
    bcc @next
    lda 1,s
    inc a
    sta 1,s
    bra @next
@zero:
.a8
    rep #$20
.a16
@next:
    inx
    dey
    bpl @cell
    lda 5,s
    tax
    lda 3,s
    sep #$20
.a8
    sta z:P,x
    rep #$20
.a16
    xba
    and #$00ff
    sta 3,s
    lda 1,s
    xba
    ora 3,s
    sta 3,s
    lda 5,s
    inc a
    sta 5,s
    cmp #8
    bcc @column
    pla
    pla
    pla
    ply
    jmp .loword(multiply64_result)
