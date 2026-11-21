; Exercise the clock and NMI ABI using real hardware NMI delivery
.setcpu "65816"
.a16
.i16
.export _clock_probe, _nmi_probe, _enable_nmi
.import _clock
.segment "BSS"
clock_result: .res 4
.segment "CODE"
; Explicit application action, separate from every time API call
_enable_nmi:
    sep #$20
    .a8
    lda f:$004210
    lda #$80
    sta f:$004200
    rep #$20
    .a16
    rts

_clock_probe:
    jsr .loword(_clock)
    sta a:.loword(clock_result)
    stx a:.loword(clock_result+2)
    lda #0
    rts

; The Lua probe redirects a snapshot instruction here once, making a real NMI
; occur between its reads. It redirects clock_pause_resume back after RTI
clock_pause:
    wai
clock_pause_resume:
    bra clock_pause_resume

; Preserve the caller, then interrupt deliberately non-ABI machine states
_nmi_probe:
    phb
    phd
    phy
    sep #$20
    .a8
    lda #$7E
    pha
    plb
    rep #$20
    .a16
    lda #$3456
    tcd
    ldy #$5A3C
    ldx #$ABCD
    lda #$1234
    sep #$09                   ; Decimal and carry must survive NMI too
clock_wait_16:
    wai
clock_after_16:
    sep #$20
    .a8
    lda #$7F
    pha
    plb
clock_wait_a8:
    wai
clock_after_a8:
    sep #$10
    .i8
clock_wait_8:
    wai
clock_after_8:
    rep #$20
    .a16
    sep #$20
.a8
    lda #$12
    pha
    plb
    rep #$20
.a16
clock_wait_x8:
    wai
clock_after_x8:
    rep #$30
    .a16
    .i16
    cld
    ply
    pld
    plb
    lda #0
    rts
