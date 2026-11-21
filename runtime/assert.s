.setcpu "65816"
.a16
.i16
.export ___zicc_assert_fail
.export __assert_expression, __assert_file, __assert_line
.import _abort

.segment "BSS"
__assert_expression: .res 4
__assert_file:       .res 4
__assert_line:       .res 4

.segment "CODE"
___zicc_assert_fail:
    ; The debugger can read the diagnostic after the foreground halts
    lda 3,s
    sta a:.loword(__assert_expression)
    lda 5,s
    sta a:.loword(__assert_expression+2)
    lda 7,s
    sta a:.loword(__assert_file)
    lda 9,s
    sta a:.loword(__assert_file+2)
    lda 11,s
    sta a:.loword(__assert_line)
    lda 13,s
    sta a:.loword(__assert_line+2)
    jml _abort
