.setcpu "65816"
.a16
.i16
.importzp __arith_lhs, __arith_rhs
.export __mul32
L=__arith_lhs
R=__arith_rhs
T=__arith_lhs+8
.segment "CODE"
__mul32:
    lda z:R+1
    ora z:R+2
    bne @full
    jmp .loword(mul32_byte)
@full:
    ; Low 32 bits of the byte partial products. Signed multiplication has the
    ; same low bits. S-CPU registers use bank-zero long accesses; Y and X width stay 16
    stz z:T+2
    .repeat 4, I
        .repeat 4, J
            .if I+J < 4
    sep #$20
.a8
                .if J = 0
    ; WRMPYA latches; each multiplicand byte is written once
    lda z:L+I
    sta f:$004202
                .endif
    lda z:R+J
    sta f:$004203
                .if I+J = 3
    ; CLC(2), LDA dp(3), ADC fetches(3): eight cycles before data read
    clc
    lda z:T+3
    adc f:$004216
    sta z:T+3
    rep #$20
.a16
                .else
    ; REP(3), CLC(2), LDA fetches(3): eight cycles before data read
    rep #$20
.a16
    clc
    lda f:$004216
                    .if I+J = 0
    sta z:T
                    .else
    adc z:T+I+J
    sta z:T+I+J
                        .if I+J = 1
    sep #$20
.a8
    lda z:T+3
    adc #0
    sta z:T+3
    rep #$20
.a16
                        .endif
                    .endif
                .endif
            .endif
        .endrepeat
    .endrepeat
    lda z:T
    ldx z:T+2
    rts
mul32_byte:
    ; The upper byte of each partial product is the carry into the
    ; next column. Overlapping stores put it at the next ADC address
    stz z:T+2
    sep #$20
.a8
    lda z:R
    sta f:$004202
    .repeat 3, I
    lda z:L+I
    sta f:$004203
    rep #$20
.a16
    clc
    lda f:$004216
    .if I
    adc z:T+I
    .endif
    sta z:T+I
    sep #$20
.a8
    .endrepeat
    lda z:L+3
    sta f:$004203
    clc
    lda z:T+3
    adc f:$004216
    sta z:T+3
    rep #$20
.a16
    lda z:T
    ldx z:T+2
    rts
