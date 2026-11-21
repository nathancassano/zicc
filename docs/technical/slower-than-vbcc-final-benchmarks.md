# Slower-than-VBCC final benchmark rechecks

## zicc sample rebuilds

Each pair of numbers shows the same program built twice. The first build
came from before the first fix. The second included all 190 fixes. Each build used its own compiler and runtime, but both received
the same C sources and test inputs, including the local empty template and
the GCC and Csmith fixtures.

Measured on NTSC FastROM. Code bytes exclude data and ROM padding. Application code includes linked sample support, and linked code includes runtime and startup. Main, kernel and busy-frame windows are listed individually. Whetstone uses binary64 double. The original integer sample reflects compile-time folding, and its split-source row exercises the runtime kernels.

| Sample | Measurement | Master clocks before → after | Change | Application code bytes | Linked code bytes |
| --- | --- | ---: | ---: | ---: | ---: |
| calc (original) | first printf entry through result printf return | 504,132 → 504,078 | -54 (-0.0107%) | 563 → 557 (-6) | 12,457 → 12,494 (+37) |
| calc (runtime) | first printf entry through result printf return | 504,670 → 504,616 | -54 (-0.0107%) | 492 → 486 (-6) | 12,386 → 12,423 (+37) |
| dhrystone (original) | 3,000 verified iterations | 57,379,450 → 57,379,450 | +0 (+0.0000%) | 2,677 → 2,677 (+0) | 9,632 → 9,675 (+43) |
| function_calls (original) | main entry to return | 73,850 → 73,814 | -36 (-0.0487%) | 229 → 219 (-10) | 4,665 → 4,698 (+33) |
| function_calls (runtime) | main entry to return | 76,072 → 76,072 | +0 (+0.0000%) | 259 → 259 (+0) | 4,695 → 4,738 (+43) |
| insertion_sort (original) | main entry to return | 14,990 → 14,990 | +0 (+0.0000%) | 326 → 326 (+0) | 2,493 → 2,536 (+43) |
| insertion_sort (runtime) | main entry to return | 14,990 → 14,990 | +0 (+0.0000%) | 326 → 326 (+0) | 2,493 → 2,536 (+43) |
| integer_operations (original) | main entry to return | 144 → 60 | -84 (-58.3333%) | 64 → 47 (-17) | 4,500 → 4,526 (+26) |
| integer_operations (runtime) | main entry to return | 27,248 → 27,248 | +0 (+0.0000%) | 611 → 611 (+0) | 5,047 → 5,090 (+43) |
| minimal (original) | 1,000 idle turns | 18,520 → 18,520 | +0 (+0.0000%) | 2 → 2 (+0) | 386 → 386 (+0) |
| minimal (runtime) | 1,000 idle turns | 18,520 → 18,520 | +0 (+0.0000%) | 9 → 9 (+0) | 393 → 393 (+0) |
| prompt (original) | main to first prompt flush | 368,274 → 368,274 | +0 (+0.0000%) | 19 → 19 (+0) | 2,563 → 2,563 (+0) |
| prompt (runtime) | main to first prompt flush | 368,292 → 368,292 | +0 (+0.0000%) | 22 → 22 (+0) | 2,566 → 2,566 (+0) |
| string_processing (original) | main entry to return | 12,038 → 12,038 | +0 (+0.0000%) | 416 → 416 (+0) | 2,583 → 2,626 (+43) |
| string_processing (runtime) | main entry to return | 14,746 → 14,746 | +0 (+0.0000%) | 423 → 423 (+0) | 2,590 → 2,633 (+43) |
| structures_and_tables (original) | main entry to return | 14,296 → 14,296 | +0 (+0.0000%) | 529 → 529 (+0) | 4,965 → 5,008 (+43) |
| structures_and_tables (runtime) | main entry to return | 14,086 → 14,086 | +0 (+0.0000%) | 359 → 359 (+0) | 4,795 → 4,838 (+43) |
| Dhrystone 1.1 | 30,000 verified iterations | 263,025,346 → 263,025,346 | +0 (+0.0000%) | 1,768 → 1,768 (+0) | 8,606 → 8,649 (+43) |
| Pi C | 896-digit kernel | 508,901,690 → 508,901,690 | +0 (+0.0000%) | 1,236 → 1,236 (+0) | 7,832 → 7,875 (+43) |
| Pi hand assembly | 896-digit kernel | 389,547,992 → 389,547,992 | +0 (+0.0000%) | 649 → 649 (+0) | 3,193 → 3,193 (+0) |
| Pi old (portable C) | 896-digit legacy kernel | 5,346,730,318 → 5,346,730,182 | -136 (-0.0000%) | 480 → 480 (+0) | 7,110 → 7,153 (+43) |
| Pi matrix legacy (zicc) | kernel with buffered-output driver | 5,331,758,144 → 5,331,758,126 | -18 (-0.0000%) | 582 → 582 (+0) | 7,212 → 7,255 (+43) |
| Pi matrix legacy (snes-asm) | kernel with buffered-output driver | 3,463,013,168 → 3,463,013,168 | +0 (+0.0000%) | 463 → 463 (+0) | 4,790 → 4,833 (+43) |
| Pi matrix revised (zicc) | kernel with buffered-output driver | 500,531,412 → 500,531,412 | +0 (+0.0000%) | 1,338 → 1,338 (+0) | 7,934 → 7,977 (+43) |
| Pi matrix revised (snes-asm) | kernel with buffered-output driver | 381,844,366 → 381,844,366 | +0 (+0.0000%) | 751 → 751 (+0) | 5,078 → 5,121 (+43) |
| FX | one empty-slot pass plus loop edge | 3,296 → 3,296 | +0 (+0.0000%) | 164 → 164 (+0) | 548 → 548 (+0) |
| Empty template init | main entry to display enable | 657,616 → 657,616 | +0 (+0.0000%) | 365 → 365 (+0) | 749 → 749 (+0) |
| Empty template busy mean | mean OAM transfer window over 120 frames | 5,523.50 → 5,523.50 | +0 (+0.0000%) | 365 → 365 (+0) | 749 → 749 (+0) |
| Empty template busy worst | worst OAM transfer window over 120 frames | 5,526 → 5,526 | +0 (+0.0000%) | 365 → 365 (+0) | 749 → 749 (+0) |
| Loop access | main entry to successful exit | 151,988 → 151,988 | +0 (+0.0000%) | 1,951 → 1,951 (+0) | 4,331 → 4,374 (+43) |
| Loop access split | 48 hooked loops plus driver | 135,540 → 135,540 | +0 (+0.0000%) | 2,058 → 2,058 (+0) | 4,438 → 4,481 (+43) |
| BouncingSprites busy mean | 600 validated frame updates | 117,609.03 → 117,609.03 | +0 (+0.0000%) | 2,844 → 2,844 (+0) | 5,011 → 5,054 (+43) |
| BouncingSprites busy worst | 600 validated frame updates | 122,736 → 122,736 | +0 (+0.0000%) | 2,844 → 2,844 (+0) | 5,011 → 5,054 (+43) |
| FX mixed slots | 1,000 seeded passes with state checks | 4,238,280 → 4,238,280 | +0 (+0.0000%) | 164 → 164 (+0) | 548 → 548 (+0) |
| Whetstone | sum of eight compute sections | 36,570,927,210 → 36,513,292,852 | -57,634,358 (-0.1576%) | 7,613 → 7,386 (-227) | 31,457 → 31,350 (-107) |
| Whetstone imported UI | sum of eight compute sections | 36,574,279,274 → 36,516,656,706 | -57,622,568 (-0.1575%) | 11,372 → 11,171 (-201) | 30,539 → 30,488 (-51) |

## Torture and Csmith fixtures

| Row group | Cases | Before accepted or passed | After accepted or passed | Faster / tied / slower among matched runs |
| --- | ---: | ---: | ---: | ---: |
| GCC pilot and kernel driver | 25 | 20 | 20 | 5 / 15 / 0 |
| GCC executable far fixtures | 59 | 37 | 37 | 18 / 18 / 1 |
| GCC compile/assemble far fixtures | 48 | 40 | 40 | - |
| GCC executable upstream forms | 59 | 0 | 0 | - |
| GCC compile/assemble upstream forms | 48 | 0 | 0 | - |
| Csmith original / far fixture variants | 64 | 6 | 6 | 6 / 0 / 0 |

The compile/assemble-only fixture rows report assembled text bytes where an object was produced. Runnable fixture rows include code sizes whenever a ROM linked and timings where both runs passed with matching checksums where applicable. The same 126 successful fixture runs reproduced their clocks on repeat. The GCC far fixture `950426-1.c` rose from 2,570 to 2,594 clocks while application code fell from 165 to 154 bytes.

The two zicc snapshots show the same fixture acceptance counts. The checked-in far adaptations and original forms remain separate rows. The Windows and VBCC Whetstone frontends, Genesis Pi variants, and the historical bundled Pi ROM belong to other toolchains. The zicc portable Pi port and the supplied SNES assembly kernels were rebuilt and measured.

The IEEE32 engine accounts for the recurring 43-byte linked-code increase on ROMs such as Dhrystone and the string-processing sample.

## Evidence

The benchmark recorded sample and fixture rows, repeated fixture results,
Whetstone clocks by section, and host reference checks.

- Raw ROMs, allocation maps, assembly, test logs, and measurement scripts are under this report's directory.

| Compiler snapshot | SHA-256 |
| --- | --- |
| Before the first fix | `923527e15fe7f61d48470fbbbf09203bd3f3de5ab7546be018509d58bbc3d3a0` |
| After all 190 fixes | `153eeaa0e09ffd329b97b6d051cfd1948415e5d6bdf9f8a6793e9501107d2712` |

## Dragon FastROM A/B

The comparison uses the pre-fix and final zicc builds. Both use the same snapshot of the working game sources and generated assets. Timings are SNES master clocks.

Application code including game NMI and assembly: 42,496 → 42,488 bytes (-8 (-0.02%)).
Padded ROM: 262,144 → 262,144 bytes.

- baseline ROM SHA-256 `48e16ef96ee9c30edbf214c29e66afcbd86c4c0883cc3dfbbaab7a674b2cf8ac`
- current ROM SHA-256 `63238201594ac978399ddca0d88bd3785fe3f515761662a5f896f30ef5146331`

| Scenario / phase | Frames | Average before → after | Average delta | Worst before → after | Worst delta | Lag before → after |
|---|---:|---:|---:|---:|---:|---:|
| breath/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| breath/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| breath/idle | 44 | 72,759 → 72,720 | -39 (-0.05%) | 73,402 → 73,362 | -40 (-0.05%) | 0 → 0 |
| breath/wake | 1010 | 126,939 → 126,898 | -41 (-0.03%) | 203,492 → 203,452 | -40 (-0.02%) | 0 → 0 |
| breath/return | 850 | 188,314 → 188,273 | -41 (-0.02%) | 250,644 → 250,598 | -46 (-0.02%) | 0 → 0 |
| breath/breath_right | 300 | 159,698 → 159,655 | -43 (-0.03%) | 283,610 → 283,570 | -40 (-0.01%) | 0 → 0 |
| breath/breath_up | 300 | 104,598 → 104,556 | -42 (-0.04%) | 123,722 → 123,682 | -40 (-0.03%) | 0 → 0 |
| breath_run/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| breath_run/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| breath_run/idle | 44 | 72,759 → 72,720 | -39 (-0.05%) | 73,402 → 73,362 | -40 (-0.05%) | 0 → 0 |
| breath_run/wake | 506 | 127,768 → 127,726 | -42 (-0.03%) | 194,196 → 194,122 | -74 (-0.04%) | 0 → 0 |
| breath_run/return | 426 | 172,906 → 172,866 | -40 (-0.02%) | 249,204 → 249,152 | -52 (-0.02%) | 0 → 0 |
| breath_run/breath_right | 300 | 215,690 → 215,649 | -41 (-0.02%) | 275,734 → 275,694 | -40 (-0.01%) | 0 → 0 |
| breath_run/breath_up | 300 | 192,755 → 192,714 | -41 (-0.02%) | 267,580 → 267,540 | -40 (-0.01%) | 0 → 0 |
| facing/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| facing/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| facing/idle | 44 | 72,759 → 72,720 | -39 (-0.05%) | 73,402 → 73,362 | -40 (-0.05%) | 0 → 0 |
| facing/approach | 39 | 78,544 → 78,502 | -42 (-0.05%) | 93,030 → 92,990 | -40 (-0.04%) | 0 → 0 |
| facing/walk_lr | 720 | 83,101 → 83,060 | -41 (-0.05%) | 94,022 → 93,982 | -40 (-0.04%) | 0 → 0 |
| facing/run_lr | 360 | 84,304 → 84,263 | -41 (-0.05%) | 95,614 → 95,574 | -40 (-0.04%) | 0 → 0 |
| facing/breath_lr | 720 | 169,823 → 169,782 | -41 (-0.02%) | 211,578 → 211,544 | -34 (-0.02%) | 0 → 0 |
| hitbox_bench/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| hitbox_bench/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| hitbox_bench/idle | 44 | 72,759 → 72,720 | -39 (-0.05%) | 73,402 → 73,362 | -40 (-0.05%) | 0 → 0 |
| hitbox_bench/hitbox_bench | 300 | 160,603 → 160,561 | -42 (-0.03%) | 163,270 → 163,230 | -40 (-0.02%) | 0 → 0 |
| hitbox_sizes/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| hitbox_sizes/warmup | 60 | 119,629 → 119,590 | -39 (-0.03%) | 272,710 → 272,712 | +2 (+0.00%) | 0 → 0 |
| hitbox_sizes/empty | 300 | 106,268 → 106,228 | -40 (-0.04%) | 106,666 → 106,632 | -34 (-0.03%) | 0 → 0 |
| hitbox_sizes/distant | 300 | 168,081 → 168,037 | -44 (-0.03%) | 170,238 → 170,198 | -40 (-0.02%) | 0 → 0 |
| hitbox_sizes/near_x | 300 | 226,644 → 226,604 | -40 (-0.02%) | 229,222 → 229,182 | -40 (-0.02%) | 0 → 0 |
| hitbox_sizes/near_y | 300 | 238,480 → 238,439 | -41 (-0.02%) | 241,252 → 241,212 | -40 (-0.02%) | 0 → 0 |
| pathing/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| pathing/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| pathing/idle | 44 | 72,759 → 72,720 | -39 (-0.05%) | 73,402 → 73,362 | -40 (-0.05%) | 0 → 0 |
| pathing/walk_test0 | 535 | 105,124 → 105,083 | -41 (-0.04%) | 156,254 → 156,214 | -40 (-0.03%) | 0 → 0 |
| pathing/door_up | 176 | 145,951 → 145,915 | -36 (-0.02%) | 4,707,746 → 4,707,718 | -28 (-0.00%) | 13 → 13 |
| pathing/door_down | 62 | 153,722 → 153,690 | -32 (-0.02%) | 3,059,984 → 3,059,932 | -52 (-0.00%) | 8 → 8 |
| pathing/chase | 600 | 105,080 → 105,039 | -41 (-0.04%) | 129,818 → 129,778 | -40 (-0.03%) | 0 → 0 |
| pathing_moving/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| pathing_moving/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| pathing_moving/idle | 44 | 72,759 → 72,720 | -39 (-0.05%) | 73,402 → 73,362 | -40 (-0.05%) | 0 → 0 |
| pathing_moving/walk_test0 | 535 | 105,124 → 105,083 | -41 (-0.04%) | 156,254 → 156,214 | -40 (-0.03%) | 0 → 0 |
| pathing_moving/door_up | 176 | 145,951 → 145,915 | -36 (-0.02%) | 4,707,746 → 4,707,718 | -28 (-0.00%) | 13 → 13 |
| pathing_moving/door_down | 62 | 153,722 → 153,690 | -32 (-0.02%) | 3,059,984 → 3,059,932 | -52 (-0.00%) | 8 → 8 |
| pathing_moving/pace | 945 | 127,045 → 127,003 | -42 (-0.03%) | 175,436 → 175,390 | -46 (-0.03%) | 0 → 0 |
| player_move/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| player_move/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| player_move/idle | 44 | 72,759 → 72,720 | -39 (-0.05%) | 73,402 → 73,362 | -40 (-0.05%) | 0 → 0 |
| player_move/normal_walk | 300 | 78,001 → 77,960 | -41 (-0.05%) | 96,752 → 96,712 | -40 (-0.04%) | 0 → 0 |
| player_move/fully_blocked | 300 | 78,150 → 78,104 | -46 (-0.06%) | 82,794 → 82,754 | -40 (-0.05%) | 0 → 0 |
| player_move/edge_clear_1px | 300 | 78,128 → 78,082 | -46 (-0.06%) | 82,794 → 82,754 | -40 (-0.05%) | 0 → 0 |
| player_move/edge_clear_2px_right | 300 | 78,161 → 78,115 | -46 (-0.06%) | 82,794 → 82,754 | -40 (-0.05%) | 0 → 0 |
| player_move/edge_clear_2px_left | 300 | 78,102 → 78,061 | -41 (-0.05%) | 82,770 → 82,730 | -40 (-0.05%) | 0 → 0 |
| player_move/run_edge_clear_1px | 300 | 79,258 → 79,214 | -44 (-0.06%) | 83,298 → 83,258 | -40 (-0.05%) | 0 → 0 |
| player_move/edge_clear_horizontal_1px | 300 | 77,900 → 77,859 | -41 (-0.05%) | 82,942 → 82,902 | -40 (-0.05%) | 0 → 0 |
| player_move/edge_clear_horizontal_2px | 300 | 77,886 → 77,845 | -41 (-0.05%) | 82,948 → 82,908 | -40 (-0.05%) | 0 → 0 |
| scroll_jitter/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| scroll_jitter/approach | 23 | 111,049 → 111,013 | -36 (-0.03%) | 212,988 → 212,834 | -154 (-0.07%) | 0 → 0 |
| scroll_jitter/warmup | 180 | 104,716 → 104,674 | -42 (-0.04%) | 105,790 → 105,750 | -40 (-0.04%) | 0 → 0 |
| scroll_jitter/scroll_jitter | 600 | 104,812 → 104,770 | -42 (-0.04%) | 105,796 → 105,756 | -40 (-0.04%) | 0 → 0 |
| standard/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| standard/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| standard/idle | 224 | 72,735 → 72,694 | -41 (-0.06%) | 73,648 → 73,608 | -40 (-0.05%) | 0 → 0 |
| standard/steady_test0 | 600 | 72,739 → 72,698 | -41 (-0.06%) | 73,648 → 73,608 | -40 (-0.05%) | 0 → 0 |
| standard/walk_test0 | 535 | 104,772 → 104,731 | -41 (-0.04%) | 150,866 → 150,820 | -46 (-0.03%) | 0 → 0 |
| standard/door | 176 | 145,941 → 145,903 | -38 (-0.03%) | 4,707,746 → 4,707,718 | -28 (-0.00%) | 13 → 13 |
| standard/steady_test1 | 300 | 154,638 → 154,596 | -42 (-0.03%) | 185,394 → 185,354 | -40 (-0.02%) | 0 → 0 |
| standard_run/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| standard_run/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| standard_run/idle | 224 | 72,735 → 72,694 | -41 (-0.06%) | 73,648 → 73,608 | -40 (-0.05%) | 0 → 0 |
| standard_run/steady_test0 | 600 | 72,739 → 72,698 | -41 (-0.06%) | 73,648 → 73,608 | -40 (-0.05%) | 0 → 0 |
| standard_run/run_test0 | 268 | 105,433 → 105,392 | -41 (-0.04%) | 145,990 → 145,950 | -40 (-0.03%) | 0 → 0 |
| standard_run/door | 176 | 147,586 → 147,547 | -39 (-0.03%) | 4,711,488 → 4,711,442 | -46 (-0.00%) | 13 → 13 |
| standard_run/steady_test1 | 300 | 151,374 → 151,332 | -42 (-0.03%) | 181,778 → 181,732 | -46 (-0.03%) | 0 → 0 |
| wall_run/boot | 0 | 27,470,406 → 27,470,406 | +0 (+0.00%) | - | - | 0 → 0 |
| wall_run/post_load_warmup | 16 | 119,878 → 119,830 | -48 (-0.04%) | 203,412 → 203,372 | -40 (-0.02%) | 0 → 0 |
| wall_run/idle | 44 | 72,759 → 72,720 | -39 (-0.05%) | 73,402 → 73,362 | -40 (-0.05%) | 0 → 0 |
| wall_run/approach | 268 | 106,066 → 106,025 | -41 (-0.04%) | 145,836 → 145,802 | -34 (-0.02%) | 0 → 0 |
| wall_run/wall_press | 60 | 130,950 → 130,910 | -40 (-0.03%) | 150,114 → 150,074 | -40 (-0.03%) | 0 → 0 |

Boot rows show the fixture's cumulative timestamp at first wait.

Gameplay differences: none in per-frame fireball counts and phase-end OAM hashes, HP, and player/enemy state.

## Pathfield fixtures

| Room | Calls | Average before → after | Average delta | Worst before → after | Worst delta | Input / field hash matched |
|---|---:|---:|---:|---:|---:|---|
| 0 | 59 → 59 | 10,652.03 → 10,652.71 | +0.68 (+0.01%) | 16,428 → 16,428 | +0 (+0.00%) | True |
| 1 | 97 → 97 | 10,825.46 → 10,826.29 | +0.82 (+0.01%) | 16,428 → 16,428 | +0 (+0.00%) | True |
| 2 | 17 → 17 | 10,782.71 → 10,787.41 | +4.71 (+0.04%) | 16,428 → 16,428 | +0 (+0.00%) | True |

## Pathfield trace accounting

The stage-two pathfinding assembly was byte-identical. The linked
`pathfinding_update` moved from `$C06593` to `$C0658B`. In the linked idle,
update, steps and next-cell routines, only relocated address operands changed.
The traces matched instruction counts and relocation-normalized PC hashes for
all 11 calls whose clocks changed. Each differing instruction interval changed
by exactly ±40 master clocks. The signed interval sums accounted for the
entire measured difference. No measured call overlapped NMI.

| Room | Calls | Added stalls | Avoided stalls | Net master clocks |
| --- | ---: | ---: | ---: | ---: |
| 0 | 59 | 1 | 0 | +40 |
| 1 | 97 | 5 | 3 | +80 |
| 2 | 17 | 2 | 0 | +80 |

Room 2's 12th and 15th calls changed from 9,446 to 9,486 and from 9,782 to
9,822 clocks. They executed 416 and 430 instructions respectively in both
builds. Both entered 80 clocks earlier and returned 40 clocks earlier.
Their first traced interval rose from 28 to 68 clocks, consistent with an
extra WRAM refresh during the measured window. The remaining interval changes
canceled out. See [Mesen's DRAM refresh event](https://raw.githubusercontent.com/SourMesen/Mesen2/master/Core/SNES/SnesMemoryManager.cpp#L213-L230).

The A/B trace captures used separate output directories.

The trace wrapper uses the current Dragon profiling fixtures. Raw ROMs,
assembly, phase results and per-call traces are in `build/sr/dragon/`.
