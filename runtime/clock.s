.setcpu "65816"
.a16
.i16
.export _clock
.import __nmi_entry
.import __nmi_library_bank
.assert __nmi_library_bank <> 0, lderror, "clock requires the library NMI bank scope"
.assert __nmi_entry <> 0, lderror, "clock requires an NMI entry"
.segment "RUNTIME_CLOCK"
.align 2
clock_frames: .res 4
.export __runtime_runtime_clock_size := * - clock_frames

.segment "NMI_LIBRARY"
    inc a:.loword(clock_frames)
    bne :+
    inc a:.loword(clock_frames+2)
:

.segment "CODE"
_clock:
    phb
    pea $7F7F
    plb
    plb
clock_snapshot:
    ldx a:.loword(clock_frames+2)
clock_snapshot_low:
    lda a:.loword(clock_frames)
clock_snapshot_verify:
    cpx a:.loword(clock_frames+2)
    bne clock_snapshot
    plb
    rts                         ; Long return: A low word, X high word
