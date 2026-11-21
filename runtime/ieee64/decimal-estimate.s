; Approximate unsigned decimal significand times 10^A
; Input: __arith_lhs+0..7 unsigned integer, A signed decimal exponent in
; -343..308. Output: approximate nonnegative IEEE binary64 in +0..7
; This is a search seed: exact decimal midpoint comparison must determine
; the final rounded result. A/flags and scratch +8..+31 clobbered;
; X/Y/D/DBR preserved. Native A16/X16, D=0, DBR=$7E
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.import __ufloat64_64, __dmul
.export __ieee64_decimal_estimate
.segment "CODE"
__ieee64_decimal_estimate:
    phx
    ora #0
    bpl @positive
    eor #$ffff
    inc a
    sta z:__arith_lhs+26
    lda #72
    bra @table
@positive:
    sta z:__arith_lhs+26
    lda #0
@table:
    sta z:__arith_lhs+30
    stz z:__arith_lhs+28
    jsr .loword(__ufloat64_64)
@next:
    lda z:__arith_lhs+26
    beq @done
    lsr a
    sta z:__arith_lhs+26
    bcc @advance
    lda z:__arith_lhs+28
    clc
    adc z:__arith_lhs+30
    tax
    lda f:decimal_powers+0,x
    sta z:__arith_lhs+8
    lda f:decimal_powers+2,x
    sta z:__arith_lhs+10
    lda f:decimal_powers+4,x
    sta z:__arith_lhs+12
    lda f:decimal_powers+6,x
    sta z:__arith_lhs+14
    jsr .loword(__dmul)
@advance:
    lda z:__arith_lhs+28
    clc
    adc #8
    sta z:__arith_lhs+28
    bra @next
@done:
    plx
    rts
.segment "RODATA"
; Nearest binary64 values to 10^(1,2,4,...,256) and their reciprocals
decimal_powers:
    .word $0000,$0000,$0000,$4024
    .word $0000,$0000,$0000,$4059
    .word $0000,$0000,$8800,$40c3
    .word $0000,$0000,$d784,$4197
    .word $8000,$37e0,$c379,$4341
    .word $6e17,$b505,$b8b5,$4693
    .word $f9f5,$e93f,$4f03,$4d38
    .word $1d32,$f930,$7748,$5a82
    .word $bf3c,$7f73,$4fdd,$7515
    .word $999a,$9999,$9999,$3fb9
    .word $147b,$47ae,$7ae1,$3f84
    .word $432d,$eb1c,$36e2,$3f1a
    .word $8c3a,$e230,$798e,$3e45
    .word $89bc,$97d8,$d2b2,$3c9c
    .word $a733,$d5a8,$f623,$3949
    .word $a73d,$44f4,$0ffd,$32a5
    .word $979d,$cf8c,$ba08,$255b
    .word $6f43,$64ac,$0628,$0ac8
