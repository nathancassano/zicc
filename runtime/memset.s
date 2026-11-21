; Near destination in X, fill word in A, count at 3,S. Return destination
.setcpu "65816"
.a16
.i16
.export _memset
.segment "CODE"
_memset:
    phy
    phx
    pha
    lda 9,s
    beq @empty                  ; MVN with A=$FFFF would copy 65536 bytes
    tay
    pla
    sep #$20
.a8
    sta a:$0000,x               ; Seed the overlapping forward copy
    rep #$20
.a16
    dey
    beq @done
    tya
    dec a                       ; Remaining count minus one
    txy
    iny
    phb
    mvn #$7E, #$7E
    plb
@done:
    pla
    ply
    rts
@empty:
    pla
    bra @done
