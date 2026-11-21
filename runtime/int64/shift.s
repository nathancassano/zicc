; 64-bit shift primitives, native mode A/X/Y 16-bit
; Operand/result: __arith_lhs through +7, little endian
; Shift count: __arith_lhs+8. A, X and flags are clobbered;
; Y, D and DBR are preserved. Counts are reduced modulo 64, matching
; the existing 32-bit helpers (out-of-range C shifts are undefined)
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __shl64, __ushr64, __sshr64
L = __arith_lhs
C = __arith_lhs+8

.macro right_byte
    lda z:L+1
    sta z:L
    lda z:L+3
    sta z:L+2
    lda z:L+5
    sta z:L+4
    lda z:L+6
    xba
    and #$00ff
.endmacro
.segment "CODE"
__shl64:
    lda z:C
    and #63
@words:
    cmp #8
    bcc @bits
    cmp #16
    bcc @byte
    sec
    sbc #16
    pha
    lda z:L+4
    sta z:L+6
    lda z:L+2
    sta z:L+4
    lda z:L
    sta z:L+2
    stz z:L
    pla
    bra @words
@byte:
    ; Unaligned word loads move the live bytes without changing A width
    and #7
    tax
    lda z:L+5
    sta z:L+6
    lda z:L+3
    sta z:L+4
    lda z:L+1
    sta z:L+2
    lda z:L
    xba
    and #$ff00
    sta z:L
    txa
@bits:
    tax
    beq @done
    lda z:L
@loop:
    asl a
    rol z:L+2
    rol z:L+4
    rol z:L+6
    dex
    bne @loop
    sta z:L
@done:
    rts
__ushr64:
    lda z:C
    and #63
@words:
    cmp #8
    bcc @bits
    cmp #16
    bcc @byte
    sec
    sbc #16
    pha
    lda z:L+2
    sta z:L
    lda z:L+4
    sta z:L+2
    lda z:L+6
    sta z:L+4
    stz z:L+6
    pla
    bra @words
@byte:
    and #7
    tax
    right_byte
    sta z:L+6
    txa
@bits:
    tax
    beq @done
    lda z:L+6
@loop:
    lsr a
    ror z:L+4
    ror z:L+2
    ror z:L
    dex
    bne @loop
    sta z:L+6
@done:
    rts
__sshr64:
    lda z:C
    and #63
@words:
    cmp #8
    bcc @bits
    cmp #16
    bcc @byte
    sec
    sbc #16
    pha
    lda z:L+2
    sta z:L
    lda z:L+4
    sta z:L+2
    lda z:L+6
    sta z:L+4
    bpl :+
    lda #$ffff
    bra :++
:   lda #0
:   sta z:L+6
    pla
    bra @words
@byte:
    and #7
    tax
    right_byte
    eor #$0080
    sec
    sbc #$0080
    sta z:L+6
    txa
@bits:
    tax
    beq @done
    lda z:L+6
@loop:
    cmp #$8000
    ror a
    ror z:L+4
    ror z:L+2
    ror z:L
    dex
    bne @loop
    sta z:L+6
@done:
    rts
