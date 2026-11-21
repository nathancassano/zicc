; Minimal link and ROM header fixture
.setcpu "65816"
.import __STACK_SIZE__
.assert __STACK_SIZE__ >= 256 .and __STACK_SIZE__ <= 7936, lderror, "stack size must be between 256 and 7936 bytes"
.export reset_entry, nmi_entry
.export __vector_nmi := nmi_entry
.exportzp smoke_s
.import __STACK_TOP__

.segment "ZEROPAGE": zeropage
smoke_s: .res 2
.segment "DP_SCRATCH": zeropage
.res 32
.segment "BSS"
.res 128
.segment "CONSOLE_MAP"
.res 2048
.export __runtime_console_map_size := 2048

.segment "STARTUP"
.a8
.i8
reset_entry:
    sei
    stz a:$4200
    clc
    xce
    jml fast_start

.a16
.i16
fast_start:
    rep #$30
    cld
    lda #$0000
    tcd
    ldx #.loword(__STACK_TOP__)
    txs
    sep #$20
    .a8
    lda #$7E
    pha
    plb
    lda #$01
    sta f:$00420D       ; FastROM requires MEMSEL as well as a header flag
    rep #$20
    .a16
    lda #$0000
    tax
    tay
    jmp .loword(smoke_main)

.segment "CODE"
smoke_main:
    jmp .loword(smoke_main)

; Native NMI starts in bank $00, so redirect into the compiled-code bank
nmi_entry:
    jml smoke_nmi
smoke_nmi:
    rep #$30
    pha
    phx
    phy
    phd
    pea $0000
    pld
    phb
    sep #$20
    .a8
    lda #$7E
    pha
    plb
    rep #$20
    .a16
    ; Empty handler body. Decimal mode is assumed unset throughout the program
    plb
    pld
    ply
    plx
    pla
    rti
