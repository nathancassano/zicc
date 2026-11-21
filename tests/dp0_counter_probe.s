; Ownership probe: callers deliberately keep a nonzero word at $00 across
; recursive borrowing callees and actual interrupts in a live counted loop
.setcpu "65816"
.a16
.i16
.export _probe, _check_live
.import _nested, _leaf, _count, _interrupt_run
.segment "BSS"
failed: .res 2
.segment "CODE"
_check_live:
    phy
    pei ($00)
    ldy #$5A5A
    jsr .loword(_leaf)
    cmp #3
    bne bad_nested
    cpy #$5A5A
    bne bad_nested
    lda z:$0000
    cmp 1,s
    beq nested_done
bad_nested:
    inc a:.loword(failed)
nested_done:
    pla
    sta z:$0000
    ply
    lda #0
    rts
_probe:
    phy
    pei ($00)
    lda #$BEEF
    sta z:$0000
    ldy #$5A5A
    ldx #2
    jsr .loword(_nested)
    cmp #27
    bne fail
    cpy #$5A5A
    bne fail
    lda z:$0000
    cmp #$BEEF
    bne fail
    lda a:.loword(failed)
    bne fail
    ldx #0
    jsr .loword(_count)
    cmp #0
    bne fail
    ldx #$8000
    jsr .loword(_count)
    cmp #0
    bne fail
    jsr .loword(_interrupt_run)
    cmp #2
    bne fail
    cpy #$5A5A
    bne fail
    lda z:$0000
    cmp #$BEEF
    bne fail
    lda #0
    bra done
fail:
    lda #1
done:
    tax
    pla
    sta z:$0000
    ply
    txa
    rts
