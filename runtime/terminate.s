; Termination shares the same halt loop as a normal return from main
.setcpu "65816"
.a16
.i16
.export ___builtin_abort, _abort, _exit, _quick_exit, __Exit
.import main_exit, __STACK_TOP__
.segment "CODE"
___builtin_abort:
_abort:
    lda #0
    bra terminate
_exit:
_quick_exit:
__Exit:
    txa
terminate:
    ldx #.loword(__STACK_TOP__)
    txs
    jml main_exit
