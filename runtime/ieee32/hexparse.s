; Far p at 3/5,S, near endptr in A, sign word at 7,S. U32 A/X result
; Native A16/X16, D=0, DBR=$7E; preserve Y/D/DBR. Private 32-byte frame
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _decimal__hexparse
.import _errno
M=__dp_scratch
E=__dp_scratch+4
F=__dp_scratch+8
R=__dp_scratch+12
P=__dp_scratch+16
N=__dp_scratch+20
DOT=__dp_scratch+22
SEEN=__dp_scratch+24
STICKY=__dp_scratch+26
K=__dp_scratch+28
ES=__dp_scratch+30
.macro h_get
    sep #$20
    lda [P]
    rep #$20
    and #$00FF
.endmacro
.macro h_next
    inc z:P
    bne :+
    sep #$20
    inc z:P+2
    rep #$20
:
.endmacro
.macro h_store_end
    ldx a:29,y
    beq :+
    lda z:P
    sta a:0,x
    lda z:P+2
    sta a:2,x
:
.endmacro
.segment "CODE"
_decimal__hexparse:
    sta z:K
    phy
    tsc
    sec
    sbc #32
    tcs
    tay
    lda z:K
    sta a:29,y
    lda a:37,y
    sta z:P
    sta a:1,y
    lda a:39,y
    and #$00FF
    sta z:P+2
    sta a:3,y
    stz z:M
    stz z:M+2
    stz z:E
    stz z:E+2
    stz z:F
    stz z:F+2
    stz z:R
    stz z:R+2
    stz z:N
    stz z:DOT
    stz z:SEEN
    stz z:STICKY
    lda #1
    sta z:ES
    h_next
    h_next
@scan:
    h_get
    sta z:K
    cmp #$002E
    bne @classify
    lda z:DOT
    bne @classify
    inc z:DOT
    h_next
    bra @scan
@classify:
    lda z:K
    sec
    sbc #$0030
    cmp #10
    bcc @digit
    lda z:K
    ora #$0020
    sec
    sbc #$0061
    cmp #6
    jcs @scan_end
    clc
    adc #10
@digit:
    sta z:K
    lda #1
    sta z:SEEN
    lda z:DOT
    beq :+
    inc z:F
    bne :+
    inc z:F+2
:
    lda z:M
    ora z:M+2
    ora z:N
    ora z:K
    beq @advance
    lda z:N
    cmp #8
    bcs @rest
    .repeat 4
    asl z:M
    rol z:M+2
    .endrepeat
    lda z:M
    ora z:K
    sta z:M
    inc z:N
    bra @advance
@rest:
    inc z:R
    bne :+
    inc z:R+2
:
    lda z:STICKY
    ora z:K
    sta z:STICKY
@advance:
    h_next
    jmp @scan
@scan_end:
    lda z:SEEN
    bne @exponent
    lda a:1,y
    sta z:P
    lda a:3,y
    sta z:P+2
    h_next
    h_store_end
    jmp @zero
@exponent:
    h_get
    ora #$0020
    cmp #$0070
    jne @finish_exponent
    lda z:P
    sta a:5,y
    lda z:P+2
    sta a:7,y
    h_next
    h_get
    cmp #$002B
    beq @exponent_sign
    cmp #$002D
    bne @exponent_first
    lda #$FFFF
    sta z:ES
@exponent_sign:
    h_next
@exponent_first:
    h_get
    sec
    sbc #$0030
    cmp #10
    bcc @exponent_digit
    lda a:5,y
    sta z:P
    lda a:7,y
    sta z:P+2
    bra @finish_exponent
@exponent_digit:
    sta z:K
    lda z:E+2
    bne @exponent_advance
    lda z:E
    cmp #10000
    bcs @exponent_advance
    asl z:E
    rol z:E+2
    lda z:E
    sta a:17,y
    lda z:E+2
    sta a:19,y
    .repeat 2
    asl z:E
    rol z:E+2
    .endrepeat
    clc
    lda z:E
    adc a:17,y
    sta z:E
    lda z:E+2
    adc a:19,y
    sta z:E+2
    clc
    lda z:E
    adc z:K
    sta z:E
    bcc @exponent_advance
    inc z:E+2
@exponent_advance:
    h_next
    h_get
    sec
    sbc #$0030
    cmp #10
    bcc @exponent_digit
    lda z:ES
    bpl @finish_exponent
    sec
    lda #0
    sbc z:E
    sta z:E
    lda #0
    sbc z:E+2
    sta z:E+2
@finish_exponent:
    h_store_end
    lda z:M
    ora z:M+2
    jeq @zero
    sec
    lda z:R
    sbc z:F
    sta a:17,y
    lda z:R+2
    sbc z:F+2
    sta a:19,y
    lda a:17,y
    sta z:R
    lda a:19,y
    sta z:R+2
    .repeat 2
    asl z:R
    rol z:R+2
    .endrepeat
    clc
    lda z:E
    adc z:R
    sta z:E
    lda z:E+2
    adc z:R+2
    sta z:E+2
    ldx #0
    lda z:M+2
    beq @low_bits
    ldx #16
    bra @bit_count
@low_bits:
    lda z:M
@bit_count:
    inx
    lsr a
    bne @bit_count
    txa
    sta a:13,y                ; nbits
    clc
    adc z:E
    sta a:17,y
    lda z:E+2
    adc #0
    sta a:19,y
    bmi @range_ok
    jne @overflow
    lda a:17,y
    cmp #130
    jcs @overflow
@range_ok:
    sec
    lda a:17,y
    sbc #24
    sta a:9,y                 ; step
    lda a:19,y
    sbc #0
    sta a:11,y
    bpl @step_ready
    cmp #$FFFF
    bne @clamp
    lda a:9,y
    cmp #$FF6B
    bcs @step_ready
@clamp:
    lda #$FF6B
    sta a:9,y
    lda #$FFFF
    sta a:11,y
@step_ready:
    sec
    lda a:9,y
    sbc z:E
    sta a:15,y                ; shift, after checking full signed range
    lda a:11,y
    sbc z:E+2
    bmi @shift_ready
    jne @underflow
    lda a:15,y
    cmp #33
    jcs @underflow
@shift_ready:
    lda a:15,y
    jeq @normalize
    jmi @left_shift
    lda #1
    sta a:21,y                ; half
    lda #0
    sta a:23,y
    ldx a:15,y
    dex
    beq @half_ready
@half_shift:
    lda a:21,y
    asl a
    sta a:21,y
    lda a:23,y
    rol a
    sta a:23,y
    dex
    bne @half_shift
@half_ready:
    lda z:M
    sta a:17,y                ; tail
    lda z:M+2
    sta a:19,y
    lda a:15,y
    cmp #32
    bne @mask
    stz z:M
    stz z:M+2
    bra @round
@mask:
    lda a:21,y
    asl a
    sta a:25,y
    lda a:23,y
    rol a
    sta a:27,y
    sec
    lda a:25,y
    sbc #1
    sta a:25,y
    lda a:27,y
    sbc #0
    sta a:27,y
    lda z:M
    and a:25,y
    sta a:17,y
    lda z:M+2
    and a:27,y
    sta a:19,y
    ldx a:15,y
@right_shift:
    lsr z:M+2
    ror z:M
    dex
    bne @right_shift
@round:
    lda a:19,y
    cmp a:23,y
    bcc @normalize
    bne @round_up
    lda a:17,y
    cmp a:21,y
    bcc @normalize
    bne @round_up
    lda z:STICKY
    bne @round_up
    lda z:M
    and #1
    beq @normalize
@round_up:
    inc z:M
    bne @normalize
    inc z:M+2
    bra @normalize
@left_shift:
    eor #$FFFF
    inc a
    tax
@left_bit:
    asl z:M
    rol z:M+2
    dex
    bne @left_bit
@normalize:
    lda z:M+2
    cmp #$0100
    bne @packed
    lda z:M
    bne @packed
    lsr z:M+2
    ror z:M
    lda a:9,y
    inc a
    sta a:9,y
    bne @packed
    lda a:11,y
    inc a
    sta a:11,y
@packed:
    lda a:11,y
    bmi @finite
    bne @overflow
    lda a:9,y
    cmp #105
    bcs @overflow
@finite:
    lda z:M+2
    cmp #$0080
    bcc @signed_result
    and #$007F
    sta z:K
    lda a:9,y
    clc
    adc #150
    .repeat 7
    asl a
    .endrepeat
    ora z:K
    sta z:M+2
    bra @signed_result
@overflow:
    lda #34
    sta a:.loword(_errno)
    stz z:M
    lda #$7F80
    sta z:M+2
    bra @signed_result
@underflow:
    lda #34
    sta a:.loword(_errno)
@zero:
    stz z:M
    stz z:M+2
@signed_result:
    lda a:41,y
    beq @return
    lda z:M+2
    ora #$8000
    sta z:M+2
@return:
    tsc
    clc
    adc #32
    tcs
    lda z:M
    ldx z:M+2
    ply
    rts
__size_decimal__hexparse = * - _decimal__hexparse
