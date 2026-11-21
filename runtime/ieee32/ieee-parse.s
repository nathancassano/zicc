; Far text at 3/5,S, near endptr in A. U32 A/X result
; Native A16/X16, D=0, DBR=$7E; preserve Y/D/DBR. Frame 56 bytes
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export ___ieee_parse
.import _decimal__hexparse, _decimal__match, ___ieee_decimal
.import ___ieee_decimal_compare, _decade_floor, _errno
ORIG=1
ENDPTR=5
SAVED=7
FIRST=11
END=15
EP=19
SIGN=23
DOT=25
SEEN=27
ES=29
FRAC=31
COUNT=35
EXP=39
LO=43
HI=47
MID=51
BE=55
P=__dp_scratch+16
K=__dp_scratch+28
.macro p_get
    sep #$20
    lda [P]
    rep #$20
    and #$00FF
.endmacro
.macro p_next
    inc z:P
    bne :+
    sep #$20
    inc z:P+2
    rep #$20
:
.endmacro
.macro p_add amount
    .repeat amount
    p_next
    .endrepeat
.endmacro
.macro save_p offset
    lda z:P
    sta a:offset,y
    lda z:P+2
    sta a:offset+2,y
.endmacro
.macro load_p offset
    lda a:offset,y
    sta z:P
    lda a:offset+2,y
    sta z:P+2
.endmacro
.macro put_end
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
.macro times_ten
    ; U32 E0/E2 = E0/E2*10 + unsigned word K
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
    sta z:__dp_scratch
    bcc :+
    inc z:__dp_scratch+2
:
.endmacro
.macro match_word literal
    pea .bankbyte(literal)
    pea .loword(literal)
    lda a:SAVED+2,y
    pha
    lda a:SAVED,y
    pha
    jsr .loword(_decimal__match)
    sta z:K
    tsc
    clc
    adc #8
    tcs
    load_p SAVED
    lda z:K
.endmacro
.segment "CODE"
___ieee_parse:
    sta z:K
    phy
    tsc
    sec
    sbc #56
    tcs
    tay
    lda z:K
    sta a:ENDPTR,y
    lda a:61,y
    sta z:P
    sta a:ORIG,y
    lda a:63,y
    and #$00FF
    sta z:P+2
    sta a:ORIG+2,y
    lda #0
    sta a:FIRST,y
    sta a:FIRST+2,y
    sta a:SIGN,y
    sta a:DOT,y
    sta a:SEEN,y
    sta a:FRAC,y
    sta a:FRAC+2,y
    sta a:COUNT,y
    sta a:COUNT+2,y
    sta a:EXP,y
    sta a:EXP+2,y
    lda #1
    sta a:ES,y
@space:
    p_get
    cmp #$0020
    beq @space_next
    cmp #9
    bcc @sign
    cmp #14
    bcs @sign
@space_next:
    p_next
    bra @space
@sign:
    cmp #$002B
    beq @sign_next
    cmp #$002D
    bne @prefix
    lda #1
    sta a:SIGN,y
@sign_next:
    p_next
@prefix:
    save_p SAVED
    p_get
    cmp #$0030
    bne @special
    p_next
    p_get
    ora #$0020
    cmp #$0078
    bne @special
    lda a:SIGN,y
    pha
    lda a:SAVED+2,y
    pha
    lda a:SAVED,y
    pha
    lda a:ENDPTR,y
    jsr .loword(_decimal__hexparse)
    sta z:__dp_scratch
    stx z:__dp_scratch+2
    tsc
    clc
    adc #6
    tcs
    jmp @return
@special:
    load_p SAVED
    match_word parse_inf
    jeq @nan
    p_add 3
    save_p SAVED
    match_word parse_inity
    beq @inf_end
    p_add 5
@inf_end:
    put_end
    stz z:__dp_scratch
    lda #$7F80
    sta z:__dp_scratch+2
    jmp @signed_result
@nan:
    match_word parse_nan
    jeq @scan
    p_add 3
    save_p SAVED
    p_get
    cmp #$0028
    bne @nan_end
    p_next
@payload:
    p_get
    cmp #$005F
    beq @payload_next
    sec
    sbc #$0030
    cmp #10
    bcc @payload_next
    p_get
    ora #$0020
    sec
    sbc #$0061
    cmp #26
    bcs @payload_end
@payload_next:
    p_next
    bra @payload
@payload_end:
    p_get
    cmp #$0029
    bne @nan_rollback
    p_next
    bra @nan_end
@nan_rollback:
    load_p SAVED
@nan_end:
    put_end
    stz z:__dp_scratch
    lda #$7FC0
    sta z:__dp_scratch+2
    jmp @return                ; Return the same quiet NaN for either sign
@scan:
    p_get
    jeq @digits_end
    cmp #$002E
    bne @decimal_digit
    lda a:DOT,y
    jne @digits_end
    lda #1
    sta a:DOT,y
    p_next
    bra @scan
@decimal_digit:
    sec
    sbc #$0030
    cmp #10
    jcs @digits_end
    sta z:K
    lda #1
    sta a:SEEN,y
    lda a:DOT,y
    beq @fraction_done
    increment_long FRAC
@fraction_done:
    lda a:FIRST,y
    ora a:FIRST+2,y
    bne @count
    lda z:K
    beq @scan_next
    save_p FIRST
@count:
    increment_long COUNT
@scan_next:
    p_next
    jmp @scan
@digits_end:
    save_p END
    lda a:SEEN,y
    bne @decimal_exponent
    load_p ORIG
    put_end
    stz z:__dp_scratch
    stz z:__dp_scratch+2
    jmp @return
@decimal_exponent:
    p_get
    ora #$0020
    cmp #$0065
    jne @after_exponent
    save_p EP
    p_next
    p_get
    cmp #$002B
    beq @exponent_sign_next
    cmp #$002D
    bne @exponent_first
    lda #$FFFF
    sta a:ES,y
@exponent_sign_next:
    p_next
@exponent_first:
    p_get
    sec
    sbc #$0030
    cmp #10
    bcc @exponent_digit
    load_p EP
    jmp @after_exponent
@exponent_digit:
    sta z:K
    lda a:EXP+2,y
    cmp #1
    bcc @exponent_accumulate
    bne @exponent_next
    lda a:EXP,y
    cmp #34464                ; 100000 - 65536
    bcs @exponent_next
@exponent_accumulate:
    lda a:EXP,y
    sta z:__dp_scratch
    lda a:EXP+2,y
    sta z:__dp_scratch+2
    times_ten
    lda z:__dp_scratch
    sta a:EXP,y
    lda z:__dp_scratch+2
    sta a:EXP+2,y
@exponent_next:
    p_next
    p_get
    sec
    sbc #$0030
    cmp #10
    bcc @exponent_digit
    lda a:ES,y
    bpl @after_exponent
    sec
    lda #0
    sbc a:EXP,y
    sta a:EXP,y
    lda #0
    sbc a:EXP+2,y
    sta a:EXP+2,y
@after_exponent:
    put_end
    lda a:FIRST,y
    ora a:FIRST+2,y
    jeq @zero
    lda a:DOT,y
    ora a:FRAC,y
    ora a:FRAC+2,y
    ora a:EXP,y
    ora a:EXP+2,y
    jne @search_setup
    lda a:COUNT+2,y
    jne @search_setup
    lda a:COUNT,y
    cmp #9
    jcs @search_setup
    load_p FIRST
    stz z:__dp_scratch
    stz z:__dp_scratch+2
@integer:
    lda z:P+2
    cmp a:END+2,y
    bcc @integer_digit
    bne @integer_end
    lda z:P
    cmp a:END,y
    bcs @integer_end
@integer_digit:
    p_get
    sec
    sbc #$0030
    sta z:K
    times_ten
    p_next
    bra @integer
@integer_end:
    lda z:__dp_scratch
    ora z:__dp_scratch+2
    jeq @search_setup
    lda z:__dp_scratch+2
    cmp #$0100
    bcc @integer_normalize
    jne @search_setup
    lda z:__dp_scratch
    jne @search_setup
@integer_normalize:
    ldx #150
@integer_left:
    lda z:__dp_scratch+2
    cmp #$0080
    bcs @integer_top
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    dex
    bra @integer_left
@integer_top:
    cmp #$0100
    bne @integer_pack
    lsr z:__dp_scratch+2
    ror z:__dp_scratch
    inx
@integer_pack:
    lda z:__dp_scratch+2
    and #$007F
    sta z:__dp_scratch+4
    txa
    .repeat 7
    asl a
    .endrepeat
    ora z:__dp_scratch+4
    sta z:__dp_scratch+2
    jmp @signed_result
@search_setup:
    sec
    lda a:COUNT,y
    sbc a:FRAC,y
    sta z:__dp_scratch
    lda a:COUNT+2,y
    sbc a:FRAC+2,y
    sta z:__dp_scratch+2
    clc
    lda a:EXP,y
    adc z:__dp_scratch
    sta a:EXP,y
    lda a:EXP+2,y
    adc z:__dp_scratch+2
    sta a:EXP+2,y
    bmi @negative_decimal_range
    jne @overflow
    lda a:EXP,y
    cmp #41
    jcs @overflow
    bra @table
@negative_decimal_range:
    cmp #$FFFF
    jne @underflow
    lda a:EXP,y
    cmp #$FFD2                ; -46
    jcc @underflow
@table:
    lda a:EXP,y
    clc
    adc #46
    asl a
    asl a
    tax
    lda f:_decade_floor,x
    sta a:LO,y
    lda f:_decade_floor+2,x
    sta a:LO+2,y
    clc
    lda f:_decade_floor+4,x
    adc #1
    sta a:HI,y
    lda f:_decade_floor+6,x
    adc #0
    sta a:HI+2,y
@search:
    lda a:LO+2,y
    cmp a:HI+2,y
    bcc @midpoint
    jne @searched
    lda a:LO,y
    cmp a:HI,y
    jcs @searched
@midpoint:
    sec
    lda a:HI,y
    sbc a:LO,y
    sta z:__dp_scratch
    lda a:HI+2,y
    sbc a:LO+2,y
    sta z:__dp_scratch+2
    lsr z:__dp_scratch+2
    ror z:__dp_scratch
    clc
    lda z:__dp_scratch
    adc a:LO,y
    sta a:MID,y
    lda z:__dp_scratch+2
    adc a:LO+2,y
    sta a:MID+2,y
    asl a
    xba
    and #$00FF
    sta a:BE,y
    beq @midpoint_subnormal
    lda a:MID+2,y
    and #$007F
    ora #$0080
    bra @midpoint_mantissa
@midpoint_subnormal:
    lda #1
    sta a:BE,y
    lda a:MID+2,y
    and #$007F
@midpoint_mantissa:
    sta z:__dp_scratch+2
    lda a:MID,y
    sta z:__dp_scratch
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    inc z:__dp_scratch
    bne :+
    inc z:__dp_scratch+2
:
    lda z:__dp_scratch+2
    pha
    lda z:__dp_scratch
    pha
    lda a:BE,y
    sec
    sbc #151
    jsr .loword(___ieee_decimal)
    plx
    plx
    lda a:EXP+2,y
    pha
    lda a:EXP,y
    pha
    lda a:END+2,y
    pha
    lda a:END,y
    pha
    lda a:FIRST+2,y
    pha
    lda a:FIRST,y
    pha
    jsr .loword(___ieee_decimal_compare)
    tax
    tsc
    clc
    adc #12
    tcs
    txa
    bmi @lower_high
    bne @raise_low
    lda a:MID,y
    and #1
    beq @lower_high
@raise_low:
    clc
    lda a:MID,y
    adc #1
    sta a:LO,y
    lda a:MID+2,y
    adc #0
    sta a:LO+2,y
    jmp @search
@lower_high:
    lda a:MID,y
    sta a:HI,y
    lda a:MID+2,y
    sta a:HI+2,y
    jmp @search
@searched:
    lda a:LO+2,y
    cmp #$0080
    bcc @small_result
    cmp #$7F80
    bne @finite
    lda a:LO,y
    bne @finite
@small_result:
    lda #34
    sta a:.loword(_errno)
@finite:
    lda a:LO,y
    sta z:__dp_scratch
    lda a:LO+2,y
    sta z:__dp_scratch+2
    bra @signed_result
@overflow:
    lda #34
    sta a:.loword(_errno)
    stz z:__dp_scratch
    lda #$7F80
    sta z:__dp_scratch+2
    bra @signed_result
@underflow:
    lda #34
    sta a:.loword(_errno)
@zero:
    stz z:__dp_scratch
    stz z:__dp_scratch+2
@signed_result:
    lda a:SIGN,y
    beq @return
    lda z:__dp_scratch+2
    ora #$8000
    sta z:__dp_scratch+2
@return:
    tsc
    clc
    adc #56
    tcs
    lda z:__dp_scratch
    ldx z:__dp_scratch+2
    ply
    rts
__size___ieee_parse = * - ___ieee_parse
.segment "RODATA"
parse_inf: .asciiz "inf"
parse_inity: .asciiz "inity"
parse_nan: .asciiz "nan"
