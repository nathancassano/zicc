; Near destination in X, near source in A, count at 3,S
.setcpu "65816"
.a16
.i16
.export __zicc_memcpy_near
.segment "CODE"
__zicc_memcpy_near:
    phy
    phb
    phx
    txy
    tax
    lda 8,s
    beq @done
    dec a
    mvn #$7E, #$7E
@done:
    pla
    plb
    ply
    rts
