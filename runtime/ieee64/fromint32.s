; Convert a signed or unsigned 32-bit integer to exact IEEE binary64
; Integer input is scratch +0..3; result occupies +0..7. Scratch +8..+15
; and A/flags are clobbered. X/Y/D/DBR are preserved, in native 16-bit mode
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.export __sfloat64_32, __ufloat64_32
L = __arith_lhs
LO = __arith_lhs+8
HI = __arith_lhs+10
SG = __arith_lhs+12
EX = __arith_lhs+14
.segment "CODE"
__sfloat64_32:
    lda z:L+2
    bpl __ufloat64_32
    lda #$8000
    sta z:SG
    sec
    lda #0
    sbc z:L
    sta z:LO
    lda #0
    sbc z:L+2
    sta z:HI
    bra int32_to_double
__ufloat64_32:
    stz z:SG
    lda z:L
    sta z:LO
    lda z:L+2
    sta z:HI
int32_to_double:
    lda z:LO
    ora z:HI
    bne @nonzero
    stz z:L
    stz z:L+2
    stz z:L+4
    stz z:L+6
    rts
@nonzero:
    lda #1054             ; exponent of bit 31, biased by 1023
    sta z:EX
@normalize:
    lda z:HI
    bmi @packed
    asl z:LO
    rol z:HI
    dec z:EX
    bra @normalize
@packed:
    ; Drop the implicit bit and shift the remaining 31 bits left 21
    lda z:HI
    and #$7fff
    sta z:HI
    stz z:L
    lda z:LO
    asl a
    asl a
    asl a
    asl a
    asl a
    sta z:L+2
    lda z:HI
    asl a
    asl a
    asl a
    asl a
    asl a
    sta z:L+4
    lda z:LO
    xba
    lsr a
    lsr a
    lsr a
    and #$001f
    ora z:L+4
    sta z:L+4
    lda z:HI
    xba
    lsr a
    lsr a
    lsr a
    and #$000f
    sta z:L+6
    lda z:EX
    asl a
    asl a
    asl a
    asl a
    ora z:L+6
    ora z:SG
    sta z:L+6
    rts
