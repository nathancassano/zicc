; 64-bit division and remainder, native A/X 16-bit
; L=operand/result at scratch +0; R=divisor at +8. Scratch +16..+25
; is clobbered, as are A/X/flags. Y, D, DBR and R are preserved for
; unsigned operations; signed operations may negate R. Division by zero
; and signed overflow have the same undefined status as in C
; __udiv64 also returns the remainder in M for decimal conversion
.setcpu "65816"
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.export __udiv64, __uquot64, __umod64, __sdiv64, __smod64
.export __udiv64_soft, __umod64_soft, __sdiv64_soft, __smod64_soft
L = __arith_lhs
R = __arith_lhs+8
M = __arith_lhs+16
MODE = __arith_lhs+24
PAIRED = $8000
.segment "CODE"
__uquot64:
    stz z:MODE
    bra divide64
__umod64:
    lda #4
    sta z:MODE
    bra divide64
__sdiv64:
    stz z:MODE
    bra signed64
__smod64:
    lda #4
    sta z:MODE
    bra signed64
; Interrupt handlers use software even for byte divisors so they can
; interrupt a foreground hardware multiply or divide in flight
__udiv64_soft:
    lda #8
    sta z:MODE
    bra divide64
__umod64_soft:
    lda #12
    sta z:MODE
    bra divide64
__sdiv64_soft:
    lda #8
    sta z:MODE
    bra signed64
__smod64_soft:
    lda #12
    sta z:MODE
signed64:
    lda z:L+6
    bpl :+
    lda z:MODE
    ora #3                  ; negative quotient and remainder
    sta z:MODE
    jsr .loword(negate_l64)
:
    lda z:R+6
    bpl divide64
    lda z:MODE
    eor #1                  ; divisor sign changes quotient only
    sta z:MODE
    sec
    lda #0
    sbc z:R
    sta z:R
    lda #0
    sbc z:R+2
    sta z:R+2
    lda #0
    sbc z:R+4
    sta z:R+4
    lda #0
    sbc z:R+6
    sta z:R+6
divide64:
    lda z:MODE
    bit #8
    bne @software
    lda z:R+6
    ora z:R+4
    ora z:R+2
    bne @software
    lda z:R
    beq @software
    cmp #$0100
    bcs @word
    lda z:MODE
    bit #4
    beq :+
    jmp .loword(divide64_mod_byte)
:
    jmp .loword(divide64_byte)
@word:
    stz z:M
    stz z:M+2
    stz z:M+4
    stz z:M+6
@word_ready:
    jmp .loword(divide64_word)
@software:
    stz z:M
    stz z:M+2
    stz z:M+4
    stz z:M+6
    lda z:R+6
    bmi @single
    bne @seed3
    lda z:R+4
    bne @three_words
    lda z:R+2
    bne @two_words
    lda z:R
    bne @word_ready
    ; Preserve the deterministic restoring path for zero divisors
    lda z:L+6
    bne @unseeded
    lda z:L+4
    bne divide64_seed1
    lda z:L+2
    bne @seed2
@seed3:
    jmp .loword(divide64_seed3)
@single:
    jmp .loword(divide64_single)
@two_words:
    lda z:L+6
    bne divide64_seed1_2
    lda z:L+4
    bne divide64_seed2_2
    lda z:L+2
    jeq divide64_zero_quotient
    ldx #2
    jmp .loword(divide64_loop2)
@three_words:
    lda z:L+6
    ora z:L+4
    jeq divide64_zero_quotient
    bra divide64_seed2_3
@seed2:
    jmp .loword(divide64_seed2)
@unseeded:
    ldx #6
    bra divide64_loop4

.macro seed_remainder words, loop
    .repeat words, I
        lda z:L+2*(4-words+I)
        sta z:M+2*I
        stz z:L+2*(4-words+I)
    .endrepeat
    ldx #6-2*words
    jmp .loword(loop)
.endmacro
divide64_seed1:
    seed_remainder 1, divide64_loop4
divide64_seed2:
    seed_remainder 2, divide64_loop4
divide64_seed3:
    seed_remainder 3, divide64_loop4
divide64_seed1_2:
    seed_remainder 1, divide64_loop2
divide64_seed2_2:
    seed_remainder 2, divide64_loop2
divide64_seed2_3:
    seed_remainder 2, divide64_loop3

.macro divide_words words
    .local top, word_loop, bit_loop, subtract_high, subtract, reload_high, next_bit
    top = (words-1)*2
    phy
    lda z:M+top
word_loop:
    ldy #16
bit_loop:
    ; Consume one dividend word at a time and replace it with its quotient
    asl z:L,x
    .repeat words-1, I
        rol z:M+I*2
    .endrepeat
    rol a
    .if words < 4
        bcs subtract_high   ; remainder overflow implies M >= R
    .endif
    cmp z:R+top
    bcc next_bit
    bne subtract_high
    ; Equal top words need a lower-word comparison. Keep A available
    ; for the next bit by reloading the saved top word on rejection
    sta z:M+top
    .repeat words-2, I
        lda z:M+top-2-I*2
        cmp z:R+top-2-I*2
        bcc reload_high
        bne subtract
    .endrepeat
    lda z:M
    cmp z:R
    bcs subtract
reload_high:
    lda z:M+top
    bra next_bit
subtract_high:
    sta z:M+top
subtract:
    .repeat words-1, I
        lda z:M+I*2
        sbc z:R+I*2
        sta z:M+I*2
    .endrepeat
    lda z:M+top
    sbc z:R+top
    inc z:L,x               ; low bit is clear following the shift
next_bit:
    dey
    bne bit_loop
    dex
    dex
    bpl word_loop
    sta z:M+top
    ply
    jmp .loword(divide64_result)
.endmacro
divide64_loop4:
    divide_words 4
divide64_loop3:
    divide_words 3
divide64_loop2:
    divide_words 2
divide64_result:
    lda z:MODE
    bit #4
    beq divide64_quotient_sign
    lda z:M
    sta z:L
    lda z:M+2
    sta z:L+2
    lda z:M+4
    sta z:L+4
    lda z:M+6
    sta z:L+6
    lda z:MODE
divide64_remainder_sign:
    bit #2
    bne negate_l64
    rts
divide64_quotient_sign:
    bit #1
    bne negate_l64
    rts

negate_l64:
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

; The first dividend is a full word. Each following dividend combines one
; byte with the preceding remainder, so its quotient is a single byte
divide64_byte:
    ldx #6
@leading:
    lda z:L,x
    bne @first
    dex
    dex
    bpl @leading
    bra @seed_remainder
@first:
    cmp z:R
    bcc @small_prefix
    jsr .loword(divide64_hardware)
    lda f:$004214
    sta z:L,x
    dex
    bmi @done
@next:
    sep #$20
.a8
    lda f:$004216
@feed_byte:
    xba
    lda z:L,x
    rep #$20
.a16
    jsr .loword(divide64_hardware)
    sep #$20
.a8
    lda f:$004214
    sta z:L,x
    rep #$20
.a16
    dex
    bpl @next
@done:
    lda z:MODE
    bpl divide64_quotient_sign
    lda f:$004216
@save_remainder:
    sta z:M
    stz z:M+2
    stz z:M+4
    stz z:M+6
    rts
@small_prefix:
    ; The first quotient word is zero and its remainder is the dividend word
    stz z:L,x
    dex
    bmi @seed_remainder
    sep #$20
.a8
    bra @feed_byte
.a16
@seed_remainder:
    bit z:MODE
    bmi @save_remainder
    lda z:MODE
    jmp .loword(divide64_quotient_sign)

; Remainder-only division need not read or store any quotient bytes
divide64_mod_byte:
    ldx #6
@leading:
    lda z:L,x
    bne @first
    dex
    dex
    bpl @leading
    bra @store
@first:
    cmp z:R
    bcc @small_prefix
    jsr .loword(divide64_hardware)
    dex
    bmi @remainder
@next:
    sep #$20
.a8
    lda f:$004216
@feed_byte:
    xba
    lda z:L,x
    rep #$20
.a16
    jsr .loword(divide64_hardware)
    dex
    bpl @next
@remainder:
    lda f:$004216
@store:
    sta z:L
    stz z:L+2
    stz z:L+4
    stz z:L+6
    lda z:MODE
    jmp .loword(divide64_remainder_sign)
@small_prefix:
    dex
    bmi @store
    sep #$20
.a8
    bra @feed_byte
.a16

divide64_hardware:
    sta f:$004204
    sep #$20
.a8
    lda z:R
    sta f:$004206
    rep #$20
.a16
    ; REP, two NOPs, RTS and the caller's long fetch cover 16 CPU cycles
    nop
    nop
    rts
; With a word divisor, each dividend word becomes one quotient word
; Only the remainder in A flows between words. No hardware is required
divide64_word:
    cmp #$0100
    beq divide64_byte_boundary
    ldx #6
@leading:
    lda z:L,x
    bne @first
    dex
    dex
    bpl @leading
    jmp .loword(divide64_result)
@first:
    phy
    cmp z:R
    bcs @no_prefix
    stz z:L,x
    dex
    dex
    bpl @word
    bra @done
@no_prefix:
    lda #0
@word:
    ldy #16
@bit:
    asl z:L,x
    rol a
    bcs @subtract           ; the 17th remainder bit is set
    cmp z:R
    bcc @next
@subtract:
    sbc z:R
    inc z:L,x
@next:
    dey
    bne @bit
    dex
    dex
    bpl @word
@done:
    sta z:M
    ply
    jmp .loword(divide64_result)

divide64_byte_boundary:
    ; A divisor of 256 splits the low byte from the quotient directly
    lda z:L
    and #$00ff
    sta z:M
    lda z:MODE
    bit #4
    bne @done
    lda z:L+1
    sta z:L
    lda z:L+3
    sta z:L+2
    lda z:L+5
    sta z:L+4
    lda z:L+6
    xba
    and #$00ff
    sta z:L+6
@done:
    jmp .loword(divide64_result)

; A divisor with bit 63 set has at most one quotient bit
divide64_single:
    sec
    .repeat 4, I
        lda z:L+I*2
        sbc z:R+I*2
        sta z:M+I*2
    .endrepeat
    bcc divide64_zero_quotient
    lda z:MODE
    bit #4
    bne divide64_single_remainder
    lda #1
    sta z:L
    stz z:L+2
    stz z:L+4
    stz z:L+6
    jmp .loword(divide64_result)
divide64_zero_quotient:
    lda z:MODE
    bit #4
    bne @original_remainder
    bpl @clear
    lda z:L
    sta z:M
    lda z:L+2
    sta z:M+2
    lda z:L+4
    sta z:M+4
    lda z:L+6
    sta z:M+6
@clear:
    stz z:L
    stz z:L+2
    stz z:L+4
    stz z:L+6
    rts
@original_remainder:
    jmp .loword(divide64_remainder_sign)
divide64_single_remainder:
    jmp .loword(divide64_result)

; Decimal conversion consumes both the quotient in L and the remainder in M
__udiv64:
    lda #PAIRED
    sta z:MODE
    jmp .loword(divide64)
