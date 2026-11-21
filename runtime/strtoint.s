; Integer string conversions use the shared arithmetic scratch area
.setcpu "65816"
.a16
.i16
.export _strtol, _strtoul, _atoi, _atol
.importzp __arith_lhs
.import _errno
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

cursor = __arith_lhs
original = __arith_lhs+4
result = __arith_lhs+8
radix = __arith_lhs+12
endptr = __arith_lhs+14
flags = __arith_lhs+16
digit = __arith_lhs+18
factor = __arith_lhs+20
multiple = __arith_lhs+22
negative = 1
unsigned_mode = 2
consumed = 4
overflow = 8
automatic_base = 16

.macro advance_cursor
    inc z:cursor
    bne :+
    inc z:cursor+2
:
.endmacro

.segment "CODE"
_strtol:
    stz z:flags
    bra explicit_base
_strtoul:
    ldx #unsigned_mode
    stx z:flags
explicit_base:
    sta z:endptr
    lda 7+LIBC_RETURN_EXTRA,s
    sta z:radix
    bra read_input
_atoi:
_atol:
    stz z:flags
    stz z:endptr
    lda #10
    sta z:radix
read_input:
    lda 3+LIBC_RETURN_EXTRA,s
    sta z:cursor
    sta z:original
    lda 5+LIBC_RETURN_EXTRA,s
    and #$ff
    sta z:cursor+2
    sta z:original+2
    phy
    ldy #0
    stz z:result
    stz z:result+2
    lda z:radix
    beq set_auto
    cmp #2
    bcc invalid_base
    cmp #37
    bcc skip_space
invalid_base:
    jmp .loword(finish)
set_auto:
    lda #automatic_base
    tsb z:flags
    lda #10
    sta z:radix
skip_space:
    lda [cursor]
    and #$ff
    cmp #' '
    beq whitespace
    cmp #9
    bcc sign
    cmp #14
    bcs sign
whitespace:
    advance_cursor
    bra skip_space
sign:
    cmp #'-'
    bne plus
    lda #negative
    tsb z:flags
    bra skip_sign
plus:
    cmp #'+'
    bne prefix
skip_sign:
    advance_cursor
prefix:
    lda [cursor]
    and #$ff
    cmp #'0'
    bne scan_digit
    lda z:flags
    bit #automatic_base
    beq explicit_hex
    lda #8
    sta z:radix
    bra try_hex
explicit_hex:
    lda z:radix
    cmp #16
    bne scan_digit
try_hex:
    ldy #1
    lda [cursor],y
    and #$df
    cmp #'X'
    bne reset_index
    iny
    jsr .loword(read_digit)
    cmp #16
    bcs reset_index
    lda #16
    sta z:radix
    advance_cursor
    advance_cursor
reset_index:
    ldy #0
scan_digit:
    jsr .loword(read_digit)
    cmp z:radix
    bcs check_range
    sta z:digit
    lda #consumed
    tsb z:flags
    lda z:flags
    bit #overflow
    bne next_digit

    ; Multiply the previous value by the radix and add the new digit
    ; Once overflow is known, keep scanning to find the true end pointer
    lda z:result
    sta z:multiple
    lda z:result+2
    sta z:multiple+2
    lda z:digit
    sta z:result
    stz z:result+2
    lda z:radix
    sta z:factor
multiply:
    lsr z:factor
    bcc shift_multiple
    clc
    lda z:result
    adc z:multiple
    sta z:result
    lda z:result+2
    adc z:multiple+2
    sta z:result+2
    bcs mark_overflow
shift_multiple:
    lda z:factor
    beq next_digit
    asl z:multiple
    rol z:multiple+2
    bcc multiply
mark_overflow:
    lda #overflow
    tsb z:flags
next_digit:
    advance_cursor
    bra scan_digit

check_range:
    lda z:flags
    bit #overflow
    bne saturate
    bit #unsigned_mode
    bne apply_sign
    lda z:result+2
    cmp #$8000
    bcc apply_sign
    bne saturate
    lda z:flags
    bit #negative
    beq saturate
    lda z:result
    bne saturate
apply_sign:
    lda z:flags
    bit #negative
    beq finish
    sec
    lda #0
    sbc z:result
    sta z:result
    lda #0
    sbc z:result+2
    sta z:result+2
    bra finish
saturate:
    lda #34
    sta a:.loword(_errno)
    lda z:flags
    bit #unsigned_mode
    beq signed_saturation
    lda #$ffff
    sta z:result
    sta z:result+2
    bra finish
signed_saturation:
    bit #negative
    bne signed_minimum
    lda #$ffff
    sta z:result
    lda #$7fff
    bra save_high
signed_minimum:
    stz z:result
    lda #$8000
save_high:
    sta z:result+2
finish:
    ldx z:endptr
    beq return_value
    lda z:flags
    bit #consumed
    beq original_end
    lda z:cursor
    sta a:0,x
    lda z:cursor+2
    bra store_bank
original_end:
    lda z:original
    sta a:0,x
    lda z:original+2
store_bank:
    and #$ff
    sta a:2,x
return_value:
    lda z:result
    ldx z:result+2
    ply
    rts

read_digit:
    lda [cursor],y
    and #$ff
    cmp #'0'
    bcc invalid_digit
    cmp #'9'+1
    bcs letter
    sec
    sbc #'0'
    rts
letter:
    and #$df
    cmp #'A'
    bcc invalid_digit
    cmp #'Z'+1
    bcs invalid_digit
    sec
    sbc #'A'-10
    rts
invalid_digit:
    lda #$ffff
    rts
