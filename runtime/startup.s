.setcpu "65816"
.export reset_entry, reset_native, ram_cleared, main_exit
.include "runtime/startup-dma.inc"
.import _main, __console_init, __STACK_TOP__
.import __zicc_reset_offset__: far
.import __STACK_SIZE__, __NEAR_START__
.assert __STACK_SIZE__ >= 256 .and __STACK_SIZE__ <= 7936, lderror, "stack size must be between 256 and 7936 bytes"
.export startup_zero
.import __RUNTIME_RAM_BOTTOM__, __RUNTIME_RAM_TOP__
.assert __RUNTIME_RAM_BOTTOM__ >= $7F0000 .and __RUNTIME_RAM_TOP__ <= $800000, lderror, "runtime RAM exceeds bank $7F"
; Declare the segments so the linker defines their symbols even when empty
.segment "ZEROPAGE"
.segment "DP_SCRATCH": zeropage
.segment "LORAM_BSS"
.segment "LORAM_DATA"
.segment "BSS"
.segment "DATA"
.ifndef AUTO_RAM_INIT
.segment "CONSOLE_MAP"
.segment "RUNTIME_BSS"
.segment "RUNTIME_CLOCK"
.segment "RUNTIME_CONSOLE"
.endif
.segment "STARTUP"
.a8
.i8
reset_entry:
    sei
    cld
    stz a:$4200        ; Disable SNES NMI and IRQ sources
    stz a:$420B        ; Disable DMA
    stz a:$420C        ; Disable HDMA
    lda #$80
    sta f:$002100        ; Keep the screen blank until the display is ready
    clc
    xce
    ; Manual expanded-WRAM links use this offset to run their DMA shim
    ; The normal reset entry resolves the offset to zero
    jml reset_native + __zicc_reset_offset__

reset_native:
    rep #$30
    .a16
    .i16
    lda #$0000
    tcd
    sep #$20
    .a8
    lda #$01
    sta a:$420D
    rep #$20
    .a16
    ldx #.loword(__STACK_TOP__)
    txs
    stz z:$00          ; Clear the saved direct-page loop counter word

    .assert __LORAM_BSS_RUN__ >= __NEAR_START__, lderror, "__loram overlaps stack"
    .assert __LORAM_BSS_RUN__ + __LORAM_BSS_SIZE__ <= $7E2000, lderror, "__loram BSS exceeds $1FFF"
    .assert __LORAM_DATA_RUN__ >= __NEAR_START__, lderror, "__loram overlaps stack"
    .assert __LORAM_DATA_RUN__ + __LORAM_DATA_SIZE__ <= $7E2000, lderror, "__loram DATA exceeds $1FFF"
    boot_clear "ZEROPAGE"
    .import __SCRATCH_START__, __SCRATCH_SIZE__
    boot_dma startup_zero, __SCRATCH_START__, __SCRATCH_SIZE__, $08
    boot_clear "LORAM_BSS"
    boot_clear "BSS"
.ifdef AUTO_RAM_INIT
    .import __initialize_extra_ram
    jsl __initialize_extra_ram
.else
    boot_clear "CONSOLE_MAP"
    boot_clear "RUNTIME_BSS"
    boot_clear "RUNTIME_CLOCK"
    boot_clear "RUNTIME_CONSOLE"
.endif
ram_cleared:
    boot_copy "LORAM_DATA"
data_copy:
    boot_copy "DATA"
data_copied:

    sep #$20
    .a8
    lda #$7E
    pha
    plb
    rep #$20
    .a16
    ; The console supplies this optional hook when it is actually linked
    lda #.loword(__console_init)
    bne runtime_console_present
    lda #.bankbyte(__console_init) ; A valid far entry may have offset zero
    beq runtime_initialized
runtime_console_present:
    jsr .loword(__console_init)
runtime_initialized:
    lda #$0000
    tax
    tay
    jsl _main                   ; Give debugger/profiler an explicit root call
    jmp .loword(main_exit)

startup_zero:
    .byte 0

.segment "CODE"
main_exit:
    jmp .loword(main_exit)
