.setcpu "65816"
.a16
.i16
.macpack longbranch
.export _far_heap_init, _far_malloc, _far_calloc, _far_realloc, _far_free
.import __NEAR_START__, __NEAR_LAST__, __RUNTIME_RAM_BOTTOM__
.importzp __arith_lhs

; Heap handle in X. Other arguments are 32-bit stack slots in declaration order
.ifdef FAR_HEAP_LONG_CALLS
ARG = 4
.else
ARG = 3
.endif

.macro return_to_c
.ifdef FAR_HEAP_LONG_CALLS
    rtl
.else
    rts
.endif
.endmacro

; First-fit blocks have an even 32-bit span including the four-byte header
; Bit zero marks a busy block. The smallest block has two bytes of payload
HEADER = 4
MIN_BLOCK = 6
WALK      = __arith_lhs
LIMIT     = __arith_lhs+4
SPAN      = __arith_lhs+8
NEED      = __arith_lhs+12
NEXT      = __arith_lhs+16
PREVIOUS  = __arith_lhs+20
SAVED_PTR = __arith_lhs+24
SAVED_LEN = __arith_lhs+28

.macro add_pair left, right, result
    clc
    lda z:left
    adc z:right
    sta z:result
    lda z:left+2
    adc z:right+2
    sta z:result+2
.endmacro

.macro payload_to_header payload, header
    sec
    lda z:payload
    sbc #HEADER
    sta z:header
    lda z:payload+2
    sbc #0
    sta z:header+2
.endmacro

.segment "CODE"

_far_heap_init:
    lda ARG+6,s
    ora ARG+4,s
    bne @nonempty
    stz a:0,x
    stz a:2,x
    stz a:4,x
    stz a:6,x
    lda #1
    return_to_c
@nonempty:
    lda ARG,s
    ora ARG+4,s
    bit #1
    jne @invalid
    lda ARG+6,s
    cmp #3
    jcs @invalid
    cmp #2
    bne @check_minimum
    lda ARG+4,s
    jne @invalid
    bra @check_bank
@check_minimum:
    cmp #0
    bne @check_bank
    lda ARG+4,s
    cmp #MIN_BLOCK
    jcc @invalid
@check_bank:
    lda ARG+2,s
    cmp #$007F
    beq @check_end
    cmp #$007E
    bne @invalid
    lda ARG,s
    cmp #.loword(__NEAR_START__)
    bcc @invalid
@check_end:
    clc
    lda ARG,s
    adc ARG+4,s
    sta z:LIMIT
    lda ARG+2,s
    adc ARG+6,s
    sta z:LIMIT+2
    cmp #.bankbyte(__RUNTIME_RAM_BOTTOM__)
    bcc @check_near_heap
    bne @invalid
    lda #.loword(__RUNTIME_RAM_BOTTOM__)
    cmp z:LIMIT
    bcc @invalid
@check_near_heap:
    lda ARG+2,s
    cmp #$007E
    bne @install
    lda #.bankbyte(__NEAR_LAST__)
    cmp #$007F
    bcs @install
    lda z:LIMIT+2
    cmp #$007F
    bcs @invalid
    lda #.loword(__NEAR_LAST__)
    cmp z:LIMIT
    bcc @invalid
@install:
    lda ARG,s
    sta z:WALK
    sta a:0,x
    lda ARG+2,s
    sta z:WALK+2
    sta a:2,x
    lda ARG+4,s
    sta a:4,x
    sta [WALK]
    lda ARG+6,s
    sta a:6,x
    phy
    ldy #2
    sta [WALK],y
    ply
    lda #1
    return_to_c
@invalid:
    lda #0
    return_to_c

_far_malloc:
    lda ARG,s
    sta z:NEED
    lda ARG+2,s
    sta z:NEED+2
    phy
    jsr .loword(allocate)
    ply
    return_to_c

_far_calloc:
    lda ARG+2,s
    cmp #2
    jcs return_null
    sta z:WALK+2
    lda ARG,s
    sta z:WALK
    ora z:WALK+2
    jeq return_null
    lda ARG+6,s
    cmp #2
    jcs return_null
    sta z:SPAN+2
    lda ARG+4,s
    sta z:SPAN
    ora z:SPAN+2
    jeq return_null
    stz z:NEED
    stz z:NEED+2
@multiply:
    lsr z:WALK+2
    ror z:WALK
    bcc @shift
    add_pair NEED, SPAN, NEED
    cmp #2
    jcs return_null
@shift:
    lda z:WALK
    ora z:WALK+2
    beq @allocate
    asl z:SPAN
    rol z:SPAN+2
    lda z:SPAN+2
    cmp #2
    bcc @multiply
    jmp .loword(return_null)
@allocate:
    lda z:NEED
    sta z:SAVED_LEN
    lda z:NEED+2
    sta z:SAVED_LEN+2
    phy
    jsr .loword(allocate)
    cpx #0
    beq @done
    pha
    phx
    sta z:WALK
    stx z:WALK+2
    ldy #0
    lda z:SAVED_LEN+2
    beq @tail
    lda #0
@full_window:
    sta [WALK],y
    iny
    iny
    bne @full_window
    inc z:WALK+2
@tail:
    lda z:SAVED_LEN
    and #$FFFE
    beq @odd_byte
    tax
    lda #0
@clear:
    sta [WALK],y
    iny
    iny
    dex
    dex
    bne @clear
@odd_byte:
    lda z:SAVED_LEN
    bit #1
    beq @restore
    sep #$20
    .a8
    lda #0
    sta [WALK],y
    rep #$20
    .a16
@restore:
    plx
    pla
@done:
    ply
    return_to_c

_far_free:
    lda ARG,s
    sta z:SAVED_PTR
    lda ARG+2,s
    sta z:SAVED_PTR+2
    phy
    jsr .loword(release)
    ply
    return_to_c

_far_realloc:
    lda ARG,s
    sta z:SAVED_PTR
    lda ARG+2,s
    sta z:SAVED_PTR+2
    lda ARG+4,s
    sta z:NEED
    lda ARG+6,s
    sta z:NEED+2
    phy
    lda z:SAVED_PTR
    ora z:SAVED_PTR+2
    bne @existing
    jsr .loword(allocate)
    bra @done
@existing:
    lda z:NEED
    ora z:NEED+2
    bne @capacity
    jsr .loword(release)
    lda #0
    tax
    bra @done
@capacity:
    payload_to_header SAVED_PTR, WALK
    ldy #2
    lda [WALK]
    and #$FFFE
    sec
    sbc #HEADER
    sta z:SAVED_LEN
    lda [WALK],y
    sbc #0
    sta z:SAVED_LEN+2
    cmp z:NEED+2
    bcc @grow
    bne @keep
    lda z:SAVED_LEN
    cmp z:NEED
    bcc @grow
@keep:
    lda z:SAVED_PTR
    ldx z:SAVED_PTR+2
    bra @done
@grow:
    phx
    jsr .loword(allocate)
    cpx #0
    beq @discard_heap
    stx z:NEXT+2
    sta z:NEXT
    phx
    pha
    ; A larger disjoint block fit in WRAM, so the old payload is under 64 KiB
    ldy #0
@copy:
    lda [SAVED_PTR],y
    sta [NEXT],y
    iny
    iny
    cpy z:SAVED_LEN
    bcc @copy
    lda 5,s
    tax
    jsr .loword(release)
    pla
    plx
@discard_heap:
    ply
@done:
    ply
    return_to_c

return_null:
    lda #0
    tax
    return_to_c

; Keep a full address for the walk and compare it with the exclusive end
heap_bounds:
    lda a:0,x
    sta z:WALK
    clc
    adc a:4,x
    sta z:LIMIT
    lda a:2,x
    sta z:WALK+2
    adc a:6,x
    sta z:LIMIT+2
    ldy #2
    rts

; NEED is the requested payload size. Keep SAVED_PTR and SAVED_LEN intact
allocate:
    lda z:NEED
    ora z:NEED+2
    jeq @null
    lda z:NEED+2
    cmp #2
    jcs @null
    clc
    lda z:NEED
    adc #HEADER+1
    and #$FFFE
    sta z:NEED
    lda z:NEED+2
    adc #0
    sta z:NEED+2
    cmp a:6,x
    bcc @start
    jne @null
    lda a:4,x
    cmp z:NEED
    jcc @null
@start:
    jsr .loword(heap_bounds)
@scan:
    lda [WALK]
    tax
    and #$FFFE
    sta z:SPAN
    lda [WALK],y
    sta z:SPAN+2
    txa
    lsr a
    bcs @advance
    lda z:SPAN+2
    cmp z:NEED+2
    bcc @advance
    bne @subtract
    lda z:SPAN
    cmp z:NEED
    bcc @advance
@subtract:
    sec
    lda z:SPAN
    sbc z:NEED
    sta z:SPAN
    lda z:SPAN+2
    sbc z:NEED+2
    sta z:SPAN+2
    bne @split
    lda z:SPAN
    cmp #MIN_BLOCK
    bcc @claim
@split:
    add_pair WALK, NEED, NEXT
    lda z:SPAN
    sta [NEXT]
    lda z:SPAN+2
    sta [NEXT],y
    lda z:NEED+2
    sta [WALK],y
    ldx z:NEED
@claim:
    txa
    ora #1
    sta [WALK]
    ldx z:WALK+2
    clc
    lda z:WALK
    adc #HEADER
    bcc @done
    inx
@done:
    rts
@advance:
    add_pair WALK, SPAN, WALK
    cmp z:LIMIT+2
    jne @scan
    lda z:WALK
    cmp z:LIMIT
    jne @scan
@null:
    lda #0
    tax
    rts

; SAVED_PTR is a payload address. Walk the actual headers to validate it
release:
    lda z:SAVED_PTR
    ora z:SAVED_PTR+2
    jeq @done
    lda a:4,x
    ora a:6,x
    jeq @done
    payload_to_header SAVED_PTR, SAVED_PTR
    jsr .loword(heap_bounds)
    stz z:PREVIOUS+2
@scan:
    lda [WALK]
    tax
    and #$FFFE
    sta z:SPAN
    lda [WALK],y
    sta z:SPAN+2
    lda z:WALK
    cmp z:SAVED_PTR
    bne @advance
    lda z:WALK+2
    cmp z:SAVED_PTR+2
    beq @found
@advance:
    txa
    lsr a
    bcs @forget_previous
    lda z:WALK
    sta z:PREVIOUS
    lda z:WALK+2
    bra @save_previous
@forget_previous:
    lda #0
@save_previous:
    sta z:PREVIOUS+2
    add_pair WALK, SPAN, WALK
    cmp z:LIMIT+2
    bne @scan
    lda z:WALK
    cmp z:LIMIT
    bne @scan
    rts
@found:
    txa
    lsr a
    bcc @done
    add_pair WALK, SPAN, NEXT
    cmp z:LIMIT+2
    bne @read_next
    lda z:NEXT
    cmp z:LIMIT
    beq @merge_previous
@read_next:
    lda [NEXT]
    bit #1
    bne @merge_previous
    clc
    adc z:SPAN
    sta z:SPAN
    lda [NEXT],y
    adc z:SPAN+2
    sta z:SPAN+2
@merge_previous:
    lda z:PREVIOUS+2
    beq @write_current
    lda [PREVIOUS]
    clc
    adc z:SPAN
    sta [PREVIOUS]
    lda [PREVIOUS],y
    adc z:SPAN+2
    sta [PREVIOUS],y
    rts
@write_current:
    lda z:SPAN
    sta [WALK]
    lda z:SPAN+2
    sta [WALK],y
@done:
    rts
