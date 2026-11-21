; Zero-initialized state selects nearest-even and clears sticky exceptions
; Clients that only update flags or read the mode can link this unit alone
.setcpu "65816"
.a16
.i16

.export __fp_round_mode, __fp_exceptions, __fp_raise

.segment "BSS"
__fp_round_mode: .res 2
__fp_exceptions: .res 2

.segment "CODE"
; A holds the exception mask to accumulate. A and flags are clobbered
__fp_raise:
    tsb a:.loword(__fp_exceptions)
    rts
