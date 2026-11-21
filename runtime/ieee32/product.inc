; Unrolled unsigned 24x24 -> 48 product. CPU hardware only
    sep #32
.a8
    lda z:ma+0
    sta f:$004202
    lda z:mb+0
    sta f:$004203
    rep #32
.a16
    ; pr starts at zero. Keep the original two-cycle multiply wait
    nop
    lda f:$004216
    sta z:pr+0
    sep #32
.a8
    lda z:ma+0
    sta f:$004202
    lda z:mb+1
    sta f:$004203
    rep #32
.a16
    clc
    lda f:$004216
    adc z:pr+1
    sta z:pr+1
    lda z:pr+3
    adc #0
    sta z:pr+3
    sep #32
.a8
    lda z:pr+5
    adc #0
    sta z:pr+5
    lda z:ma+0
    sta f:$004202
    lda z:mb+2
    sta f:$004203
    rep #32
.a16
    clc
    lda f:$004216
    adc z:pr+2
    sta z:pr+2
    lda z:pr+4
    adc #0
    sta z:pr+4
    sep #32
.a8
    lda z:ma+1
    sta f:$004202
    lda z:mb+0
    sta f:$004203
    rep #32
.a16
    clc
    lda f:$004216
    adc z:pr+1
    sta z:pr+1
    lda z:pr+3
    adc #0
    sta z:pr+3
    sep #32
.a8
    lda z:pr+5
    adc #0
    sta z:pr+5
    lda z:ma+1
    sta f:$004202
    lda z:mb+1
    sta f:$004203
    rep #32
.a16
    clc
    lda f:$004216
    adc z:pr+2
    sta z:pr+2
    lda z:pr+4
    adc #0
    sta z:pr+4
    sep #32
.a8
    lda z:ma+1
    sta f:$004202
    lda z:mb+2
    sta f:$004203
    rep #32
.a16
    clc
    lda f:$004216
    adc z:pr+3
    sta z:pr+3
    sep #32
.a8
    lda z:pr+5
    adc #0
    sta z:pr+5
    lda z:ma+2
    sta f:$004202
    lda z:mb+0
    sta f:$004203
    rep #32
.a16
    clc
    lda f:$004216
    adc z:pr+2
    sta z:pr+2
    lda z:pr+4
    adc #0
    sta z:pr+4
    sep #32
.a8
    lda z:ma+2
    sta f:$004202
    lda z:mb+1
    sta f:$004203
    rep #32
.a16
    clc
    lda f:$004216
    adc z:pr+3
    sta z:pr+3
    sep #32
.a8
    lda z:pr+5
    adc #0
    sta z:pr+5
    lda z:ma+2
    sta f:$004202
    lda z:mb+2
    sta f:$004203
    rep #32
.a16
    clc
    lda f:$004216
    adc z:pr+4
    sta z:pr+4
