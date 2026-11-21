.setcpu "65816"
.a16
.i16
.export _sram_capacity, _sram_read, _sram_write
.import __sram_capacity: far
.import __sram_window_size, __sram_window_shift, __sram_base, __sram_first_bank
.importzp __dp_scratch

.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA = 0
.endif

; Buffer arrives in A, the offset and count on the stack
ARG = 3 + LIBC_RETURN_EXTRA
CURSOR = __dp_scratch
REMAINING = __dp_scratch+4
CHUNK = __dp_scratch+6
WRITING = __dp_scratch+8

.macro copy_chunk writing
    ldy #0
    sep #$20
    .a8
:
    .if writing
        lda a:$0000,x
        sta [CURSOR],y
    .else
        lda [CURSOR],y
        sta a:$0000,x
    .endif
    inx
    iny
    cpy z:CHUNK
    bne :-
    rep #$20
    .a16
.endmacro

.segment "CODE"
_sram_capacity:
    lda #.loword(__sram_capacity)
    ldx #.bankbyte(__sram_capacity)
    rts

_sram_read:
    phy
    ldy #0
    bra transfer
_sram_write:
    phy
    ldy #1
transfer:
    tax
    ; Subtract the offset as a 32-bit value before checking the count
    sec
    lda #.loword(__sram_capacity)
    sbc ARG+2,s
    pha
    lda #.bankbyte(__sram_capacity)
    sbc ARG+6,s
    bcs @available
    pla
    bra @invalid
@available:
    bne @wide
    pla
    cmp ARG+6,s
    bcc @invalid
    bra @check_buffer
@wide:
    pla
@check_buffer:
    lda ARG+6,s
    beq @ok
    cpx #0
    bne @start
@invalid:
    lda #1
    ply
    rts
@ok:
    lda #0
    ply
    rts

@start:
    pei (CURSOR)
    pei (CURSOR+2)
    pei (REMAINING)
    pei (CHUNK)
    pei (WRITING)
    sta z:REMAINING
    sty z:WRITING
    lda ARG+12,s
    sta z:CURSOR
    lda ARG+14,s
    sta z:CURSOR+2
    ldy #__sram_window_shift
@shift:
    lsr z:CURSOR+2
    ror z:CURSOR
    dey
    bne @shift
    clc
    lda z:CURSOR
    adc #__sram_first_bank
    sta z:CURSOR+2
    lda ARG+12,s
    and #.loword(__sram_window_size-1)
    clc
    adc #__sram_base
    sta z:CURSOR
@chunk:
    sec
    lda #.loword(__sram_base+__sram_window_size)
    sbc z:CURSOR
    cmp z:REMAINING
    bcc @copy
    lda z:REMAINING
@copy:
    sta z:CHUNK
    lda z:REMAINING
    sec
    sbc z:CHUNK
    sta z:REMAINING
    lda z:WRITING
    beq @read
    copy_chunk 1
    bra @next
@read:
    copy_chunk 0
@next:
    lda z:REMAINING
    beq @done
    lda #__sram_base
    sta z:CURSOR
    inc z:CURSOR+2
    bra @chunk
@done:
    pla
    sta z:WRITING
    pla
    sta z:CHUNK
    pla
    sta z:REMAINING
    pla
    sta z:CURSOR+2
    pla
    sta z:CURSOR
    brl @ok
