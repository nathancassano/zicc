.setcpu "65816"
.import reset_entry, __vector_nmi, __vector_irq, __vector_brk, __vector_cop
.export unused_interrupt

.ifdef HIROM
.segment "VECTOR_STUBS"
.export reset_vector, nmi_vector, irq_vector, brk_vector, cop_vector
reset_vector: jml reset_entry
nmi_vector: jml __vector_nmi
irq_vector: jml __vector_irq
brk_vector: jml __vector_brk
cop_vector: jml __vector_cop
.else
.segment "CODE"
.endif
; Vector entry is always through bank $00. This byte is also in that mirror
unused_interrupt:
    rti

.ifdef HIROM
RESET_TARGET = reset_vector
NMI_TARGET = nmi_vector
IRQ_TARGET = irq_vector
BRK_TARGET = brk_vector
COP_TARGET = cop_vector
.else
RESET_TARGET = reset_entry
NMI_TARGET = __vector_nmi
IRQ_TARGET = __vector_irq
BRK_TARGET = __vector_brk
COP_TARGET = __vector_cop
.endif
.segment "VECTORS"
; Native mode: reserved, reserved, COP, BRK, ABORT, NMI, reserved, IRQ
.addr .loword(unused_interrupt), .loword(unused_interrupt)
.addr .loword(COP_TARGET), .loword(BRK_TARGET)
.addr .loword(unused_interrupt), .loword(NMI_TARGET)
.addr .loword(unused_interrupt), .loword(IRQ_TARGET)
; Emulation: reserved, reserved, COP, reserved, ABORT, NMI, RESET, IRQ/BRK
.addr .loword(unused_interrupt), .loword(unused_interrupt)
.addr .loword(unused_interrupt), .loword(unused_interrupt)
.addr .loword(unused_interrupt), .loword(unused_interrupt)
.addr .loword(RESET_TARGET), .loword(unused_interrupt)
