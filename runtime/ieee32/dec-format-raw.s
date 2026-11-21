; Near text in X; U32 bits at 3/5,S; signed word byte count returned in A
; Default and precision-aware entries share one body and an 80-byte digit buffer
; Native A16/X16, D=0, DBR=$7E; preserve Y/D/DBR. Calls retain their normal ABI
.setcpu "65816"
.importzp __dp_scratch
.macpack longbranch
.a16
.i16
.export _decimal__dec_format_raw, _decimal__dec_format_raw_spec
.import _decimal__dec_n, _decimal__dec_scale
.import ___ieee_decimal, _decimal__rounded, _decimal__render, _decimal__dec_copy
.segment "CODE"
_decimal__dec_format_raw:
    lda #$0067
    sta z:__dp_scratch
    lda #6
    sta z:__dp_scratch+2
    bra format_raw_body
__size_decimal__dec_format_raw = * - _decimal__dec_format_raw
; Precision-aware entry: spec at 7,S and precision at 9,S
_decimal__dec_format_raw_spec:
    lda 7,s
    sta z:__dp_scratch
    lda 9,s
    sta z:__dp_scratch+2
format_raw_body:
    phy
    tsc
    sec
    sbc #96
    tcs
    tay
    txa
    sta a:1,y                 ; p
    sta a:3,y                 ; original text
    lda z:__dp_scratch
    sta a:93,y                ; specifier
    lda z:__dp_scratch+2
    sta a:95,y                ; precision; digits occupy 13..92
    lda a:101,y
    sta a:5,y                 ; mantissa low
    lda a:103,y
    bpl @positive
    sep #$20
.a8
    lda #$2D
    sta a:$0000,x
    rep #$20
.a16
    inx
    txa
    sta a:1,y
@positive:
    lda a:103,y
    and #$7FFF
    sta a:7,y                 ; absolute bits high
    cmp #$7F80
    jcs @special
    asl a
    xba
    and #$00FF                ; b
    beq @subnormal
    sec
    sbc #150
    sta a:11,y
    lda a:7,y
    and #$007F
    ora #$0080
    bra @mantissa
@subnormal:
    lda #$FF6B                ; 1 - 150
    sta a:11,y
    lda a:7,y
    and #$007F
@mantissa:
    pha
    lda a:5,y
    pha
    lda a:11,y
    jsr .loword(___ieee_decimal)
    plx
    plx
    ; The converter's zero case already establishes the same zero state
    lda a:93,y
    ora #$0020
    cmp #$0067
    bne @keep
    lda a:95,y
    bne @keep
    inc a
    sta a:95,y                ; g precision zero means one significant digit
@keep:
    lda a:93,y
    ora #$0020
    cmp #$0066
    beq @fixed_keep
    cmp #$0065
    beq @exponent_keep
    lda a:95,y
    bra @rounded_keep
@fixed_keep:
    lda f:_decimal__dec_n
    sec
    sbc f:_decimal__dec_scale
    clc
    adc a:95,y
    bra @rounded_keep
@exponent_keep:
    lda a:95,y
    inc a
@rounded_keep:
    tax
    tya
    clc
    adc #11
    pha
    tya
    clc
    adc #9
    pha
    tya
    clc
    adc #13
    jsr .loword(_decimal__rounded)
    plx
    plx
    pea $0000                 ; alt
    lda a:95,y
    pha                       ; precision
    lda a:93,y
    pha                       ; specifier
    lda a:11,y
    pha
    lda a:9,y
    pha
    pea $007E
    tya
    clc
    adc #13
    pha
    ldx a:1,y
    jsr .loword(_decimal__render)
    tax
    tsc
    clc
    adc #14
    tcs
    sep #$20
.a8
    lda #0
    sta a:$0000,x
    rep #$20
.a16
    txa
    sec
    sbc a:3,y
    bra @return
@special:
    cmp #$7F80
    bne @nan
    lda a:5,y
    bne @nan
    pea .bankbyte(inf_text)
    pea .loword(inf_text)
    bra @copy
@nan:
    pea .bankbyte(nan_text)
    pea .loword(nan_text)
@copy:
    ldx a:1,y
    jsr .loword(_decimal__dec_copy)
    plx
    plx
    lda a:1,y
    sec
    sbc a:3,y
    clc
    adc #3
@return:
    tax
    tya
    clc
    adc #96
    tcs
    txa
    ply
    rts
__size_decimal__dec_format_raw_spec = * - _decimal__dec_format_raw_spec
.segment "RODATA"
inf_text: .asciiz "inf"
nan_text: .asciiz "nan"
