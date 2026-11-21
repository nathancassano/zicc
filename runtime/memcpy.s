; Near destination in X; far source at 3,S; unsigned count at 7,S
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _memcpy, __memcpy_resume
.segment "CODE"
_memcpy:
    lda 7,s
    beq @empty
    clc
    adc 3,s
    bcc @block
    beq @block                  ; Ending exactly at the bank boundary is safe
    ; MVN wraps X within a bank. Long indirect indexing carries instead
    phy
    phx
    pei (__dp_scratch)
    pei (__dp_scratch+2)
    lda 11,s
    sta z:__dp_scratch
    lda 13,s
    and #$00FF
    sta z:__dp_scratch+2
    lda 15,s
    pha                         ; Remaining count
    ldy #0
@byte:
    sep #$20
.a8
    lda [__dp_scratch],y
    sta a:$0000,x
    rep #$20
.a16
    inx
    iny
    lda 1,s
    dec a
    sta 1,s
    bne @byte
    pla
    pla
    sta z:__dp_scratch+2
    pla
    sta z:__dp_scratch
    pla
    ply
    rts
@empty:
    txa
    rts
@block:
    phy
    phx
    phb
    ; A private stack thunk supplies MVN's immediate source bank. Execute in
    ; bank $00, where the hardware stack is mapped, then RTL back to our PBR
    ; Bytes at 1,S: $54, $7E, source bank, $6B (MVN source,$7E; RTL)
    sep #$20
.a8
    lda #$6B
    pha
    lda 11,s
    pha
    lda #$7E
    pha
    lda #$54
    pha
    rep #$20
.a16
    lda 6,s                     ; Original destination
    tay
    lda 12,s                    ; Source offset
    tax
    phk
    pea .loword(__memcpy_resume-1)
    sep #$20
.a8
    lda #0
    pha                         ; Thunk PBR
    rep #$20
.a16
    tsc
    clc
    adc #4                      ; Thunk address minus one for RTL
    pha
    lda 22,s                    ; Original count
    dec a
    rtl
__memcpy_resume:
    pla                         ; Discard thunk only after it returns
    pla
    plb
    pla
    ply
    rts
