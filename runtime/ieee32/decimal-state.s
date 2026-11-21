; Decimal conversion workspace, shared by the assembly routines
.setcpu "65816"
.export _decimal__dec_digits, _decimal__dec_n, _decimal__dec_scale
.export _decimal__dec_output
.export __runtime_runtime_bss_size := 284
.segment "RUNTIME_BSS"
_decimal__dec_digits: .res 200
.align 2
_decimal__dec_n: .res 2
.align 2
_decimal__dec_scale: .res 2
_decimal__dec_output: .res 80
.assert _decimal__dec_digits >= $7F0000 .and _decimal__dec_output + 80 <= $800000, lderror, "decimal workspace exceeds bank $7F"
