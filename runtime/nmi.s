.setcpu "65816"
.export nmi_entry, __nmi_entry, __vector_nmi
__nmi_entry = nmi_entry
__vector_nmi = nmi_entry
.segment "NMI_USER"
nmi_entry:
    jml nmi_wrapper
nmi_wrapper:
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phd
    pea $0000
    pld
    phb
    sep #$20
    .a8
    lda #$7E
    pha
    plb
    rep #$20
    .a16

.segment "NMI_END"
    plb
    pld
    ply
    plx
    pla
    rti
