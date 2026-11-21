; Comparator arguments are near pointers in X and A. The adapter preserves
; the result in A and uses Y to restore the synthetic long return
.macro invoke_comparator
    .local resume
    phy
    phk
    pea .loword(resume-1)
    pha
    tsc
    inc a
    inc a
    tay
    pla
    jml [__arith_rhs]
resume:
    ply
.endmacro
