; Independent callee fixtures for the public integer-call convention
.setcpu "65816"
.a16
.i16
.export _abi_probe, _abi_first, _abi_second, _abi_third, _abi_tick
.export _abi_char, _abi_promoted
.segment "BSS"
abi_ticks: .res 2
.segment "CODE"
_abi_probe:
    cpx #17
    bne @wrong
    cmp #23
    bne @wrong
    lda 3,s                    ; Third argument above the two-byte JSR return
    cmp #42
    bne @wrong
    lda #82
    rts
@wrong:
    lda #$FFFF
    rts
_abi_first:
    ldx #$ABCD
    lda #17
    rts
_abi_second:
    ldx #$DEAD
    lda #23
    rts
_abi_third:
    ldx #$BEEF
    lda #42
    rts
_abi_tick:
    lda abi_ticks
    cmp #3
    bcs @finished
    inc abi_ticks
    lda #1
    rts
@finished:
    lda #0
    rts
_abi_char:
    lda #$AB41                 ; Only the low byte belongs to the char result
    rts
_abi_promoted:
    txa
    rts
