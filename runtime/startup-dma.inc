; DMA channel 0 to the WRAM data port, with DBR still in bank zero
; A and X are 16-bit on entry and exit. A zero count is skipped unless
; the actual span is 64 KiB, which the DMA hardware encodes as zero
.macro boot_dma source, dest, count, mode
    .local transfer, done
    .assert count <= $10000, lderror, "startup DMA span exceeds 64 KiB"
    .assert .loword(source) + count <= $10000 .or mode = $08, lderror, "startup DMA source crosses a bank"
    ldx #.loword(count)
    bne transfer
    lda #.bankbyte(count)
    beq done
transfer:
    boot_dma_registers source, dest, mode
done:
.endmacro

; The generated initializer already knows each span is nonempty
.macro boot_dma_known source, dest, count, mode
    .assert count > 0 .and count <= $10000, lderror, "invalid startup DMA count"
    .assert .loword(source) + count <= $10000 .or mode = $08, lderror, "startup DMA source crosses a bank"
    ldx #.loword(count)
    boot_dma_registers source, dest, mode
.endmacro

.macro boot_dma_registers source, dest, mode
    stx a:$4305
    lda #.loword(dest)
    sta a:$2181
    lda #.loword(source)
    sta a:$4302
    lda #$8000 | mode
    sta a:$4300
    sep #$20
    .a8
    lda #(.bankbyte(dest) & 1)
    sta a:$2183
    lda #.bankbyte(source)
    sta a:$4304
    lda #$01
    sta a:$420B
    rep #$20
    .a16
.endmacro

.macro boot_clear name
    .import .ident(.concat("__", name, "_RUN__")), .ident(.concat("__", name, "_SIZE__"))
    boot_dma startup_zero, .ident(.concat("__", name, "_RUN__")), .ident(.concat("__", name, "_SIZE__")), $08
.endmacro

.macro boot_copy name
    .import .ident(.concat("__", name, "_LOAD__"))
    .import .ident(.concat("__", name, "_RUN__")), .ident(.concat("__", name, "_SIZE__"))
    boot_dma .ident(.concat("__", name, "_LOAD__")), .ident(.concat("__", name, "_RUN__")), .ident(.concat("__", name, "_SIZE__")), $00
.endmacro
