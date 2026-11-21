.setcpu "65816"
.a16
.i16
.export _qsort
.importzp __arith_lhs, __arith_rhs
.include "callback.inc"
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

base = 1
next = 3
remaining = 5
size = 7
compare = 9
right = 13
left = 15
frame = 16
args = frame + 7 + LIBC_RETURN_EXTRA

.segment "CODE"
_qsort:
    cmp #2
    bcs :+
    rts
:
    phy
    pha
    tsc
    sec
    sbc #frame
    tcs
    tay
    txa
    sta a:base,y
    lda frame+1,s
    dec a
    sta a:remaining,y
    lda args,s
    bne :+
    jmp .loword(qsort_done)
:
    sta a:size,y
    lda args+2,s
    sta a:compare,y
    lda args+4,s
    sta a:compare+2,y
    lda a:base,y
qsort_advance:
    clc
    adc a:size,y
    sta a:next,y
    sta a:right,y
qsort_insert:
    sec
    sbc a:size,y
    sta a:left,y
    lda a:compare,y
    sta z:__arith_rhs
    lda a:compare+2,y
    sta z:__arith_rhs+2
    ldx a:left,y
    lda a:right,y
    invoke_comparator
    cmp #0
    bmi qsort_ordered
    beq qsort_ordered

    ; Swap adjacent elements byte by byte, including odd-sized records
    lda a:left,y
    sta z:__arith_lhs
    lda a:right,y
    sta z:__arith_rhs
    ldx a:size,y
    phy
    ldy #0
    sep #$20
.a8
qsort_swap:
    lda (__arith_lhs),y
    pha
    lda (__arith_rhs),y
    sta (__arith_lhs),y
    pla
    sta (__arith_rhs),y
    iny
    dex
    bne qsort_swap
    rep #$20
.a16
    ply
    lda a:left,y
    cmp a:base,y
    beq qsort_ordered
    sta a:right,y
    bra qsort_insert
qsort_ordered:
    lda a:remaining,y
    dec a
    sta a:remaining,y
    beq qsort_done
    lda a:next,y
    bra qsort_advance
qsort_done:
    tya
    clc
    adc #frame+2
    tcs
    ply
qsort_empty:
    rts
