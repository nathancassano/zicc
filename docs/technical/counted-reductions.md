# Counted struct reductions

A loop that multiplies two fields in every record and adds up the products can just count down the records left. The compiler checks first that the index has no other job and that skipping it preserves every read, write, and call.

The later [word by long specialization](mul16x32-specialization.md) replaces
the selected loop's `__mul32` call with `__mul16x32`. The implementation and
measurements below describe the original counted-selector step; its frame
layout and fallback rules still apply.

`src/counted_reductions.inc` selects a complete function before ordinary frame
planning. Its first supported shape is an unsigned-long sum initialized to zero,
a signed-int index initialized to zero, `i < count`, unit pre/post increment,
and `total += (unsigned long)p[i].signed_word * p[i].unsigned_long`, followed
by returning the sum. The function takes the struct pointer and signed count
in the normal X/A parameter registers. Names, struct stride and field offsets
come from the parsed program, rather than the sample.

The accepted statement grammar and reference checks prove that the index is
dead outside the loop, the bound and base remain unchanged, and no calls,
escaping addresses or additional observable statements are removed. Extra
locals, different casts/types/control flow and unrecognized reductions retain
the ordinary emitter. Either `--no-strength-reduction` or `--no-register-loops`
also retains that fallback. Matching does not change the AST or symbol offsets.

Counts at or below zero return zero before allocating a frame. Positive counts
push a private remaining count, cursor and zero sum. The eight-byte frame holds
sum low/high at Y+1/3, cursor at Y+5, and remaining count at Y+7. Each iteration
stages the signed field directly into the arithmetic scratch, using zero/FFFF
for its high word while preserving the address in X. The existing `__mul32`
performs the full product. Its result updates the sum in place. Decrementing
the remaining count replaces the signed comparison and induction variable;
the cursor advances by the struct stride only when another iteration is needed.
The dead count slot preserves the low return word during stack restoration.

## Matched measurement

Same unchanged `samples/structures_and_tables.c`, startup, integer runtime,
linker layout and FastROM settings. Each saved compiler has two independent
Mesen measurements agreeing exactly, with return zero and balanced stacks.
Timing is main entry through its return, excluding startup and exit cleanup.

| Metric | Running-cursor baseline | Counted reduction |
| --- | ---: | ---: |
| Master clocks | 20,826 | 17,450 |
| Microseconds at 21.477272 MHz | 969.68 | 812.49 |
| inventory_value code bytes | 158 | 105 |
| Application code bytes | 412 | 359 |
| All linked code bytes | 1,688 | 1,635 |
| Used non-asset ROM bytes | 1,776 | 1,723 |
| ROM file bytes | 32,768 | 32,768 |
| inventory_value allocated frame bytes | 14 | 8 |

Elapsed time falls 16.21%; the function loses 53 bytes (33.54%) and six frame
bytes (42.86%). Profiler inclusive time for its three calls falls from 17,768
to 14,392 master clocks; self time falls from 7,312 to 3,936. The four `__mul32`
calls still consume 10,456 master clocks. Profiler totals include call-boundary
overhead and are distinct from the main entry/return interval.

Evidence is in `build/counted-reduction-trial/`: saved `baseline.exe`, baseline
and candidate assembly/maps/ROMs, manifests and repeated profiles, measurement
script, comparison JSON, and full verification logs. `runtime/integers.s` and
`build/integers.o` retain their original SHA-256 hashes:

```text
f1e95caca5c8313c864cf72cbfec6635531635e1aa7f92df81a84bafbee50780
7b884d360a0ecf2ab2a6446e2fad7cdf08a6a7269ed782ada851c9b44f9d4289
```

`tests/check-struct-cursors.py` retains its twelve cursor cases and adds nine
host/MSVC and Mesen on/off reduction cases. They cover signed minimum/maximum,
negative quantities, full-width prices, carry/overflow, empty/null/negative
counts, repeat calls, 8/12-byte layouts, block bodies and pre/post increments.
Live indices, changed bases/bounds, cast chains and extra calls must decline.
The catalog additionally checks shape and timing. These cases run within the
existing struct-cursors suite in the full hardware-thread verification queue.
