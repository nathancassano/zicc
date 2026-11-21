; IEEE binary32 unpack and NaN classification
; Unpack and classify through one near call; NaNs discard that return below
.setcpu "65816"
.importzp __arith_lhs, __arith_rhs
.a16
.i16
ea = __arith_lhs+8
eb = __arith_lhs+10
sg = __arith_lhs+12
ma = __arith_lhs+14
mb = __arith_lhs+18
sa = __arith_lhs+30
sb = __arith_lhs+28
al = __arith_lhs
ah = __arith_lhs+2
bl = __arith_rhs
bh = __arith_rhs+2

.segment "CODE"
.export unpack_checked, ieee32_invalid
unpack_checked:
    lda z:al
    sta z:ma
    lda z:bl
    sta z:mb
    ; Classify each exponent while it is still in A. Only NaNs require
    ; testing the fraction of an operand whose exponent is all ones
    .macro unpack_operand hi, lo, exp, mant, sign, second
        .local subnormal, special, normal, done
        ; Keep the original high word in X while A extracts its exponent
        ldx z:hi
        txa
        and #$8000
        sta z:sign
        .if second
            eor z:sa
            sta z:sg
        .endif
        txa
        asl
        xba
        and #$00ff
        beq subnormal
        cmp #255
        beq special
normal:
        sta z:exp
        txa
        and #$007f
        ora #$0080
        sta z:mant+2
        .if second
            rts
        .else
            bra done
        .endif
special:
        txa
        and #$007f
        ora z:lo
        bne nan_found
        lda #255
        sta z:exp
        lda #$0080
        sta z:mant+2
        .if second
            rts
        .else
            bra done
        .endif
subnormal:
        inc a                       ; zero exponent encodes an effective one
        sta z:exp
        txa
        and #$007f
        sta z:mant+2
done:
    .endmacro
    unpack_operand ah, al, ea, ma, sa, 0
    unpack_operand bh, bl, eb, mb, sb, 1
    rts
nan_found:
    pla                         ; discard unpack_checked return address
.ifdef LIBC_RETURN_EXTRA
    tsc
    inc a                       ; discard its JSL return bank
    tcs
.endif
ieee32_invalid:
    lda #0
    ldx #$7fc0
    rts
