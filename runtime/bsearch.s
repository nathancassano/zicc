.setcpu "65816"
.a16
.i16
.export _bsearch
.importzp __arith_lhs, __arith_rhs
.include "callback.inc"
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

key = 1
base = 3
count = 5
size = 7
compare = 9
middle = 13
element = 15
frame = 16
args = frame + 7 + LIBC_RETURN_EXTRA

.segment "CODE"
_bsearch:
    phy
    pha
    tsc
    sec
    sbc #frame
    tcs
    tay
    txa
    sta a:key,y
    lda frame+1,s
    sta a:base,y
    lda args,s
    sta a:count,y
    lda args+2,s
    beq bsearch_missing
    sta a:size,y
    lda args+4,s
    sta a:compare,y
    lda args+6,s
    sta a:compare+2,y
bsearch_search:
    lda a:count,y
    beq bsearch_missing
    lsr a
    sta a:middle,y
    tax
    lda a:size,y
    sta z:__arith_lhs
    lda a:base,y
    cpx #0
    beq bsearch_element
    stx z:__arith_rhs
bsearch_scale:
    lsr z:__arith_rhs
    bcc bsearch_skip
    clc
    adc z:__arith_lhs
bsearch_skip:
    asl z:__arith_lhs
    ldx z:__arith_rhs
    bne bsearch_scale
bsearch_element:
    sta a:element,y
    lda a:compare,y
    sta z:__arith_rhs
    lda a:compare+2,y
    sta z:__arith_rhs+2
    ldx a:key,y
    lda a:element,y
    invoke_comparator
    cmp #0
    beq bsearch_found
    bmi bsearch_lower
    lda a:element,y
    clc
    adc a:size,y
    sta a:base,y
    lda a:count,y
    clc
    sbc a:middle,y
    bra bsearch_set_count
bsearch_lower:
    lda a:middle,y
bsearch_set_count:
    sta a:count,y
    bra bsearch_search
bsearch_found:
    ldx a:element,y
    bra bsearch_done
bsearch_missing:
    ldx #0
bsearch_done:
    tya
    clc
    adc #frame+2
    tcs
    ply
    txa
    rts
