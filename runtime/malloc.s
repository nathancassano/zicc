; First-fit near allocator. Header: even span including header, bit 0 busy
; Foreground only: malloc/free must not be reentered from interrupt handlers
.setcpu "65816"
.a16
.i16
.export _malloc, __heap_ready
.import __NEAR_LAST__
HEAP_BEGIN = .loword((__NEAR_LAST__ + 1) & $FFFFFE)
.segment "BSS"
__heap_ready: .res 2
.segment "CODE"
_malloc:
    txa                         ; First word argument is in X
    beq @null
    cmp #$FFFD
    bcs @null                   ; Rounding and header must not overflow
    inc a
    and #$FFFE
    inc a
    inc a
    phy
    pha                         ; Required span at 1,S
    ldx #HEAP_BEGIN
    beq @failure                ; Bank is full
    cpx #$FFFE
    beq @failure                ; A header alone cannot hold a payload
    lda a:.loword(__heap_ready)
    bne @scan
    inc a:.loword(__heap_ready)
    lda #0
    sec
    sbc #HEAP_BEGIN
    sta a:$0000,x
@scan:
    lda a:$0000,x
    bit #1
    bne @next
    cmp 1,s
    bcc @next
    sec
    sbc 1,s
    cmp #4
    bcc @whole                  ; Avoid an unusable two-byte fragment
    tay                         ; Remainder span
    txa
    clc
    adc 1,s
    tax
    tya
    sta a:$0000,x
    txa
    sec
    sbc 1,s
    tax
    lda 1,s
    bra @claim
@whole:
    lda a:$0000,x
@claim:
    ora #1
    sta a:$0000,x
    txa
    inc a
    inc a
    plx                         ; Discard required span, keep return value
    ply
    rts
@next:
    txa
    clc
    adc a:$0000,x
    bcs @failure                ; End of bank; busy bit cannot change carry
    and #$FFFE
    tax
    bra @scan
@failure:
    plx
    ply
@null:
    lda #0
    rts
