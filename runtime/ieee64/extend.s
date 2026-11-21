; Exact IEEE binary32 to binary64 conversion. Input is the binary32 bit
; pattern at arithmetic scratch +0..3; result occupies +0..7. NaNs retain
; sign and payload and are quieted. A/flags and scratch +8..+17 are clobbered;
; X/Y/D/DBR are preserved. Native A/X/Y 16-bit mode is required
.setcpu "65816"
.a16
.i16
.importzp __arith_lhs
.import __fp_raise
.export __fext32_64
L = __arith_lhs
LO = __arith_lhs+8
HI = __arith_lhs+10
SG = __arith_lhs+12
EX = __arith_lhs+14
NANFLAG = __arith_lhs+16
.segment "CODE"
__fext32_64:
    lda z:L
    sta z:LO
    lda z:L+2
    and #$8000
    sta z:SG
    lda z:L+2
    and #$007f
    sta z:HI
    lda z:L+2
    and #$7f80
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    stz z:NANFLAG
    beq @subnormal
    cmp #255
    beq @special
    clc
    adc #896
    sta z:EX
    bra @pack
@special:
    lda #2047
    sta z:EX
    lda z:LO
    ora z:HI
    beq @pack
    lda z:HI
    bit #$0040
    bne :+
    lda #1
    jsr .loword(__fp_raise)
:
    inc z:NANFLAG
    bra @pack
@subnormal:
    lda z:LO
    ora z:HI
    bne @normalize
    stz z:EX
    bra @pack
@normalize:
    lda #897
    sta z:EX
@shift:
    asl z:LO
    rol z:HI
    dec z:EX
    lda z:HI
    bit #$0080
    beq @shift
    and #$007f
    sta z:HI
@pack:
    ; binary64 fraction = binary32 fraction << 29
    stz z:L
    lda z:LO
    and #7
    xba
    asl a
    asl a
    asl a
    asl a
    asl a
    sta z:L+2
    lda z:HI
    and #7
    xba
    asl a
    asl a
    asl a
    asl a
    asl a
    sta z:L+4
    lda z:LO
    lsr a
    lsr a
    lsr a
    ora z:L+4
    sta z:L+4
    lda z:HI
    lsr a
    lsr a
    lsr a
    sta z:L+6
    lda z:EX
    asl a
    asl a
    asl a
    asl a
    ora z:L+6
    ora z:SG
    sta z:L+6
    lda z:NANFLAG
    beq :+
    lda z:L+6
    ora #8
    sta z:L+6
:
    rts
