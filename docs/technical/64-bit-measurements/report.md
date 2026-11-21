# zicc FastROM operation costs

Read each table cell as the fastest and slowest time seen for that operation.
Times are in SNES master clocks. Across 886 checked runs, each small function
read its inputs from volatile globals, evaluated one expression and wrote its
answer to a volatile global. Timing begins at function entry and ends when
control returns to the caller. It includes helper calls and the return
instruction. Setting up the inputs and calling the function happen outside
that interval.

The driver and timed functions were compiled in separate files with LTO off.
Both ROMs used the binary64-enabled compiler so they could exercise explicit
binary32 and binary64 types. Mesen checked the FastROM MEMSEL write. Each
timed result matched the reference calculation on the PC.

The ranges are for the sampled operands. They include branch paths and hardware memory timing, including WRAM refresh. They do not bound all possible operands, particularly subnormal and exceptional floating-point inputs. Eight-bit C arithmetic promotes operands to 16-bit int before arithmetic and narrows stores. Signed right shifts use the compiler's arithmetic shift semantics. Floating comparisons and logical expressions store a 16-bit int. The math rows call the f-suffixed entry points for binary32 and the unsuffixed entry points for binary64.

## Integers

| Operation | i8 | u8 | i16 | u16 | i32 | u32 | i64 | u64 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Assignment | 128 | 128 | 108 | 108 | 250–290 | 250–290 | 612 | 572–612 |
| Add (+) | 512–552 | 404 | 266–306 | 266–306 | 702–742 | 702–742 | 1,168–1,208 | 1,208 |
| Subtract (-) | 512–552 | 404–444 | 266–306 | 266–306 | 702–742 | 702–742 | 1,208 | 1,168–1,208 |
| Multiply (*) | 1,114–1,126 | 600–640 | 868–908 | 868–908 | 3,038–3,078 | 3,038 | 3,030–4,030 | 3,030–4,030 |
| Divide (/) | 1,438–1,594 | 798–838 | 1,192–1,324 | 730–770 | 1,726–2,582 | 1,276–2,092 | 51,120–59,632 | 51,068–64,364 |
| Unary minus | 302–354 | 230–270 | 138–178 | 138 | 484–524 | 484–524 | 880–920 | 880–920 |
| Logical NOT | 172–224 | 172–184 | 144–156 | 144–156 | 320–360 | 320–332 | 506–546 | 506–546 |
| Logical AND | 172–258 | 212–258 | 144–242 | 144–242 | 320–594 | 320–594 | 506–930 | 506–930 |
| Logical OR | 190–258 | 190–258 | 162–202 | 162–202 | 338–594 | 338–594 | 524–930 | 524–890 |
| Equal (==) | 460–512 | 388–440 | 178–218 | 178–190 | 860–1,032 | 832–952 | 924–1,210 | 896–1,136 |
| Not equal (!=) | 472–512 | 388–440 | 178–230 | 190–230 | 912–1,038 | 884–952 | 872–1,204 | 844–1,130 |
| Less (<) | 472–536 | 388–400 | 208–260 | 178–218 | 912–1,026 | 832–952 | 912–1,210 | 856–1,136 |
| Less or equal (<=) | 496–530 | 400–446 | 208–260 | 190–230 | 872–1,026 | 872–958 | 902–1,240 | 886–1,142 |
| Greater (>) | 472–496 | 388–412 | 190–272 | 178–230 | 900–1,020 | 844–964 | 918–1,204 | 844–1,130 |
| Greater or equal (>=) | 472–524 | 400–440 | 208–248 | 178–230 | 900–1,038 | 884–964 | 914–1,228 | 914–1,154 |
| Remainder (%) | 1,700–1,976 | 906–946 | 1,454–1,666 | 838–878 | 1,908–2,764 | 1,412–2,268 | 51,406–59,878 | 51,332–64,628 |
| Bitwise NOT | 302–342 | 200–240 | 126 | 126 | 372–412 | 372 | 868–908 | 868–908 |
| Bitwise AND | 500–540 | 374 | 254–294 | 254–294 | 690–730 | 690–730 | 1,196 | 1,196 |
| Bitwise OR | 500–564 | 374–414 | 254 | 254–294 | 690–730 | 690–730 | 1,156–1,196 | 1,156–1,196 |
| Bitwise XOR | 500–564 | 374–414 | 254–294 | 254–294 | 690–730 | 690–730 | 1,196 | 1,196 |
| Left shift | 546–670 | 504–712 | 300–424 | 384–552 | 890–1,074 | 1,074–1,442 | 1,270–1,770 | 1,730–2,690 |
| Right shift | 684–964 | 598–798 | 438–678 | 384–552 | 1,140–1,620 | 1,086–1,454 | 1,868–3,012 | 1,730–2,690 |

## Floating point

| Operation | f32 | f64 |
|---|---:|---:|
| Assignment | 250–290 | 572 |
| Add (+) | 4,782–5,398 | 6,018–6,902 |
| Subtract (-) | 5,012–5,356 | 6,156–6,764 |
| Multiply (*) | 2,146–4,636 | 1,880–72,220 |
| Divide (/) | 2,220–14,938 | 2,052–46,830 |
| Unary minus | 354 | 646–686 |
| Logical NOT | 338–390 | 524–564 |
| Logical AND | 378–590 | 524–966 |
| Logical OR | 356–630 | 542–966 |
| Equal (==) | 1,454–1,574 | 1,348–1,604 |
| Not equal (!=) | 1,466–1,580 | 1,336–1,616 |
| Less (<) | 1,466–1,602 | 1,452–1,772 |
| Less or equal (<=) | 1,496–1,580 | 1,482–1,720 |
| Greater (>) | 1,454–1,562 | 1,464–1,732 |
| Greater or equal (>=) | 1,524–1,610 | 1,494–1,720 |
| sqrt | 160,898–162,072 | 152,300–153,558 |
| log | 79,780–137,010 | 319,760–1,481,112 |
| exp | 133,648–154,538 | 1,237,840–1,608,580 |
| atan | 130,310–172,938 | 2,086,802–2,466,758 |
| sin | 78,558–119,772 | 808,848–1,223,386 |
| cos | 71,590–125,652 | 820,422–1,214,980 |

Per-input timings and result bits are in results.csv. Source, ROM, emulator, and Lua hashes are in hashes.json.

[FastROM Whetstone and Dhrystone results](fastrom-benchmarks.json) retain the
separate sample benchmark measurements.
