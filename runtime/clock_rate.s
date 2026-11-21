.setcpu "65816"
.a16
.i16
.export ___clock_rate
.segment "BSS"
clock_rate: .res 2
.segment "CODE"
___clock_rate:
    lda a:.loword(clock_rate)
    bne @done
    sep #$20
    .a8
    lda f:$00213F               ; STAT78 bit 4: PAL hardware
    and #$10
    rep #$20
    .a16
    beq @ntsc
    lda #50
    bra @rate
@ntsc:
    lda #60
@rate:
    sta a:.loword(clock_rate)
@done:
    rts
