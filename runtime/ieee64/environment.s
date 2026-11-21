; IEEE rounding helpers and the public floating-point environment interface
.setcpu "65816"
.a16
.i16

.import __fp_round_mode, __fp_exceptions, __fp_raise
.export __fp_round_increment, __fp_overflow, __fp_tiny
.export _fegetround, _fesetround, _fetestexcept, _feclearexcept, _feraiseexcept
.export _fegetexceptflag, _fesetexceptflag, _fegetenv, _feholdexcept
.export _fesetenv, _feupdateenv
.importzp __arith_lhs

.segment "CODE"
; A holds four low bits: retained parity, guard and two sticky bits, in
; descending order. X holds the sign bit. Carry returns the increment
; Preserve X/Y and the scratch area so stack-based helpers can use this too
__fp_round_increment:
    and #$000f
    bit #7
    beq @no
    pha
    lda f:__fp_round_mode
    beq @nearest
    cmp #1
    beq @down
    cmp #2
    beq @up
    pla
    bra @no
@down:
    pla
    cpx #$8000
    rts
@up:
    pla
    cpx #$8000
    bcc @yes
    bra @no
@nearest:
    pla
    cmp #12
    bcs @yes
    and #7
    cmp #5
    rts
@yes:
    sec
    rts
@no:
    clc
    rts

; Finite overflow. X holds the sign word. Choose infinity or maximum
; finite, then record overflow and inexact
__fp_overflow:
    lda #$0014
    jsr .loword(__fp_raise)
    lda f:__fp_round_mode
    beq @infinity
    lda #1
    jsr .loword(__fp_round_increment)
    bcs @infinity
    lda #$ffff
    sta z:__arith_lhs
    sta z:__arith_lhs+2
    sta z:__arith_lhs+4
    txa
    ora #$7fef
    sta z:__arith_lhs+6
    rts
@infinity:
    stz z:__arith_lhs
    stz z:__arith_lhs+2
    stz z:__arith_lhs+4
    txa
    ora #$7ff0
    sta z:__arith_lhs+6
    rts

; Nonzero exact magnitude strictly below half the minimum subnormal
__fp_tiny:
    lda #$0018
    jsr .loword(__fp_raise)
    lda #1
    jsr .loword(__fp_round_increment)
    lda #0
    adc #0
    sta z:__arith_lhs
    stz z:__arith_lhs+2
    stz z:__arith_lhs+4
    stx z:__arith_lhs+6
    rts

_fegetround:
    lda f:__fp_round_mode
    rts
_fesetround:
    cpx #4
    bcs invalid_mode
    txa
    sta f:__fp_round_mode
    jmp .loword(success)
invalid_mode:
    lda #1
    rts
_fetestexcept:
    txa
    and f:__fp_exceptions
    rts
_feclearexcept:
    txa
    eor #$ffff
    and f:__fp_exceptions
    sta f:__fp_exceptions
    jmp .loword(success)
_feraiseexcept:
    txa
    and #31
    jsr .loword(__fp_raise)
    jmp .loword(success)
_fegetexceptflag:
    and f:__fp_exceptions
    sta a:0,x
    jmp .loword(success)
_fesetexceptflag:
    and #31
    pha
    and a:0,x
    tax
    pla
    eor #$ffff
    and f:__fp_exceptions
    sta f:__fp_exceptions
    txa
    jsr .loword(__fp_raise)
    jmp .loword(success)
_fegetenv:
    lda f:__fp_round_mode
    xba
    ora f:__fp_exceptions
    sta a:0,x
    jmp .loword(success)
_feholdexcept:
    jsr .loword(_fegetenv)
    sta f:__fp_exceptions
    rts
_feupdateenv:
    lda f:__fp_exceptions
    pha
    jsr .loword(_fesetenv)
    pla
    jsr .loword(__fp_raise)
    jmp .loword(success)
_fesetenv:
    lda #0
    cpx #0
    beq restore_env
    lda a:0,x
restore_env:
    pha
    and #31
    sta f:__fp_exceptions
    pla
    xba
    and #3
    sta f:__fp_round_mode
success:
    lda #0
    rts
