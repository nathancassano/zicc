; Compare unsigned bytes through two arbitrary far pointers
.setcpu "65816"
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif
left_ptr = 7+LIBC_RETURN_EXTRA
right_ptr = left_ptr+4
.a16
.i16
.export _strcmp
.segment "CODE"
_strcmp:
    phy
    phd
    tsc
    tax                         ; keep the restore stack pointer across bank wraps
    tcd                         ; both caller-owned far pointers are now DP operands
    ldy #0
    sep #$20
.a8
    ; The short prefix also handles one-byte strings without paying for
    ; pointer identity. Y cannot wrap in these first two iterations
    .repeat 2
        lda [left_ptr],y
        cmp [right_ptr],y
        bne @different
        cmp #0
        beq @equal
        iny
    .endrepeat
    rep #$20
.a16
    lda z:left_ptr
    cmp z:right_ptr
    bne @more
    lda z:left_ptr+2
    eor z:right_ptr+2
    and #$00ff
    beq @restore
@more:
    sep #$20
.a8
@compare:
    lda [left_ptr],y
    beq @left_zero
    cmp [right_ptr],y
    bne @different
    iny
    bne @compare
    ; On a full Y wrap, advance private copies of both pointers. Reset S
    ; first so further wraps reuse the same eight bytes without recursion
    rep #$20
.a16
    txs
    lda z:right_ptr+2
    inc a
    pha
    pei (right_ptr)
    lda z:left_ptr+2
    inc a
    pha
    pei (left_ptr)
    tsc
    sec
    sbc #left_ptr-1
    tcd
    sep #$20
.a8
    bra @compare
@left_zero:
    cmp [right_ptr],y
    beq @equal
@different:
    rep #$20
.a16
    lda #1
    bcs @restore
    lda #$FFFF
    bra @restore
@equal:
    rep #$20
.a16
    lda #0
@restore:
    txs
    pld
    ply
    rts
