.setcpu "65816"
.a16
.i16
.export _loop_interrupt_enable, _loop_interrupt_disable
.segment "CODE"
_loop_interrupt_enable:
    sep #$20
.a8
    lda #100
    sta f:$004209
    lda #0
    sta f:$00420A
    lda f:$004210
    lda #$A0                    ; Explicit NMI and vertical IRQ enable
    sta f:$004200
    rep #$20
.a16
    cli
    rts
_loop_interrupt_disable:
    sei
    sep #$20
.a8
    lda f:$004210
    lda #0
    sta f:$004200
    rep #$20
.a16
    rts
