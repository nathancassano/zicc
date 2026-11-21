; Shared definitions for binary32 elementary functions
.ifndef MATH_RETURN_EXTRA
MATH_RETURN_EXTRA = 0
.endif
FRAME = 112
V = 1
Z = 5
P = 9
T = 13
U = 17
N = 21
SIGN = 25
MODE = 27
COUNT = 29
E = 31
F = 33
C = 47
Q = 61
M = 63
.macro constant dest, bits
    lda #.loword(bits)
    sta dest,s
    lda #.hiword(bits)
    sta dest+2,s
.endmacro
.macro copy dest, src
    lda src,s
    sta dest,s
    lda src+2,s
    sta dest+2,s
.endmacro
.macro binary op, dest, left, right
    lda left,s
    sta z:__arith_lhs
    lda left+2,s
    sta z:__arith_lhs+2
    lda right,s
    sta z:__arith_rhs
    lda right+2,s
    sta z:__arith_rhs+2
.if MATH_RETURN_EXTRA
    jsl op
.else
    jsr .loword(op)
.endif
    sta dest,s
    txa
    sta dest+2,s
.endmacro
.macro enter
    tsc
    sec
    sbc #FRAME
    tcs
    lda FRAME+3+MATH_RETURN_EXTRA,s
    sta V,s
    lda FRAME+5+MATH_RETURN_EXTRA,s
    sta V+2,s
.endmacro
.macro finish src
    lda src,s
    sta z:__arith_lhs
    lda src+2,s
    tax
    tsc
    clc
    adc #FRAME
    tcs
    lda z:__arith_lhs
.if MATH_RETURN_EXTRA
    rtl
.else
    rts
.endif
.endmacro
.macro jump_eq target
    bne :+
    jmp .loword(target)
:
.endmacro
.macro jump_ne target
    beq :+
    jmp .loword(target)
:
.endmacro
.macro jump_cc target
    bcs :+
    jmp .loword(target)
:
.endmacro
.macro jump_cs target
    bcc :+
    jmp .loword(target)
:
.endmacro
; Convert the small signed integer E to binary32 N exactly, using a biased
; integer representation at exponent 23. E is bounded by [-150, 150]
.macro exponent_float
    lda E,s
    bpl :+
    eor #$ffff
    inc
:
    sta N,s
    lda #$4b00
    sta N+2,s
    constant U, $4b000000
    binary __fsub32, N, N, U
    lda E,s
    bpl :+
    lda N+2,s
    eor #$8000
    sta N+2,s
:
.endmacro
