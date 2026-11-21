# Stack-argument frame reservations

When the caller has already put an argument on the stack, the called function can use it there. Skipping the second reservation leaves more stack space for local variables.

This change followed the removal of unused loop cursor and induction homes.
Ordinary functions now omit the local reservations for parameters already housed
on the incoming stack. The caller ABI, parameter objects and parser/type layout
are unchanged; this work is separate from union development.

## Layout and ownership

A shared classification predicate identifies word arguments in the first two
positions as register arguments; existing variadic call rules remain in place.
Other arguments use the incoming stack, including wide arguments in the first
two positions. Their rounded local reservations were previously allocated by
the parser and left unused after the emitter redirected their symbols.

After specialized leaf selection, the ordinary path removes those reservations
and shifts retained symbol, function-cursor, affine-cursor and div/mod-cache
offsets consistently. All removed widths are whole words, preserving existing
object alignment and padding. Final frame size and wide-return scratch are then
calculated, followed by incoming parameter offsets. Register-argument homes stay
allocated; stack arguments remain private, writable, addressable incoming copies.

The ordinary path now tracks the need for a Y frame base independently of the
allocated byte count. A zero-byte frame still saves Y, establishes it from S,
maps stack parameters above saved Y and the near return address, and restores Y
before returning. The existing small-frame push/pop path handles two- and
four-byte frames, including an A-only second argument when the first argument
is wide, or an X-only first argument when the second is wide. Wide and floating
returns preserve A/X through all these transitions.

## Verification

The existing frame suite includes `tests/stack_argument_cases.c`, which checks:

- zero allocated bytes with word, wide, float and void returns;
- transitions to two/four bytes, with mixed register/stack arguments;
- mutable and address-taken stack words, bytes, longs and floats;
- eight mixed arguments, nested calls and recursion;
- relocated structs, arrays, derived cursors and div/mod cache storage.

The source passes both MSVC reference execution and target execution. Existing
ABI hooks assert return order, caller Y/D/DBR and stack restoration for every
exported C function. Additional instruction callbacks measure the actual minimum
S during the fixture, including transient pushes and runtime helper execution.
Assembly assertions check the zero/two/four-byte prologues and matching returns.

The queue remains 27 logical suites / 76 jobs, with the additional fixture inside
the existing sequential frame suite. Final `make check` passed all 27 suites,
all 76 jobs and all 200,873 arithmetic cases in 286.54 seconds, using the normal
hardware-thread default of 20 workers. Logs and summary:
`build/check/20261106T161907.030785Z/` (UTC naming; November 7 locally).

## Measurements

Both versions use the same separately compiled opaque kernel and driver sources,
without LTO, with input/call/write/result assertions and the same FastROM and
near-pointer runtime. Every raw sequence was reproduced three times.

| Opaque kernel | Frame bytes before/after | Peak stack bytes below call entry, before/after | Code bytes | Complete-call master clocks |
|---|---:|---:|---:|---:|
| Across five row elements | 8 / 6 | 10 / 8 | 71 / 71 | 942 / 942 |
| Down three column elements | 8 / 6 | 12 / 10 | 72 / 72 | 1000 / 1000 |
| Three rows of five elements | 8 / 8 | 12 / 12 | 118 / 118 | 2592-2632, unchanged |
| Five columns of three elements | 8 / 8 | 14 / 14 | 116 / 116 | 4626-4666, unchanged |
| Runtime row | 10 / 8 | Not profiled here | 183 / 183 | All counts 0-65 unchanged |

The ordinary large-frame instruction counts stay the same in these kernels;
the changed frame-size immediates save stack space, without a timing gain.
The nested kernels have two register arguments and no duplicate stack reservation.

Representative allocated frame sizes in the mixed ABI fixture are:

| Function/form | Before | After |
|---|---:|---:|
| Two stack longs, wide return | 10 | 0 |
| Two stack longs, word return | 8 | 0 |
| Stack long, void return | 4 | 0 |
| Two stack floats, float return | 10 | 0 |
| Wide/word or word/wide arguments | 8 | 2 |
| Mixed arguments with a retained word local | 10 | 4 |
| Two register words and two stack words | 8 | 4 |
| Eight mixed arguments | 20 | 4 |
| Recursive mixed arguments | 10 | 2 |
| Stack operands with div/mod cache | 16 | 12 |
| Stack arguments with retained objects/cursor | 26 | 20 |

The complete ABI fixture has 465 instrumented C calls in both versions. Its
minimum observed SP rises from 8082 to 8122: 40 fewer peak stack bytes in that
fixture. Application CODE size, excluding runtime/startup, falls from 1958 to
1786 bytes. Three retained-ROM replays reproduce these values with the same
source/runtime hashes and ABI/result assertions. This is a whole-program ABI
fixture, not a matched arithmetic/kernel throughput comparison; its raw elapsed
times are retained without using them as throughput claims.

The zero-count runtime path remains 27 instructions and 92 CPU cycles. Controlled
replay gives identical results for all 1024 paired calls across 331 horizontal
phases, repeated three times: 567 calls at 592 master clocks and 457 at 632 in
each version. The original driver zero-count samples are both 632 clocks.

## Evidence and reproduction

All evidence is local to this worktree under `build/stack-argument-evidence/`:
the frozen baseline compiler and `before/source.zip`, original loop/frame-suite
outputs, the new baseline ABI fixture, candidate outputs, source/compiler/runtime
hashes, objects, ROMs, labels, assembly, raw logs and full-check results.


The corresponding `results.json` files
contain the inventories and every repeated sample. `make-check.log` contains the
full launcher result. A failed first reporting-tool attempt is also retained;
its assertion counted one generated return callback instead of four. It required
no compiler change, and the corrected replay passed.

The later [register-entry cleanup](register-argument-homes.md) omits unused
register homes and provably dead incoming spills in ordinary functions.
