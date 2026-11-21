.setcpu "65816"
.a16
.i16
.importzp __arith_rhs
.export udiv16_hardware
R=__arith_rhs
.segment "CODE"
; Start one 16/8 operation. Return while the ALU finishes; the caller reads
; $4214 immediately. REP(3), two NOPs(4), RTS(6), and the caller's three
; LDA fetches cover 16 machine cycles before its first data read in FastROM
udiv16_hardware:
    sta f:$004204
    sep #$20
.a8
    lda z:R
    sta f:$004206
    rep #$20
.a16
    nop
    nop
    rts
