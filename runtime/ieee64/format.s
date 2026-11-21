; Binary64 fixed/scientific/general decimal formatting, demand-linked
; Input: binary64 bits in __arith_lhs+0..7; ASCII f/e/g (either case) at
; +24; precision 0..32 at +26; near output buffer at +28. The caller must
; provide at least 352 bytes. Return signed byte count in A, or $FFFF for an
; unsupported specifier/precision. Output is zero-terminated. X/flags and
; arithmetic scratch are clobbered; Y/D/DBR are preserved. Native A16/X16,
; D=0, DBR=$7E. Uses shared decimal workspace and a private 368-byte frame
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.importzp __arith_lhs
.import __ieee64_decimal, __ieee64_rounded_signed
.import _ieee64_dec_n, _ieee64_dec_scale, _decimal__render
.export __ieee64_format
.export __format_float_hook := __ieee64_format
.export __require_float_format := __ieee64_format
.segment "CODE"
__ieee64_format:
    phy
    tsc
    sec
    sbc #368
    tcs
    tay
    lda z:__arith_lhs+28
    sta a:1,y                 ; current output pointer
    sta a:3,y                 ; original output pointer
    lda z:__arith_lhs+24
    sta a:7,y                 ; original specifier
    ora #$20
    cmp #'f'
    beq @valid
    cmp #'e'
    beq @valid
    cmp #'g'
    beq @valid
    jmp .loword(@invalid)
@valid:
    lda z:__arith_lhs+26
    cmp #33
    jcs @invalid
    sta a:9,y                 ; requested precision
    lda z:__arith_lhs+6
    and #$8000
    sta a:5,y
    bpl @positive
    ldx a:1,y
    sep #$20
.a8
    lda #'-'
    sta a:0,x
    rep #$20
.a16
    inx
    txa
    sta a:1,y
@positive:
    jsr .loword(__ieee64_decimal)
    cmp #1
    jeq @infinity
    cmp #2
    jeq @nan
    lda a:7,y
    ora #$20
    cmp #'g'
    bne @precision_ready
    lda a:9,y
    bne @precision_ready
    inc a
    sta a:9,y                 ; %g precision zero means one significant digit
@precision_ready:
    lda a:7,y
    ora #$20
    cmp #'f'
    beq @fixed_keep
    cmp #'e'
    beq @scientific_keep
    lda a:9,y
    bra @round
@fixed_keep:
    lda f:_ieee64_dec_n
    sec
    sbc f:_ieee64_dec_scale
    clc
    adc a:9,y
    bra @round
@scientific_keep:
    lda a:9,y
    inc a
@round:
    tax                       ; number of significant digits to retain
    lda a:5,y
    sta z:__dp_scratch+16
    tya
    clc
    adc #13
    pha                       ; exponent pointer
    tya
    clc
    adc #11
    pha                       ; digit-count pointer
    tya
    clc
    adc #15                   ; 352-byte local digit buffer
    jsr .loword(__ieee64_rounded_signed)
    plx
    plx
    pea $0000                 ; alternate form disabled
    lda a:9,y
    pha                       ; precision
    lda a:7,y
    pha                       ; specifier
    lda a:13,y
    pha                       ; exponent
    lda a:11,y
    pha                       ; digit count
    pea $007E
    tya
    clc
    adc #15
    pha                       ; far pointer to digits
    ldx a:1,y
    jsr .loword(_decimal__render)
    tax
    tsc
    clc
    adc #14
    tcs
    jmp .loword(@terminate)
@infinity:
    lda #0
    bra @special
@nan:
    lda #1
@special:
    sta a:11,y
    ldx a:1,y
    lda a:7,y
    cmp #'a'
    bcc @upper
    lda a:11,y
    beq @inf_lower
    lda #.loword(@nan_lower)
    bra @copy_special
@inf_lower:
    lda #.loword(@inf_lower_text)
    bra @copy_special
@upper:
    lda a:11,y
    beq @inf_upper
    lda #.loword(@nan_upper)
    bra @copy_special
@inf_upper:
    lda #.loword(@inf_upper_text)
@copy_special:
    sta z:__arith_lhs
    lda #.bankbyte(__ieee64_format)
    sta z:__arith_lhs+2
    phx
    ldy #0
    sep #$20
.a8
@copy_byte:
    lda [__arith_lhs],y
    iny
    cmp #0
    beq @copy_done
    sta a:0,x
    inx
    bra @copy_byte
@copy_done:
    sta a:0,x
    rep #$20
.a16
    pla                       ; original X, discard while retaining final X
    tsc
    tay                       ; restore private frame base
    bra @finish
@terminate:
    sep #$20
.a8
    lda #0
    sta a:0,x
    rep #$20
.a16
@finish:
    txa
    sec
    sbc a:3,y
    tax
    tya
    clc
    adc #368
    tcs
    txa
    ply
    rts
@invalid:
    tya
    clc
    adc #368
    tcs
    lda #$ffff
    ply
    rts
@inf_lower_text: .asciiz "inf"
@nan_lower: .asciiz "nan"
@inf_upper_text: .asciiz "INF"
@nan_upper: .asciiz "NAN"
