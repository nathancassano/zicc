; IEEE binary64 square root, round to nearest, ties to even. Public _sqrt
; accepts an eight-byte stack argument and returns in __arith_lhs+0..7;
; __dsqrt accepts/returns the value in that slot. Native A16/X16, D=0,
; DBR=$7E. X/Y/D/DBR preserved; A/flags and scratch +0..23 clobbered
; The restoring integer square root computes 53 result bits and an exact
; remainder. For integer N, sqrt(N) rounds upward exactly when r=N-q*q>q
.setcpu "65816"
.macpack longbranch
.import __fp_round_mode, __fp_raise
.a16
.i16
.importzp __arith_lhs
.export _sqrt, __dsqrt
L=__arith_lhs
R=__arith_lhs+8
T=__arith_lhs+16
N=1
EXP=15
FRAME=16
.segment "CODE"
_sqrt:
    phy
    lda 5,s
    sta z:L
    lda 7,s
    sta z:L+2
    lda 9,s
    sta z:L+4
    lda 11,s
    sta z:L+6
    ply
    jsr .loword(__dsqrt)
    rts
__dsqrt:
    phx
    phy
    tsc
    sec
    sbc #FRAME
    tcs
    tay
    lda z:L+6
    and #$7fff
    ora z:L+4
    ora z:L+2
    ora z:L
    jeq @done                ; preserve both signed zeros
    lda z:L+6
    and #$7ff0
    cmp #$7ff0
    bne @finite
    lda z:L+6
    and #$000f
    ora z:L+4
    ora z:L+2
    ora z:L
    beq @check_sign
    lda z:L+6
    bit #$0008
    jne @nan
    jmp .loword(@invalid)
@check_sign:
    lda z:L+6
    jmi @invalid
    jmp .loword(@done)
@finite:
    lda z:L+6
    jmi @invalid
    lda z:L+6
    and #$7ff0
    lsr a
    lsr a
    lsr a
    lsr a
    beq @subnormal
    sec
    sbc #1023
    sta a:EXP,y
    lda z:L+6
    and #$000f
    ora #$0010
    sta z:L+6
    bra @normalized
@subnormal:
    lda #$fc02               ; -1022
    sta a:EXP,y
@normalize:
    lda z:L+6
    and #$0010
    bne @normalized
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    lda a:EXP,y
    dec a
    sta a:EXP,y
    bra @normalize
@normalized:
    lda a:EXP,y
    and #1
    beq @even
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    lda a:EXP,y
    dec a
    sta a:EXP,y
@even:
    lda a:EXP,y
    cmp #$8000               ; carry is the sign bit for arithmetic ROR
    ror a
    clc
    adc #1023
    sta a:EXP,y
    ; N = significand << 58, top-aligned in 112 bits. Its first 106 bits
    ; are consumed as 53 two-bit groups; the final six bits are padding
    lda #0
    sta a:N,y
    sta a:N+2,y
    sta a:N+4,y
    .repeat 4, I
    lda z:L+I*2
    sta a:N+6+I*2,y
    .endrepeat
    .repeat 10
    lda a:N+6,y
    asl a
    sta a:N+6,y
    .repeat 3, I
    lda a:N+8+I*2,y
    rol a
    sta a:N+8+I*2,y
    .endrepeat
    .endrepeat
    .repeat 4, I
    stz z:L+I*2
    stz z:R+I*2
    .endrepeat
    ldx #53
@digit:
    .repeat 2
    lda a:N,y
    asl a
    sta a:N,y
    .repeat 6, I
    lda a:N+2+I*2,y
    rol a
    sta a:N+2+I*2,y
    .endrepeat
    rol z:R
    rol z:R+2
    rol z:R+4
    rol z:R+6
    .endrepeat
    asl z:L
    rol z:L+2
    rol z:L+4
    rol z:L+6
    ; T = 2*root+1. C starts clear because root never reaches bit 63
    lda z:L
    asl a
    ora #1
    sta z:T
    .repeat 3, I
    lda z:L+2+I*2
    rol a
    sta z:T+2+I*2
    .endrepeat
    lda z:R+6
    cmp z:T+6
    bcc @next
    bne @subtract
    lda z:R+4
    cmp z:T+4
    bcc @next
    bne @subtract
    lda z:R+2
    cmp z:T+2
    bcc @next
    bne @subtract
    lda z:R
    cmp z:T
    bcc @next
@subtract:
    sec
    .repeat 4, I
    lda z:R+I*2
    sbc z:T+I*2
    sta z:R+I*2
    .endrepeat
    inc z:L
@next:
    dex
    jne @digit
    lda z:R
    ora z:R+2
    ora z:R+4
    ora z:R+6
    jeq @pack
    lda #$0010
    jsr .loword(__fp_raise)
    lda f:__fp_round_mode
    beq :+
    cmp #2
    beq @round_up
    bra @pack
:
    ; Round upward precisely when the integer remainder exceeds the root
    lda z:R+6
    cmp z:L+6
    bcc @pack
    bne @round_up
    lda z:R+4
    cmp z:L+4
    bcc @pack
    bne @round_up
    lda z:R+2
    cmp z:L+2
    bcc @pack
    bne @round_up
    lda z:R
    cmp z:L
    bcc @pack
    beq @pack
@round_up:
    inc z:L
    bne @rounded
    inc z:L+2
    bne @rounded
    inc z:L+4
    bne @rounded
    inc z:L+6
@rounded:
    lda z:L+6
    cmp #$0020
    bcc @pack
    lsr z:L+6
    ror z:L+4
    ror z:L+2
    ror z:L
    lda a:EXP,y
    inc a
    sta a:EXP,y
@pack:
    lda a:EXP,y
    .repeat 4
    asl a
    .endrepeat
    sta z:T
    lda z:L+6
    and #$000f
    ora z:T
    sta z:L+6
    bra @done
@invalid:
    lda #1
    jsr .loword(__fp_raise)
@nan:
    stz z:L
    stz z:L+2
    stz z:L+4
    lda #$7ff8
    sta z:L+6
@done:
    tya
    clc
    adc #FRAME
    tcs
    ply
    plx
    rts
