; Binary64 strtod. Far text at 3/5,S; near endptr in A. Decimal subjects
; use exact midpoint refinement; hexadecimal subjects dispatch to hexparse
; Return binary64 in __arith_lhs+0..7
; Native A16/X16, D=0, DBR=$7E; preserve Y/D/DBR. Private frame: 56 bytes
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import _decimal__match, _errno
.import __ieee64_decimal_estimate, __ieee64_decimal_refine_signed, __ieee64_hexparse
.import __fp_overflow, __fp_tiny, __fp_exceptions, __fp_round_mode
.export __ieee64_parse_decimal, _strtod, _strtold
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
MANT=43
KEPT=51
P=__dp_scratch+16
K=__dp_scratch+28
.macro p_get
    sep #$20
    lda [P]
    rep #$20
    and #$00ff
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
.macro times_ten32
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
__ieee64_parse_decimal:
_strtold:
_strtod:
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
    and #$00ff
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
    sta a:MANT,y
    sta a:MANT+2,y
    sta a:MANT+4,y
    sta a:MANT+6,y
    sta a:KEPT,y
    lda #1
    sta a:ES,y
@space:
    p_get
    cmp #$20
    beq @space_next
    cmp #9
    bcc @sign
    cmp #14
    bcs @sign
@space_next:
    p_next
    bra @space
@sign:
    cmp #'+'
    beq @sign_next
    cmp #'-'
    bne @special
    lda #1
    sta a:SIGN,y
@sign_next:
    p_next
@special:
    save_p SAVED
    p_get
    cmp #'0'
    bne @not_hex
    p_next
    p_get
    ora #$20
    cmp #'x'
    bne @not_hex
    lda a:SIGN,y
    pha
    lda a:SAVED+2,y
    pha
    lda a:SAVED,y
    pha
    lda a:ENDPTR,y
    jsr .loword(__ieee64_hexparse)
    tsc
    clc
    adc #6
    tcs
    jmp .loword(@return)
@not_hex:
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
    stz z:__dp_scratch+2
    stz z:__dp_scratch+4
    lda #$7ff0
    sta z:__dp_scratch+6
    jmp .loword(@signed_result)
@nan:
    match_word parse_nan
    jeq @scan
    p_add 3
    save_p SAVED
    p_get
    cmp #'('
    bne @nan_end
    p_next
@payload:
    p_get
    cmp #'_'
    beq @payload_next
    sec
    sbc #'0'
    cmp #10
    bcc @payload_next
    p_get
    ora #$20
    sec
    sbc #'a'
    cmp #26
    bcs @payload_end
@payload_next:
    p_next
    bra @payload
@payload_end:
    p_get
    cmp #')'
    bne @nan_rollback
    p_next
    bra @nan_end
@nan_rollback:
    load_p SAVED
@nan_end:
    put_end
    stz z:__dp_scratch
    stz z:__dp_scratch+2
    stz z:__dp_scratch+4
    lda #$7ff8
    sta z:__dp_scratch+6
    jmp .loword(@signed_result)
@scan:
    p_get
    jeq @digits_end
    cmp #'.'
    bne @digit
    lda a:DOT,y
    jne @digits_end
    lda #1
    sta a:DOT,y
    p_next
    bra @scan
@digit:
    sec
    sbc #'0'
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
    jeq @scan_next
    save_p FIRST
@count:
    increment_long COUNT
    lda a:KEPT,y
    cmp #17
    jcs @scan_next
    inc a
    sta a:KEPT,y
    ; The first 17 significant digits fit in 64 bits. E0..EF are temporary;
    ; the input cursor at F0 and the current digit at FC remain intact
    .repeat 4, I
    lda a:MANT+I*2,y
    sta z:__dp_scratch+I*2
    .endrepeat
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    rol z:__dp_scratch+4
    rol z:__dp_scratch+6
    .repeat 4, I
    lda z:__dp_scratch+I*2
    sta z:__dp_scratch+8+I*2
    .endrepeat
    .repeat 2
    asl z:__dp_scratch
    rol z:__dp_scratch+2
    rol z:__dp_scratch+4
    rol z:__dp_scratch+6
    .endrepeat
    clc
    .repeat 4, I
    lda z:__dp_scratch+I*2
    adc z:__dp_scratch+8+I*2
    sta z:__dp_scratch+I*2
    .endrepeat
    clc
    lda z:__dp_scratch
    adc z:K
    sta z:__dp_scratch
    .repeat 3, I
    lda z:__dp_scratch+2+I*2
    adc #0
    sta z:__dp_scratch+2+I*2
    .endrepeat
    .repeat 4, I
    lda z:__dp_scratch+I*2
    sta a:MANT+I*2,y
    .endrepeat
@scan_next:
    p_next
    jmp .loword(@scan)
@digits_end:
    save_p END
    lda a:SEEN,y
    bne @decimal_exponent
    load_p ORIG
    put_end
    jmp .loword(@unsigned_zero)
@decimal_exponent:
    p_get
    ora #$20
    cmp #'e'
    jne @after_exponent
    save_p EP
    p_next
    p_get
    cmp #'+'
    beq @exponent_sign_next
    cmp #'-'
    bne @exponent_first
    lda #$ffff
    sta a:ES,y
@exponent_sign_next:
    p_next
@exponent_first:
    p_get
    sec
    sbc #'0'
    cmp #10
    bcc @exponent_digit
    load_p EP
    jmp .loword(@after_exponent)
@exponent_digit:
    sta z:K
    lda a:EXP+2,y
    cmp #1
    bcc @exponent_accumulate
    bne @exponent_next
    lda a:EXP,y
    cmp #34464
    bcs @exponent_next
@exponent_accumulate:
    lda a:EXP,y
    sta z:__dp_scratch
    lda a:EXP+2,y
    sta z:__dp_scratch+2
    times_ten32
    lda z:__dp_scratch
    sta a:EXP,y
    lda z:__dp_scratch+2
    sta a:EXP+2,y
@exponent_next:
    p_next
    p_get
    sec
    sbc #'0'
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
    ; EXP is now the decimal-point exponent of the significant digit stream
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
    bmi @negative_range
    jne @overflow
    lda a:EXP,y
    cmp #310
    jcs @overflow
    bra @estimate
@negative_range:
    cmp #$ffff
    jne @underflow
    lda a:EXP,y
    cmp #$febd               ; -323
    jcc @underflow
@estimate:
    lda f:__fp_exceptions
    pha
    lda f:__fp_round_mode
    pha
    lda #0
    sta f:__fp_round_mode
    .repeat 4, I
    lda a:MANT+I*2,y
    sta z:__dp_scratch+I*2
    .endrepeat
    lda a:EXP,y
    sec
    sbc a:KEPT,y
    jsr .loword(__ieee64_decimal_estimate)
    pla
    sta f:__fp_round_mode
    pla
    sta f:__fp_exceptions
    lda a:FIRST,y
    sta z:__dp_scratch+8
    lda a:FIRST+2,y
    sta z:__dp_scratch+10
    lda a:END,y
    sta z:__dp_scratch+12
    lda a:END+2,y
    sta z:__dp_scratch+14
    lda a:EXP,y
    sta z:__dp_scratch+16
    lda a:EXP+2,y
    sta z:__dp_scratch+18
    lda a:SIGN,y
    jsr .loword(__ieee64_decimal_refine_signed)
    lda z:__dp_scratch+6
    and #$7ff0
    beq @range_error
    cmp #$7ff0
    bne @signed_result
@range_error:
    lda #34
    sta a:.loword(_errno)
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
    bra @return
@unsigned_zero:
    stz z:__dp_scratch
    stz z:__dp_scratch+2
    stz z:__dp_scratch+4
    stz z:__dp_scratch+6
@return:
    tya
    clc
    adc #56
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
.segment "RODATA"
parse_inf: .asciiz "inf"
parse_inity: .asciiz "inity"
parse_nan: .asciiz "nan"
