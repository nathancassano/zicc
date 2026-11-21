.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.ifndef STRING_FORMAT
.export console_init, console_map, console_cursor, console_error
.export _printf, _fflush, _console_putc, ___stdout
.export console_flush_dma, console_flush_done
.export __console_init := console_init
.import __nmi_entry                  ; Pull a valid wrapper unless user-defined
.import __nmi_library_bank          ; One bank switch shared by linked services
.assert __nmi_library_bank <> 0, lderror, "console requires the library NMI bank scope"
.assert __nmi_entry <> 0, lderror, "console requires an NMI entry"

.segment "BSS"
___stdout:     .res 2
.segment "RUNTIME_CONSOLE"
.align 2
console_cursor: .res 2          ; Byte offset of the next cell, 64x28 visible area
console_origin: .res 2          ; Physical top row, in tilemap bytes (modulo $1000)
console_display_origin: .res 2  ; Top row last presented to the PPU
console_busy: .res 2            ; Foreground update nesting; NMI skips while nonzero
console_pending: .res 2
console_dirty_rows: .res 64     ; One word per physical row
console_deadline: .res 2        ; Last allowed starting scanline, exclusive
console_layer: .res 2
console_run_size: .res 2
console_scan: .res 2            ; NMI-private dirty-run iterator
console_run_start: .res 2
console_present_line: .res 2
console_work_row: .res 2        ; Foreground-private scrolling state
console_row_changed: .res 2
console_error:  .res 2          ; 1 = unsupported format, 2 = invalid stream
.export __runtime_runtime_console_size := * - console_cursor
.segment "CONSOLE_MAP"
.align 2
console_map: .res $1000 ; BG1 even columns, then BG2 odd columns
.export __runtime_console_map_size := * - console_map

.segment "RODATA"
CONSOLE_FIRST_GLYPH = '!'
CONSOLE_LAST_GLYPH = '~'
console_font:
    .incbin "assets/console/ascii8x8.1bpp"
console_font_end:
.assert console_font_end - console_font = (CONSOLE_LAST_GLYPH - CONSOLE_FIRST_GLYPH + 1) * 8, error, "wrong console font size"
console_font_zero:
    .byte 0
console_palette:
    .incbin "assets/console/palette.bgr555"

.segment "CODE"
console_init:
    phy
    phb
    pea $7F7F
    plb
    plb
    lda #228
    sta a:.loword(console_deadline)
    sep #$20
.a8
    lda f:$00213F
    and #$10
    beq :+
    rep #$20
.a16
    lda #278
    sta a:.loword(console_deadline)
:
    sep #$20
    .a8
    lda #$05
    sta f:$002105                 ; Mode 5, 16x8 tile pairs
    lda #0
    sta f:$002106
    lda #$30
    sta f:$002107                 ; BG1 map at word $3000
    lda #$34
    sta f:$002108                 ; BG2 map at word $3400
    lda #$10
    sta f:$00210B                 ; BG1 font $0000, BG2 font $1000
    lda #0
    sta f:$00210D
    sta f:$00210D
    lda #$FC
    sta f:$00210F
    lda #$FF
    sta f:$00210F                 ; BG2 shifted right by one 8-pixel glyph
    lda #$FF
    sta f:$00210E
    sta f:$00210E
    sta f:$002110
    sta f:$002110                 ; Both vertical scrolls = -1
    lda #0
    sta f:$002123
    sta f:$002124
    sta f:$002125                 ; Disable window selections
    lda #$03
    sta f:$00212C                 ; Both backgrounds on both hires screens
    sta f:$00212D
    lda #0
    sta f:$00212E
    sta f:$00212F
    sta f:$002130
    sta f:$002131                 ; No color math
    sta f:$002133                 ; 224 lines, no interlace
    sta f:$002121
    ldx #$0000
@palette:
    lda f:console_palette,x
    sta f:$002122
    inx
    cpx #$0008
    bcc @palette
    lda #$80
    sta f:$002115                 ; Increment VRAM address after high-byte write
    rep #$20
    .a16
    lda #$0000
    sta f:$002116
    lda #$1809                 ; Fixed zero source, alternating $2118/$2119
    sta f:$004300
    lda #.loword(console_font_zero)
    sta f:$004302
    lda #$3000
    sta f:$004305
    sep #$20
    .a8
    lda #.bankbyte(console_font_zero)
    sta f:$004304
    lda #$01
    sta f:$00420B                 ; Clear both font regions while forced blank
    rep #$20
    .a16
    ldy #CONSOLE_FIRST_GLYPH*32    ; BG1 pairs are 32 words each
    lda #32
    jsr .loword(console_upload_glyphs)
    ldy #$1000+CONSOLE_FIRST_GLYPH*16 ; BG2 pairs are 16 words each
    lda #16
    jsr .loword(console_upload_glyphs)
    jsr .loword(console_upload_map)
    jsr .loword(console_wait_vblank)
    sep #$20
    .a8
    lda #$0F
    sta f:$002100
    lda f:$004210                    ; Clear stale VBlank before enabling NMI
    lda #$80
    sta f:$004200                    ; Console owns initial NMI-only enablement
    rep #$20
    .a16
    plb
    ply
    rts

; Y is the first glyph's VRAM word address, A is the stride between glyphs
console_upload_glyphs:
    pha
    ldx #0
@glyph:
    tya
    sta f:$002116
    sep #$20
    .a8
@row:
    lda f:console_font,x
    sta f:$002118               ; Duplicate the mask into planes 0 and 1
    sta f:$002119               ; A set pixel selects palette color 3
    inx
    txa
    and #7
    bne @row
    rep #$20
    .a16
    tya
    clc
    adc 1,s                     ; Skip any upper planes and the blank tile
    tay
    cpx #console_font_end-console_font
    bcc @glyph
    pla
    rts

; Enter/return A16. Wait for a fresh VBlank, not the tail of an existing one
console_wait_vblank:
    sep #$20
    .a8
@outside:
    lda f:$004212
    bmi @outside
@inside:
    lda f:$004212
    bpl @inside
    rep #$20
    .a16
    rts

; Safe only during forced blank or with a full transfer's VBlank budget
console_upload_map:
    sep #$20
    .a8
    lda #$80
    sta f:$002115
    rep #$20
    .a16
    lda #$3000
    sta f:$002116
    lda #$1801
    sta f:$004300
    lda #.loword(console_map)
    sta f:$004302
    lda #$1000
    sta f:$004305
    sep #$20
    .a8
    lda #.bankbyte(console_map)
    sta f:$004304
    lda #$01
    sta f:$00420B
    rep #$20
    .a16
    rts

_fflush:
    phb
    pea $7F7F
    plb
    plb
    cpx #$0000                 ; NULL flushes the sole output stream too
    beq @flush
    cpx #.loword(___stdout)
    beq @flush
    lda #$0002
    sta a:.loword(console_error)
    lda #$FFFF
    plb
    rts
@flush:
    lda a:.loword(console_pending)
    bne @flush                 ; The library NMI owns presentation
console_flush_done:
    lda #$0000
    plb
    rts

; The wrapper already preserves registers/DBR. Never use compiler DP scratch
.segment "NMI_LIBRARY"
    jsr .loword(console_present)
.segment "CODE"
console_present:
    lda a:.loword(console_busy)
    beq :+
    rts
:
    lda a:.loword(console_pending)
    bne :+
    rts
:
    sep #$20
.a8
    lda f:$004212
    bmi :+
    rep #$20
.a16
    rts
:
    ; A user handler may consume most of VBlank. Latch V and leave at least
    ; 34 scanlines (NTSC/PAL) for scanning, DMA setup and at most 4 KiB of DMA
    lda f:$00213F             ; Reset counter read latches
    lda f:$002137
    lda f:$00213D
    rep #$20
.a16
    and #$00FF
    sta a:.loword(console_present_line)
    sep #$20
.a8
    lda f:$00213D
    rep #$20
.a16
    and #1
    xba
    ora a:.loword(console_present_line)
    cmp #225
    bcc console_present_defer
    cmp a:.loword(console_deadline)
    bcc console_present_ready
console_present_defer:
    rts
console_present_ready:
    sep #$20
.a8
    lda #$80
    sta f:$002115
    lda #.bankbyte(console_map)
    sta f:$004304
    rep #$20
.a16
    lda #$1801
    sta f:$004300
    stz a:.loword(console_scan)
console_present_scan:
    ldx a:.loword(console_scan)
    cpx #64
    beq console_present_scroll
    lda a:.loword(console_dirty_rows),x
    bne console_present_start_run
    inx
    inx
    txa
    sta a:.loword(console_scan)
    bra console_present_scan
console_present_start_run:
    txa
    sta a:.loword(console_run_start)
console_present_run:
    stz a:.loword(console_dirty_rows),x
    inx
    inx
    cpx #64
    beq console_present_upload
    lda a:.loword(console_dirty_rows),x
    bne console_present_run
console_present_upload:
    txa
    sta a:.loword(console_scan)
    sec
    sbc a:.loword(console_run_start)
    asl a
    asl a
    asl a
    asl a
    asl a                    ; Two-byte flags -> 64-byte tilemap rows
    sta a:.loword(console_run_size)
    stz a:.loword(console_layer)
console_present_layer:
    lda a:.loword(console_run_size)
    sta f:$004305
    lda a:.loword(console_run_start)
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc a:.loword(console_layer)
    pha
    clc
    adc #.loword(console_map)
    sta f:$004302
    pla
    lsr a
    clc
    adc #$3000
    sta f:$002116
console_flush_dma = *
    sep #$20
.a8
    lda #$01
    sta f:$00420B
    rep #$20
.a16
    lda a:.loword(console_layer)
    bne :+
    lda #$0800
    sta a:.loword(console_layer)
    bra console_present_layer
:
    jmp .loword(console_present_scan)
console_present_scroll:
    lda a:.loword(console_origin)
    cmp a:.loword(console_display_origin)
    beq console_present_finish
    sta a:.loword(console_display_origin)
    lsr a
    lsr a
    lsr a
    lsr a                    ; Logical row bytes / 16 = pixels
    dec a                    ; Existing -1-pixel display alignment
    sep #$20
.a8
    sta f:$00210E
    xba
    sta f:$00210E
    xba
    sta f:$002110
    xba
    sta f:$002110
    rep #$20
.a16
console_present_finish:
    stz a:.loword(console_pending)
console_present_done:
    rts

.endif ; console-only display and stream support

; Variadic arguments remain on the caller's bank-zero stack. The formatter's
; cursors, counters and digit buffer are invocation-local. E0-E3 are transient
; caller-clobbered ABI scratch, also covered by interrupt scratch preservation
; Cache the far format cursor privately, saving it across nested printf calls
.segment "ZEROPAGE": zeropage
console_format_pointer: .res 4
.segment "CODE"
.ifdef STRING_FORMAT
.export _sprintf, _snprintf
.ifndef LIBC_RETURN_EXTRA
LIBC_RETURN_EXTRA=0
.endif
_sprintf:
    lda #$FFFF
_snprintf:
    phy
    pei (__dp_scratch)
    pei (__dp_scratch+2)
    ldy z:console_format_pointer+2
    phy
    ldy z:console_format_pointer
    phy
    phx
    pha
    tsc
    sec
    sbc #72
    tcs
    tay
    lda a:75,y
    sta a:65,y                ; Current destination
    lda a:73,y
    sta a:67,y                ; Remaining capacity, including terminator
    lda #0
    sta a:69,y                ; Output count overflow
    lda a:89+LIBC_RETURN_EXTRA,y
    sta z:console_format_pointer
    lda a:91+LIBC_RETURN_EXTRA,y
    and #$FF
    sta z:console_format_pointer+2
    tya
    clc
    adc #93+LIBC_RETURN_EXTRA
.else
_printf:
    phy
    lda z:console_format_pointer+2
    pha
    lda z:console_format_pointer
    pha
    tsc
    sec
    sbc #64
    tcs
    tay
    lda a:73,y
    sta z:console_format_pointer
    lda a:75,y
    and #$00FF
    sta z:console_format_pointer+2
    tya
    clc
    adc #77
.endif
    sta a:3,y
    lda #0
    sta a:1,y
@next:
    jsr .loword(format_next)
    bne :+
    jmp .loword(@done)
:
    cmp #'%'
    beq @conversion
    jsr .loword(format_emit)
    bra @next
@conversion:
    lda #0
    sta a:9,y                 ; Width
    sta a:13,y                ; Flags: left=1, zero=2, long=4, negative=8
    lda #$FFFF
    sta a:11,y                ; Unspecified precision
@flags:
    jsr .loword(format_next)
    cmp #'-'
    bne :+
    lda a:13,y
    ora #1
    sta a:13,y
    bra @flags
:
    cmp #'0'
    bne @width
    lda a:13,y
    ora #2
    sta a:13,y
    bra @flags
@width:
    cmp #'0'
    bcc @precision
    cmp #'9'+1
    bcs @precision
    sec
    sbc #'0'
    sta a:35,y
    lda a:9,y
    cmp #100
    bcc :+
    jmp .loword(@unsupported)
:
    asl a
    sta a:37,y
    asl a
    asl a
    clc
    adc a:37,y
    adc a:35,y
    sta a:9,y
    jsr .loword(format_next)
    bra @width
@precision:
    cmp #'.'
    bne @length
    lda #0
    sta a:11,y
@precision_digit:
    jsr .loword(format_next)
    cmp #'0'
    bcc @length
    cmp #'9'+1
    bcs @length
    sec
    sbc #'0'
    sta a:35,y
    lda a:11,y
    cmp #100
    bcc :+
    jmp .loword(@unsupported)
:
    asl a
    sta a:37,y
    asl a
    asl a
    clc
    adc a:37,y
    adc a:35,y
    sta a:11,y
    bra @precision_digit
@length:
    cmp #'j'
    beq @intmax_length
    cmp #'l'
    bne @spec
    lda a:13,y
    ora #4
    sta a:13,y
    jsr .loword(format_next)
    cmp #'l'
    bne @spec
@intmax_length:
    lda a:13,y
    ora #$24                  ; long and long long/intmax
    sta a:13,y
    jsr .loword(format_next)
@spec:
    sta a:15,y
    lda #0
    sta a:17,y                ; Text length
    lda #$7E
    sta a:23,y
    tya
    clc
    adc #41
    sta a:21,y                ; Local digit buffer
    lda a:15,y
    cmp #'%'
    beq @character
    cmp #'c'
    bne :+
    jsr .loword(format_word)
@character:
    sep #$20
.a8
    sta a:41,y
    rep #$20
.a16
    lda #1
    sta a:17,y
    jmp .loword(@noninteger)
:
    cmp #'s'
    beq @string
    cmp #'S'
    beq @string
    cmp #'d'
    jeq @integer
    cmp #'i'
    jeq @integer
    cmp #'u'
    jeq @integer
    cmp #'x'
    jeq @integer
    cmp #'X'
    jeq @integer
.ifdef CALC
    cmp #'f'
    bne :+
    jmp .loword(@float)
:
    cmp #'F'
    bne :+
    jmp .loword(@float)
:
    cmp #'e'
    bne :+
    jmp .loword(@float)
:
    cmp #'E'
    bne :+
    jmp .loword(@float)
:
    cmp #'g'
    bne :+
    jmp .loword(@float)
:
    cmp #'G'
    bne :+
    jmp .loword(@float)
:
.endif
    jmp .loword(@unsupported)
@string:
    jsr .loword(format_word)
    sta a:21,y
    lda a:15,y
    cmp #'S'
    bne @string_length
    jsr .loword(format_word)
    and #$00FF
    sta a:23,y
@string_length:
    lda a:11,y
    bmi :+
    cmp a:17,y
    beq @noninteger
:
    lda a:17,y
    jsr .loword(format_text_byte)
    beq @noninteger
    lda a:17,y
    inc a
    sta a:17,y
    bra @string_length
@noninteger:
    lda #$FFFF
    sta a:11,y                ; Precision for strings was already applied
    jmp .loword(@padding)
@integer:
    lda a:13,y
    and #$20
    beq :+
    jmp .loword(@integer64)
:
    jsr .loword(format_word)
    sta a:25,y
    lda #0
    sta a:27,y
    lda a:13,y
    and #4
    beq @integer_base
    jsr .loword(format_word)
    sta a:27,y
@integer_base:
    lda a:15,y
    cmp #'x'
    jeq @hex
    cmp #'X'
    jeq @hex
    lda a:13,y
    and #4
    bne @sign
    lda a:15,y
    cmp #'u'
    beq @digits
    lda a:25,y
    bpl @digits
    lda #$FFFF
    sta a:27,y
@sign:
    lda a:15,y
    cmp #'u'
    beq @digits
    lda a:27,y
    bpl @digits
    lda a:13,y
    ora #8
    sta a:13,y
    lda #0
    sec
    sbc a:25,y
    sta a:25,y
    lda #0
    sbc a:27,y
    sta a:27,y
@digits:
    lda #0
    sta a:31,y
@digit:
    ldx a:31,y
    lda #0
    sta a:29,y
@subtract:
    lda a:27,y
    cmp f:format_powers+2,x
    bcc @digit_done
    bne @subtract_power
    lda a:25,y
    cmp f:format_powers,x
    bcc @digit_done
@subtract_power:
    lda a:25,y
    sec
    sbc f:format_powers,x
    sta a:25,y
    lda a:27,y
    sbc f:format_powers+2,x
    sta a:27,y
    lda a:29,y
    inc a
    sta a:29,y
    bra @subtract
@digit_done:
    lda a:29,y
    bne @append
    lda a:17,y
    bne @append
    cpx #36
    bne @advance_power
    lda a:11,y
    beq @advance_power
@append:
    lda a:17,y
    clc
    adc #41
    sta z:__dp_scratch
    tya
    clc
    adc z:__dp_scratch
    tax
    lda a:29,y
    clc
    adc #'0'
    sep #$20
.a8
    sta a:$0000,x
    rep #$20
.a16
    lda a:17,y
    inc a
    sta a:17,y
@advance_power:
    lda a:31,y
    clc
    adc #4
    sta a:31,y
    cmp #40
    beq :+
    jmp .loword(@digit)
:
@padding:
    lda #0
    sta a:33,y                ; Leading precision zeroes
    lda a:11,y
    bmi :+
    sec
    sbc a:17,y
    bmi :+
    sta a:33,y
:
    lda a:9,y
    sec
    sbc a:17,y
    sec
    sbc a:33,y
    sta a:19,y
    lda a:13,y
    and #8
    beq :+
    lda a:19,y
    dec a
    sta a:19,y
:
    lda a:19,y
    bpl :+
    lda #0
    sta a:19,y
:
    lda a:13,y
    and #1
    bne @sign_out
    lda a:11,y
    bpl @spaces
    lda a:13,y
    and #2
    bne @sign_out
@spaces:
    lda a:19,y
    beq @sign_out
    dec a
    sta a:19,y
    lda #' '
    jsr .loword(format_emit)
    bra @spaces
@sign_out:
    lda a:13,y
    and #8
    beq @zero_pad
    lda #'-'
    jsr .loword(format_emit)
@zero_pad:
    lda a:13,y
    and #1
    bne @precision_zero
    lda a:19,y
    beq @precision_zero
    dec a
    sta a:19,y
    lda #'0'
    jsr .loword(format_emit)
    bra @zero_pad
@precision_zero:
    lda a:33,y
    beq @text_start
    dec a
    sta a:33,y
    lda #'0'
    jsr .loword(format_emit)
    bra @precision_zero
@text_start:
    lda #0
    sta a:35,y
@text:
    lda a:35,y
    cmp a:17,y
    beq @trailing
    jsr .loword(format_text_byte)
    jsr .loword(format_emit)
    lda a:35,y
    inc a
    sta a:35,y
    bra @text
@trailing:
    lda a:19,y
    beq @continue
    dec a
    sta a:19,y
    lda #' '
    jsr .loword(format_emit)
    bra @trailing
@continue:
.ifdef CALC
    lda a:13,y
    and #$10
    beq :+
    tsc
    clc
    adc #352
    tcs
:
.endif
    jmp .loword(@next)
; Write hexadecimal digits from right to left into the local digit buffer
@hex:
    tya
    clc
    adc #65
    sta a:21,y
    lda a:25,y
    ora a:27,y
    bne @hex_digit
    lda a:11,y
    jeq @padding              ; A zero value with zero precision emits no digits
@hex_digit:
    lda a:21,y
    dec a
    sta a:21,y
    tax
    lda a:25,y
    and #$000F
    cmp #10
    bcc @hex_numeric
    clc
    adc #'A'-10
    sta a:29,y
    lda a:15,y
    and #$20                  ; ASCII case bit from x/X
    ora a:29,y
    bra @hex_store
@hex_numeric:
    clc
    adc #'0'
@hex_store:
    sep #$20
.a8
    sta a:$0000,x
    rep #$20
.a16
    lda a:17,y
    inc a
    sta a:17,y
    ldx #4
@hex_shift:
    lda a:27,y
    lsr a
    sta a:27,y
    lda a:25,y
    ror a
    sta a:25,y
    dex
    bne @hex_shift
    ora a:27,y
    bne @hex_digit
    jmp .loword(@padding)
@integer64:
    lda #.loword(__format_int64_hook)
    ora #.bankbyte(__format_int64_hook)
    bne :+
    jmp .loword(@unsupported)
:
    jsr .loword(format_word)
    sta z:__dp_scratch
    jsr .loword(format_word)
    sta z:__dp_scratch+2
    jsr .loword(format_word)
    sta z:__dp_scratch+4
    jsr .loword(format_word)
    sta z:__dp_scratch+6
    lda a:15,y
    cmp #'d'
    beq @integer64_signed
    cmp #'i'
    bne @integer64_magnitude
@integer64_signed:
    lda z:__dp_scratch+6
    bpl @integer64_magnitude
    lda a:13,y
    ora #8
    sta a:13,y
    sec
    lda #0
    sbc z:__dp_scratch
    sta z:__dp_scratch
    lda #0
    sbc z:__dp_scratch+2
    sta z:__dp_scratch+2
    lda #0
    sbc z:__dp_scratch+4
    sta z:__dp_scratch+4
    lda #0
    sbc z:__dp_scratch+6
    sta z:__dp_scratch+6
@integer64_magnitude:
    lda a:11,y
    bne @integer64_format
    lda z:__dp_scratch
    ora z:__dp_scratch+2
    ora z:__dp_scratch+4
    ora z:__dp_scratch+6
    bne @integer64_format
    jmp .loword(@padding)
@integer64_format:
    lda #0
    sta z:__dp_scratch+26
    ldx #10
    lda a:15,y
    cmp #'x'
    bne :+
    lda #$20
    sta z:__dp_scratch+26
    ldx #16
    bra @integer64_call
:
    cmp #'X'
    bne @integer64_call
    ldx #16
@integer64_call:
    tya
    clc
    adc #65                  ; one past the private 24-byte digit buffer
    jsr .loword(__format_int64_hook)
    sta a:21,y
    txa
    sta a:17,y
    jmp .loword(@padding)
.import __format_int64_hook
.ifdef CALC
.ifdef ZICC_BINARY64
@float:
    lda #.loword(__format_float_hook)
    ora #.bankbyte(__format_float_hook)
    bne :+
    jmp .loword(@unsupported)
:
    lda a:11,y
    bpl :+
    lda #6
:
    cmp #33
    bcc :+
    jmp .loword(@unsupported)
:
    sta z:__dp_scratch+26
    jsr .loword(format_word)
    sta z:__dp_scratch
    jsr .loword(format_word)
    sta z:__dp_scratch+2
    jsr .loword(format_word)
    sta z:__dp_scratch+4
    jsr .loword(format_word)
    sta z:__dp_scratch+6
    lda a:15,y
    sta z:__dp_scratch+24
    tsc
    sec
    sbc #352
    tcs
    inc a                     ; near buffer on the caller's stack
    sta z:__dp_scratch+28
    sta a:21,y
    lda a:13,y
    ora #$10                  ; release the buffer after emission
    sta a:13,y
    jsr .loword(__format_float_hook)
    lda #$7e
    sta a:23,y
    lda #0
    jsr .loword(format_text_byte)
    cmp #'-'
    bne :+
    lda a:13,y
    ora #8
    sta a:13,y
    lda a:21,y
    inc a
    sta a:21,y
:
    lda #$FFFF
    sta a:11,y
    jmp .loword(@string_length)
.import __format_float_hook
.else
@float:
    lda a:11,y
    bpl :+
    lda #6
:
    cmp #33
    bcc :+
    jmp .loword(@unsupported)
:
    pha                      ; Parameter 2: precision
    jsr .loword(format_word)
    sta a:25,y
    jsr .loword(format_word)
    pha                      ; Parameter 0: high word then low word
    lda a:25,y
    pha
    lda a:15,y               ; Parameter 1: specifier in A
    jsr .loword(_dec_format_spec)
    sta a:21,y
    txa
    sta a:23,y               ; Far result bank; cleanup must preserve X's result
    plx
    plx
    plx
    lda #0
    jsr .loword(format_text_byte)
    cmp #'-'
    bne :+
    lda a:13,y
    ora #8
    sta a:13,y
    lda a:21,y
    inc a
    sta a:21,y
:
    lda #$FFFF
    sta a:11,y
    jmp .loword(@string_length)
.import _dec_format_spec
.endif
.endif
@unsupported:
.ifndef STRING_FORMAT
    lda #1
    sta f:console_error
.endif
    lda #'?'
    jsr .loword(format_emit)
    lda #$FFFF
    bra @return
@done:
.ifdef STRING_FORMAT
    lda a:69,y
    beq :+
    lda #$FFFF
    bra @return
:
.endif
    lda a:1,y
@return:
.ifdef STRING_FORMAT
    pha
    lda a:67,y
    beq :+
    ldx a:65,y
    lda #0
    sep #$20
.a8
    sta a:$0000,x
    rep #$20
.a16
:
    pla
.endif
    tax
    tya
    clc
.ifdef STRING_FORMAT
    adc #72
.else
    adc #64
.endif
    tcs
    txa
.ifdef STRING_FORMAT
    plx                       ; Capacity and destination
    plx
.endif
    plx
    stx z:console_format_pointer
    plx
    stx z:console_format_pointer+2
.ifdef STRING_FORMAT
    plx
    stx z:__dp_scratch+2
    plx
    stx z:__dp_scratch
.endif
    ply
    rts

; Helpers preserve the formatter's frame pointer Y. All far cursors carry
; across bank boundaries; padded address bits are never used as bank bits
format_next:
    sep #$20
.a8
    lda [console_format_pointer]
    rep #$20
.a16
    pha
    inc z:console_format_pointer
    bne :+
    sep #$20
.a8
    inc z:console_format_pointer+2
    rep #$20
.a16
:
    pla
    and #$00FF
    rts
format_text_byte:
    clc
    adc a:21,y
    sta z:__dp_scratch
    lda a:23,y
    adc #0
    and #$00FF
    sta z:__dp_scratch+2
format_read_byte:
    sep #$20
.a8
    lda [__dp_scratch]
    rep #$20
.a16
    and #$00FF
    rts
format_word:
    ldx a:3,y
    lda a:$0000,x
    pha
    inx
    inx
    txa
    sta a:3,y
    pla
    rts
format_emit:
.ifdef STRING_FORMAT
    pha
    lda a:67,y
    cmp #2
    bcc @discard
    ldx a:65,y
    pla
    sep #$20
.a8
    sta a:$0000,x
    rep #$20
.a16
    lda a:65,y
    inc a
    sta a:65,y
    lda a:67,y
    dec a
    sta a:67,y
    bra @count
@discard:
    pla
@count:
    lda a:1,y
    cmp #32767
    bcc :+
    lda #1
    sta a:69,y
    rts
:
.else
    tax
    jsr .loword(_console_putc)
    lda a:1,y
.endif
    inc a
    sta a:1,y
    rts
.segment "RODATA"
format_powers:
    .dword 1000000000,100000000,10000000,1000000,100000,10000,1000,100,10,1
.segment "CODE"

; X = character. Updates WRAM only; never touches VRAM or display registers
.ifndef STRING_FORMAT
_console_putc:
    phb
    pea $7F7F
    plb
    plb
    inc a:.loword(console_busy)
    txa
    cmp #$000A
    beq @newline
    cmp #$000D
    beq @carriage
    cmp #$0020
    bcc @replacement
    cmp #$007F
    bcc @character
@replacement:
    lda #$003F
@character:
    asl a                    ; Glyph/transparent tile pair
    pha
    lda a:.loword(console_cursor)
    clc
    adc a:.loword(console_origin)
    and #$0FFF
    lsr a
    tax
    and #1
    beq :+
    txa
    and #$FFFE
    ora #$0800
    tax
:
    pla
    cmp a:.loword(console_map),x
    beq @advance
    sta a:.loword(console_map),x
    txa
    jsr .loword(console_mark_row)
@advance:
    lda a:.loword(console_cursor)
    clc
    adc #2
    sta a:.loword(console_cursor)
    cmp #$0E00
    bcc @done
    bra @scroll
@carriage:
    lda a:.loword(console_cursor)
    and #$FF80
    sta a:.loword(console_cursor)
    bra @done
@newline:
    lda a:.loword(console_cursor)
    and #$FF80
    clc
    adc #$0080
    sta a:.loword(console_cursor)
    cmp #$0E00
    bcc @done
@scroll:
    lda a:.loword(console_origin)
    clc
    adc #$0080
    and #$0FFF
    sta a:.loword(console_origin)
    clc
    adc #$0D80
    and #$0FFF
    lsr a
    sta a:.loword(console_work_row)
    tax
    stz a:.loword(console_row_changed)
    phy
    ldy #32
@clear:
    lda a:.loword(console_map),x
    ora a:.loword(console_map+$0800),x
    beq @clear_next
    stz a:.loword(console_map),x
    stz a:.loword(console_map+$0800),x
    lda #1
    sta a:.loword(console_row_changed)
@clear_next:
    inx
    inx
    dey
    bne @clear
    ply
    lda a:.loword(console_row_changed)
    beq @scrolled
    lda a:.loword(console_work_row)
    jsr .loword(console_mark_row)
@scrolled:
    lda #1
    sta a:.loword(console_pending)
    lda #$0D80
    sta a:.loword(console_cursor)
@done:
    dec a:.loword(console_busy)
    plb
    rts

; A = physical byte offset. Mark only the changed row; foreground owns busy
console_mark_row:
    lsr a
    lsr a
    lsr a
    lsr a
    lsr a
    and #$003E
    tax
    lda #1
    sta a:.loword(console_dirty_rows),x
    sta a:.loword(console_pending)
    rts
.endif ; console-only output
