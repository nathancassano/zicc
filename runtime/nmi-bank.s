; Shared boundary after user code/frame cleanup and before all library services
; A16/X16, D=0. The wrapper already owns the interrupted DBR save
.setcpu "65816"
.export __nmi_library_bank
.segment "NMI_BANK"
__nmi_library_bank:
    pea $7F7F
    plb
    plb
