; Binary64 hexadecimal text conversion. Input: far pointer to 0x/0X at
; 3/5,S, sign word at 7,S, near endptr in A. Return bits in __arith_lhs+0..7
; Native A16/X16, D=0, DBR=$7E; Y/D/DBR preserved. The first 15 significant
; hexadecimal digits plus a sticky bit suffice for exact ties-to-even rounding
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.import __fp_round_increment, __fp_raise, __fp_overflow, __fp_tiny
.a16
.i16
.importzp __arith_lhs
.import _errno
.export __ieee64_hexparse
ORIG=1
ENDPTR=5
SIGN=7
EXP=9
FRAC=13
REST=17
NDIG=21
DOT=23
SEEN=25
STICKY=27
ES=29
MANT=31
STEP=39
NBITS=41
TEMP=43
EP=47
FRAME=50
P=__dp_scratch+16
K=__dp_scratch+28
.macro h_get
    sep #$20
    lda [P]
    rep #$20
    and #$00ff
.endmacro
.macro h_next
    inc z:P
    bne :+
    sep #$20
    inc z:P+2
    rep #$20
:
.endmacro
.macro h_end
    ldx a:ENDPTR,y
    beq :+
    lda z:P
    sta a:0,x
    lda z:P+2
    sta a:2,x
:
.endmacro
.macro increment_long offset
    lda a:offset,y
    inc a
    sta a:offset,y
    bne :+
    lda a:offset+2,y
    inc a
    sta a:offset+2,y
:
.endmacro
.segment "CODE"
__ieee64_hexparse:
    sta z:K
    phy
    tsc
    sec
    sbc #FRAME
    tcs
    tay
    lda z:K
    sta a:ENDPTR,y
    lda a:55,y
    sta z:P
    sta a:ORIG,y
    lda a:57,y
    and #$00ff
    sta z:P+2
    sta a:ORIG+2,y
    lda a:59,y
    sta a:SIGN,y
    lda #0
    sta a:EXP,y
    sta a:EXP+2,y
    sta a:FRAC,y
    sta a:FRAC+2,y
    sta a:REST,y
    sta a:REST+2,y
    sta a:NDIG,y
    sta a:DOT,y
    sta a:SEEN,y
    sta a:STICKY,y
    .repeat 4, I
    sta a:MANT+I*2,y
    .endrepeat
    lda #1
    sta a:ES,y
    h_next
    h_next
@scan:
    h_get
    sta z:K
    cmp #'.'
    bne @classify
    lda a:DOT,y
    bne @classify
    lda #1
    sta a:DOT,y
    h_next
    bra @scan
@classify:
    lda z:K
    sec
    sbc #'0'
    cmp #10
    bcc @digit
    lda z:K
    ora #$20
    sec
    sbc #'a'
    cmp #6
    jcs @scan_end
    clc
    adc #10
@digit:
    sta z:K
    lda #1
    sta a:SEEN,y
    lda a:DOT,y
    beq @fraction_done
    increment_long FRAC
@fraction_done:
    lda a:NDIG,y
    ora z:K
    beq @advance
    lda a:NDIG,y
    cmp #15
    bcs @rest
    .repeat 4, I
    lda a:MANT+I*2,y
    sta z:__dp_scratch+I*2
    .endrepeat
    .repeat 4
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    rol z:__dp_scratch+4
    rol z:__dp_scratch+6
    .endrepeat
    lda z:__dp_scratch
    ora z:K
    sta z:__dp_scratch
    .repeat 4, I
    lda z:__dp_scratch+I*2
    sta a:MANT+I*2,y
    .endrepeat
    lda a:NDIG,y
    inc a
    sta a:NDIG,y
    bra @advance
@rest:
    increment_long REST
    lda a:STICKY,y
    ora z:K
    sta a:STICKY,y
@advance:
    h_next
    jmp .loword(@scan)
@scan_end:
    lda a:SEEN,y
    bne @exponent
    lda a:ORIG,y
    sta z:P
    lda a:ORIG+2,y
    sta z:P+2
    h_next                   ; invalid prefix consumes only its leading zero
    h_end
    jmp .loword(@zero)
@exponent:
    h_get
    ora #$20
    cmp #'p'
    jne @finish_exponent
    lda z:P
    sta a:EP,y
    lda z:P+2
    sta a:EP+2,y
    h_next
    h_get
    cmp #'+'
    beq @exponent_sign
    cmp #'-'
    bne @exponent_first
    lda #$ffff
    sta a:ES,y
@exponent_sign:
    h_next
@exponent_first:
    h_get
    sec
    sbc #'0'
    cmp #10
    bcc @exponent_digit
    lda a:EP,y
    sta z:P
    lda a:EP+2,y
    sta z:P+2
    jmp .loword(@finish_exponent)
@exponent_digit:
    sta z:K
    lda a:EXP+2,y
    cmp #1
    bcc @exponent_accumulate
    bne @exponent_advance
    lda a:EXP,y
    cmp #34464
    bcs @exponent_advance
@exponent_accumulate:
    lda a:EXP,y
    sta z:__dp_scratch
    lda a:EXP+2,y
    sta z:__dp_scratch+2
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    lda z:__dp_scratch
    sta z:__dp_scratch+4
    lda z:__dp_scratch+2
    sta z:__dp_scratch+6
    .repeat 2
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    .endrepeat
    clc
    lda z:__dp_scratch
    adc z:__dp_scratch+4
    sta z:__dp_scratch
    lda z:__dp_scratch+2
    adc z:__dp_scratch+6
    sta z:__dp_scratch+2
    clc
    lda z:__dp_scratch
    adc z:K
    sta a:EXP,y
    lda z:__dp_scratch+2
    adc #0
    sta a:EXP+2,y
@exponent_advance:
    h_next
    h_get
    sec
    sbc #'0'
    cmp #10
    bcc @exponent_digit
    lda a:ES,y
    bpl @finish_exponent
    sec
    lda #0
    sbc a:EXP,y
    sta a:EXP,y
    lda #0
    sbc a:EXP+2,y
    sta a:EXP+2,y
@finish_exponent:
    h_end
    lda a:MANT,y
    ora a:MANT+2,y
    ora a:MANT+4,y
    ora a:MANT+6,y
    jeq @zero
    ; EXP = parsed exponent + 4*(discarded nibbles - fractional nibbles)
    sec
    lda a:REST,y
    sbc a:FRAC,y
    sta z:__dp_scratch
    lda a:REST+2,y
    sbc a:FRAC+2,y
    sta z:__dp_scratch+2
    .repeat 2
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    .endrepeat
    clc
    lda a:EXP,y
    adc z:__dp_scratch
    sta a:EXP,y
    lda a:EXP+2,y
    adc z:__dp_scratch+2
    sta a:EXP+2,y
    .repeat 4, I
    lda a:MANT+I*2,y
    sta z:__dp_scratch+I*2
    .endrepeat
    ldx #0
@bit_count:
    inx
    lsr z:__dp_scratch+6
    ror z:__dp_scratch+4
    ror z:__dp_scratch+2
    ror z:__dp_scratch
    lda z:__dp_scratch
    ora z:__dp_scratch+2
    ora z:__dp_scratch+4
    ora z:__dp_scratch+6
    bne @bit_count
    txa
    sta a:NBITS,y
    clc
    adc a:EXP,y
    sta a:TEMP,y
    lda a:EXP+2,y
    adc #0
    sta a:TEMP+2,y
    bmi @negative_range
    jne @overflow
    lda a:TEMP,y
    cmp #1026
    jcs @overflow
    bra @step
@negative_range:
    cmp #$ffff
    jne @underflow
    lda a:TEMP,y
    cmp #$fbce               ; -1074
    jcc @underflow
@step:
    lda a:TEMP,y
    sec
    sbc #53
    cmp #$fbce
    bvs @step_ok
    bpl @step_ok
    lda #$fbce               ; minimum subnormal quantum, 2^-1074
@step_ok:
    sta a:STEP,y
    sec
    sbc a:EXP,y              ; shift after full-range checks above
    .repeat 4, I
    pha
    lda a:MANT+I*2,y
    sta z:__dp_scratch+I*2
    pla
    .endrepeat
    beq @pack
    bmi @left_shift
    cmp #57
    jcs @underflow
    tax
@right_shift:
    lsr z:__dp_scratch+6
    ror z:__dp_scratch+4
    ror z:__dp_scratch+2
    ror z:__dp_scratch
    dex
    beq @guard
    bcc @right_shift
    lda #1
    sta a:STICKY,y
    bra @right_shift
@guard:
    lda #0
    adc #0
    asl a
    asl a
    ldx a:STICKY,y
    beq :+
    ora #1
:
    pha
    lda z:__dp_scratch
    and #1
    asl a
    asl a
    asl a
    ora 1,s
    ldx #0
    pha
    lda a:SIGN,y
    beq :+
    ldx #$8000
:
    pla
    jsr .loword(__fp_round_increment)
    pla
    sta a:STICKY,y
    bcc @pack
    inc z:__dp_scratch
    bne @pack
    inc z:__dp_scratch+2
    bne @pack
    inc z:__dp_scratch+4
    bne @pack
    inc z:__dp_scratch+6
    bra @pack
@left_shift:
    eor #$ffff
    inc a
    tax
@left_bit:
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    rol z:__dp_scratch+4
    rol z:__dp_scratch+6
    dex
    bne @left_bit
@pack:
    lda z:__dp_scratch+6
    cmp #$0020
    bcc @packed
    lsr z:__dp_scratch+6
    ror z:__dp_scratch+4
    ror z:__dp_scratch+2
    ror z:__dp_scratch
    lda a:STEP,y
    inc a
    sta a:STEP,y
@packed:
    lda z:__dp_scratch+6
    cmp #$0010
    bcs @normal
    lda #34
    sta a:.loword(_errno)
    lda a:STICKY,y
    beq @signed_result
    lda #$0018
    jsr .loword(__fp_raise)
    bra @signed_result
@normal:
    lda a:STEP,y
    clc
    adc #1075
    cmp #2047
    jcs @overflow
    .repeat 4
    asl a
    .endrepeat
    sta z:K
    lda z:__dp_scratch+6
    and #$000f
    ora z:K
    sta z:__dp_scratch+6
    lda a:STICKY,y
    beq @signed_result
    lda #$0010
    jsr .loword(__fp_raise)
    bra @signed_result
@overflow:
    lda #34
    sta a:.loword(_errno)
    jsr .loword(@result_sign)
    jsr .loword(__fp_overflow)
    bra @return
@underflow:
    lda #34
    sta a:.loword(_errno)
    jsr .loword(@result_sign)
    jsr .loword(__fp_tiny)
    bra @return
@zero:
    stz z:__dp_scratch
    stz z:__dp_scratch+2
    stz z:__dp_scratch+4
    stz z:__dp_scratch+6
@signed_result:
    lda a:SIGN,y
    beq @return
    lda z:__dp_scratch+6
    ora #$8000
    sta z:__dp_scratch+6
@return:
    tya
    clc
    adc #FRAME
    tcs
    ply
    rts
@result_sign:
    ldx #0
    lda a:SIGN,y
    beq :+
    ldx #$8000
:
    rts
