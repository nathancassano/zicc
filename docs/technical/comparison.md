# Calculator comparison

Measured on the installed MesenCE 2.2.1 core. Times are **SNES master clocks** (21.477272 MHz), not CPU instruction cycles. One fixed input is evaluated, from entry to the first printf through return from the result printf. Both runs emit `result: 30`. Raw logs, ROM hashes, profiler records and CSVs are in `build/comparison/`.

zicc uses IEEE binary32, near pointers and the polling console. VBCC is the unmodified web release at `C:/snesdev/vbcc65816_r2/vbcc65816_win/vbcc`, `-O3 -msfp4`, linked with `-lms4 -lvc`; only fgets is replaced with the same fixed input. It retains the stock startup, far pointers, stdio and ROM layout. zicc executes in FastROM bank $80; the release reference executes in bank $00 at SlowROM speed. This compares the resulting systems, not isolated optimizer quality. VBCC inlines some application calls. Neither runtime is replaced with the other's implementation.

| Metric | zicc IEEE32 | VBCC r2 MSFP |
| --- | ---: | ---: |
| ROM file bytes | 32,768 | 163,840 |
| Loaded ROM bytes (no padding) | 15,293 | 14,336 |
| Font/palette asset bytes | 2,056 | 768 |
| Entire non-asset ROM bytes | 13,237 | 13,568 |
| One iteration, master clocks | 619,534 | 1,501,200 |

Non-asset ROM includes code, numeric tables, strings, input fixture, startup, header, vectors and initialization images. Unused fill and graphics assets are excluded. The file sizes above deliberately retain each toolchain's normal layout.

The following tables contain **every profiler entry called from reset through the measured iteration**, including startup and library helpers. Inclusive times overlap for nested/recursive calls and must not be summed; they can exceed the total elapsed time. Exclusive times partition the measured boot interval. Active main/reset frames include the elapsed portion so far. A helper tail-jumped to is attributed to its calling entry by Mesen.

C function sizes are exact emitted sizes. Assembly/helper sizes are disjoint entry regions ending at the next callable symbol/section boundary; shared tails are counted once in that layout rather than duplicated in every caller. Use the whole-ROM totals to see how much space each build needs. A dash denotes no ROM body for the profiler's synthetic reset frame.

## Application and library entry comparison

| Entry | zicc bytes | VBCC bytes | zicc calls | VBCC calls | zicc inclusive clocks | VBCC inclusive clocks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `main` | 52 | 78 | 1 | 1 | 619,626 | 1,501,324 |
| `prim_exp` | 66 | - | 5 | - | 264,618 | - |
| `add_exp` | 207 | 461 | 2 | 2 | 291,244 | 1,000,754 |
| `mul_exp` | 207 | 1,141 | 3 | 3 | 282,032 | 991,708 |
| `num_exp` | 33 | 19 | 4 | 4 | 165,202 | 623,734 |
| `skip` | 25 | - | 14 | - | 8,178 | - |
| `printf` | 129 | 43 | 2 | 2 | 44,502 | 816,316 |
| `fflush` | 23 | 105 | 1 | 1 | 372,782 | 6,594 |
| `fgets` | 69 | 100 | 1 | 1 | 5,808 | 8,914 |
| `strtod` | 3 | 131 | 4 | 4 | 162,754 | 622,342 |

A dash means no separate call was observed (for example, VBCC inlines skip). All emitted code, including uncalled functions, still contributes to the whole-ROM footprint. Private MSFP assembly entry points without public symbols are identified by their nearest public symbol plus byte offset in the full table.

## zicc IEEE32: all called entries

| Function | PRG offset | Code bytes | Calls | Inclusive clocks | Exclusive clocks |
| --- | ---: | ---: | ---: | ---: | ---: |
| `[reset]` | - | - | 0 | 5,929,784 | 4,929,298 |
| `console_wait_vblank` | 00032a | 15 | 2 | 699,872 | 699,872 |
| `main` | 000265 | 52 | 1 | 619,626 | 586 |
| `console_init` | 000299 | 145 | 1 | 380,860 | 18,928 |
| `fflush` | 000369 | 23 | 1 | 372,782 | 204 |
| `add_exp` | 000154 | 207 | 2 | 291,244 | 3,068 |
| `mul_exp` | 000085 | 207 | 3 | 282,032 | 5,512 |
| `prim_exp` | 000223 | 66 | 5 | 264,618 | 2,550 |
| `num_exp` | 000064 | 33 | 4 | 165,202 | 2,448 |
| `strtod` | 000472 | 3 | 4 | 162,754 | 137,762 |
| `printf` | 000387 | 129 | 2 | 44,502 | 5,498 |
| `console_upload_map` | 000339 | 48 | 2 | 34,638 | 34,638 |
| `dec_format` | 0031a0 | 29 | 1 | 34,292 | 542 |
| `decimal__dec_format_raw` | 002f45 | 603 | 1 | 33,750 | 5,766 |
| `__ieee_decimal` | 0010a4 | 896 | 1 | 13,790 | 12,374 |
| `_ucmp32` | 0009a6 | 28 | 94 | 12,964 | 12,964 |
| `decimal__match` | 001424 | 108 | 8 | 10,264 | 9,520 |
| `skip` | 00004b | 25 | 14 | 8,178 | 4,808 |
| `decimal__rounded` | 002852 | 742 | 1 | 7,202 | 7,202 |
| `decimal__render` | 002c86 | 703 | 1 | 6,506 | 6,388 |
| `fgets` | 000475 | 69 | 1 | 5,808 | 5,808 |
| `console_putc` | 000408 | 106 | 14 | 4,712 | 4,712 |
| `_fadd32` | 000508 | 6 | 1 | 4,132 | 142 |
| `isspace` | 0004ba | 18 | 25 | 4,122 | 4,122 |
| `_fmul32` | 000514 | 6 | 1 | 4,052 | 142 |
| `ieee_fadd32_core` | 0009ca | 418 | 1 | 3,990 | 2,404 |
| `ieee_fmul32_core` | 000d58 | 462 | 1 | 3,910 | 2,654 |
| `unpack_checked` | 000b6c | 121 | 3 | 3,264 | 3,264 |
| `_fdiv32` | 00051a | 6 | 1 | 3,254 | 142 |
| `ieee_fdiv32_core` | 000f26 | 238 | 1 | 3,112 | 1,856 |
| `_udiv32` | 00079d | 70 | 2 | 1,416 | 1,028 |
| `tolower` | 0004f9 | 15 | 12 | 1,216 | 1,216 |
| `_scmp32` | 00099a | 12 | 4 | 1,144 | 1,144 |
| `shift_b` | 000c74 | 129 | 1 | 498 | 498 |
| `udiv16_hardware` | 0007e3 | 95 | 2 | 388 | 388 |
| `normalize_ab` | 000cf5 | 99 | 2 | 336 | 336 |

## VBCC r2 MSFP: all called entries

| Function | PRG offset | Code bytes | Calls | Inclusive clocks | Exclusive clocks |
| --- | ---: | ---: | ---: | ---: | ---: |
| `[reset]` | - | - | 0 | 2,349,888 | 2,564 |
| `__main` | 00013a | 43 | 1 | 2,216,288 | 1,234 |
| `main` | 0009f0 | 78 | 1 | 1,501,324 | 1,036 |
| `add_exp` | 00033f | 461 | 2 | 1,000,754 | 6,478 |
| `mul_exp` | 00050c | 1141 | 3 | 991,708 | 17,998 |
| `powl` | 002fd0 | 21 | 6 | 934,400 | 3,744 |
| `__flttouint16+$12c` | 002e5f | 231 | 6 | 926,888 | 3,248 |
| `printf` | 0028fe | 43 | 2 | 816,316 | 1,756 |
| `vfprintf` | 000a3e | 2389 | 2 | 814,560 | 44,506 |
| `indir_call_r0` | 000137 | 3 | 2 | 713,730 | 713,730 |
| `_INIT_0_MSFLOAT+$16b` | 002a94 | 62 | 7 | 674,222 | 12,000 |
| `num_exp` | 000981 | 19 | 4 | 623,734 | 1,392 |
| `strtod` | 003145 | 131 | 4 | 622,342 | 9,104 |
| `fscanf` | 0031c8 | 43 | 4 | 608,618 | 3,608 |
| `vfscanf` | 001934 | 2733 | 4 | 605,010 | 48,450 |
| `_INIT_0_MSFLOAT+$1a9` | 002ad2 | 3 | 69 | 502,056 | 41,838 |
| `_INIT_0_MSFLOAT+$1d0` | 002af9 | 6 | 192 | 432,256 | 432,256 |
| `__flttouint16+$69` | 002d9c | 24 | 7 | 412,830 | 9,064 |
| `__flttouint16+$b5` | 002de8 | 98 | 6 | 313,148 | 7,460 |
| `__flttouint16+$81` | 002db4 | 4 | 6 | 250,376 | 14,368 |
| `__flttouint16+$85` | 002db8 | 48 | 7 | 225,478 | 6,764 |
| `_INIT_0_MSFLOAT+$1d6` | 002aff | 38 | 64 | 192,872 | 192,872 |
| `log10l` | 00189a | 18 | 1 | 113,966 | 696 |
| `_INIT_0_MSFLOAT+$27` | 002950 | 3 | 64 | 110,896 | 49,536 |
| `logl` | 002fb5 | 9 | 1 | 101,624 | 404 |
| `__floadarg+$6c` | 002b95 | 3 | 7 | 95,710 | 87,392 |
| `clear` | 000102 | 32 | 3 | 93,286 | 93,286 |
| `_INIT_0_MSFLOAT+$1fc` | 002b25 | 4 | 161 | 89,460 | 89,460 |
| `__mulflt32` | 002f94 | 12 | 16 | 89,218 | 7,480 |
| `_INIT_0_MSFLOAT+$1ac` | 002ad5 | 36 | 17 | 82,660 | 14,202 |
| `fputc` | 00146c | 17 | 14 | 57,626 | 5,452 |
| `__putc` | 00147d | 129 | 14 | 52,174 | 22,200 |
| `__divflt32` | 002fa0 | 12 | 3 | 41,442 | 1,350 |
| `__floadarg+$6f` | 002b98 | 160 | 3 | 37,820 | 36,510 |
| `copy` | 0000dc | 38 | 3 | 37,750 | 37,750 |
| `__flttouint16+$56` | 002d89 | 19 | 7 | 33,004 | 10,924 |
| `_INIT_0_MSFLOAT+$14a` | 002a73 | 23 | 22 | 32,254 | 32,254 |
| `_putbuf` | 0014fe | 319 | 3 | 29,974 | 8,554 |
| `__floadarg+$22` | 002b4b | 2 | 98 | 27,400 | 27,400 |
| `_flushbuf` | 0017c3 | 196 | 3 | 26,738 | 9,274 |
| `__sint16toflt32` | 003009 | 13 | 11 | 24,820 | 5,048 |
| `__flttouint16` | 002d33 | 49 | 13 | 24,618 | 3,180 |
| `_INIT_0_MSFLOAT+$161` | 002a8a | 10 | 31 | 24,188 | 24,188 |
| `__flt32touint16` | 003094 | 12 | 6 | 18,902 | 1,260 |
| `_INIT_0_MSFLOAT+$10` | 002939 | 3 | 7 | 18,664 | 14,616 |
| `__floadarg+$18e` | 002cb7 | 5 | 11 | 18,386 | 18,386 |
| `__write` | 00178b | 56 | 4 | 17,884 | 6,588 |
| `__floadarg+$165` | 002c8e | 8 | 100 | 17,526 | 14,936 |
| `__flttouint16+$31` | 002d64 | 37 | 6 | 14,782 | 9,346 |
| `__addflt32` | 002f7c | 12 | 7 | 14,054 | 3,270 |
| `fgetc` | 002435 | 10 | 9 | 13,486 | 13,486 |
| `__flttouint16+$213` | 002f46 | 17 | 51 | 12,880 | 12,880 |
| `__subflt32` | 002f88 | 12 | 6 | 11,742 | 2,700 |
| `__chrout` | 0016f9 | 146 | 14 | 11,296 | 11,296 |
| `__floadarg+$186` | 002caf | 8 | 7 | 11,014 | 11,014 |
| `__uint16toflt32` | 003016 | 14 | 6 | 10,994 | 2,932 |
| `_INIT_0_MSFLOAT+$13` | 00293c | 20 | 12 | 10,966 | 10,450 |
| `__floadarg+$10f` | 002c38 | 6 | 13 | 10,794 | 7,976 |
| `__flttouint16+$224` | 002f57 | 37 | 39 | 9,134 | 9,134 |
| `fgets` | 0031f3 | 100 | 1 | 8,914 | 8,914 |
| `__floadarg+$193` | 002cbc | 4 | 6 | 7,480 | 7,480 |
| `fflush` | 00288d | 105 | 1 | 6,594 | 592 |
| `nungetc` | 0018b3 | 129 | 4 | 6,568 | 6,568 |
| `_INIT_0_MSFLOAT+$2a` | 002953 | 220 | 7 | 6,244 | 3,668 |
| `__floadarg+$115` | 002c3e | 4 | 7 | 5,144 | 4,070 |
| `strlen` | 002879 | 9 | 4 | 4,620 | 4,620 |
| `__floadarg+$14f` | 002c78 | 3 | 7 | 4,586 | 2,404 |
| `__floadarg+$119` | 002c42 | 37 | 6 | 3,984 | 3,308 |
| `__flt32tosint16` | 0030a0 | 31 | 1 | 3,636 | 296 |
| `__cmpsflt32` | 002fac | 9 | 4 | 2,994 | 712 |
| `_INIT_0_MSFLOAT+$128` | 002a51 | 34 | 26 | 2,692 | 2,692 |
| `tolower` | 001888 | 18 | 10 | 1,840 | 1,840 |
| `__floadarg+$24` | 002b4d | 72 | 6 | 1,824 | 1,824 |
| `__floadarg+$152` | 002c7b | 19 | 6 | 1,796 | 1,796 |
| `__floadarg+$13e` | 002c67 | 17 | 6 | 1,652 | 1,652 |
| `__uint24toflt+$42` | 002d02 | 49 | 4 | 1,282 | 1,282 |
| `__floadarg+$175` | 002c9e | 17 | 7 | 1,176 | 1,176 |
| `toupper` | 002423 | 18 | 4 | 720 | 720 |
| `__flttouint16+$117` | 002e4a | 21 | 6 | 644 | 644 |
| `_INIT_0_MSFLOAT+$106` | 002a2f | 34 | 1 | 516 | 516 |
| `localeconv` | 0018ac | 7 | 5 | 460 | 460 |
| `_chkabort` | 001887 | 1 | 6 | 264 | 264 |
| `__floadarg+$16d` | 002c96 | 8 | 1 | 212 | 110 |

## JML versus JSL main

An otherwise identical ROM was patched at the startup transfer only. JSL exposes main as a profiler entry: **True**; JML: **False**. The measured iteration is 619,534 clocks with JSL and 619,582 with JML. The three-byte root return frame changes stack addresses; instruction/data timing and VBlank phase can therefore differ slightly. Both variants produce 30. The normal build uses JSL/RTL and halts after main returns.

Recursive inclusive totals above 100% remain expected after JSL: the same time interval appears in both outer and recursive invocations. The old `end_*` labels have been removed; byte sizes use `__size_*` constants, which do not alias code entry addresses.
