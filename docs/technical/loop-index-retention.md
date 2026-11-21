# Loop-local X/Y index retention

When a loop visits equally spaced array elements, zicc can keep the byte
offset in register X and advance it after each visit. This saves the work of
calculating the offset again for each access. The [known-bit and range results](known-values.md)
use this build as their baseline.

Implemented in the isolated checkout on top of the direct indexed operand
milestone. Baseline is its frozen executable and accepted `final-build`/
`final-logical600` evidence, not an unmodified master executable or the hand-written
ideal loop. All changes remain uncommitted; the original checkout is unchanged.
No `make check` or aggregate verification command was run.

## General selection

`src/index_retention.inc` selects bounded ascending for-loops with a private,
unescaped byte/word counter, constant `<`/`<=` limit and unit increment. It finds
affine indexed memory uses structurally, chooses a frequently used byte stride,
and keeps that displacement in X. There are no source, function or asset-name
checks. Existing specialized loop selectors retain priority.

A first speculative trial also holds the C counter in Y. Scalar reads of the
counter become TYA; affine accesses with the selected stride use X and ordinary
byte accesses can use Y. Positive constant offsets stay in memory operands, e.g.
HDMA offsets 3 and 4. X advances by its stride, Y by one, rather than recomputing
subscript expressions and reading/updating the counter home every iteration.
The original Y/frame base is saved once and restored on every loop exit.

When Y is unavailable because the emitted body still accesses its frame, a second
trial retains only X and maintains the counter in its original home. The focused
fixture exercises this X-only path with 20 live scalar locals.

The emitted body is audited for register ownership, calls, index-width changes,
frame-base accesses and unsupported machine-state effects. A failed trial restores
the codegen state and assembly and falls back. Y-bound counters cannot silently be
read through stale homes: direct-memory shortcuts are excluded, and any other
counter-home access rejects the trial. Unmatched indexed accesses temporarily save
X and cannot mistake that temporary X for the retained displacement. ROM indexed
loads cooperate with the same binding/scratch protocol.

This first selector rejects calls/helpers, volatile bodies, mutation or escape of
the counter, non-unit steps, variable bounds, wide scalar work, returns from inside
the loop and unsupported control flow. It can optimize an innermost loop inside an
otherwise unselected outer loop; it does not retain two independent nested counters
at once. Competing existing cursor/frame-free choices remain valid fallbacks.
Signed entries need a visibly nonnegative start representable in the counter type;
conversion of an out-of-range constant cannot bypass that requirement. Limits must stop before counter
wrap, including unsigned-byte wrap, and `_Bool` counters are excluded because their
value stays at one after the first increment.
Folded affine offsets must also stay within the original 16-bit displacement
range throughout the loop. An access that would wrap retains its ordinary
evaluation through a saved scratch X, preserving unsigned subscript arithmetic.

`break` and `continue` use the retained loop's own exit/step labels. Y is synchronized
back to the C home at the exit, and a zero-trip entry bypasses the binding/save
entirely. Calls and unsafe register clobbers are rejected, not assumed harmless.
`--no-loop-index-retention` disables this pass independently.

## BouncingSprites result against the previous milestone

The generated FastROM application selects five regions: gradient, startup sprite
initialization, startup HDMA-table initialization, movement/bounds, and the inner
collision loop. These use stride 5 or 2 in X and the counter in Y. The final OAM
pass still uses the direct-indexed lowering; it is not claimed as a retained region.

All staged C, shared headers and generated asset bytes match the baseline. The
same ROM-speed settings, startup/runtime sources, separate C units and emulator
configuration are retained. Disabling retention reproduces byte-identical assembly
for both BouncingSprites C units with the frozen prior compiler.

Average work over 600 logical frames, excluding startup and VBlank waiting:

| Build | Baseline master clocks | Retained master clocks | Retained ms | Fewer work clocks |
| --- | ---: | ---: | ---: | ---: |
| FastROM | 321,235.12 | 272,608.06 | 12.692863 | 15.14% |
| SlowROM | 382,674.65 | 324,734.98 | 15.119936 | 15.14% |

Two fresh runs per speed agree exactly. Every update matches the established
positions, velocities, full OAM shadow, HDMA table and phase. State-sequence
SHA-256 remains `0bad2bb9b559eb75c14a74746e26f6122a74175e2d3291d8deb1742b5576fd1d`.
All four final screenshots are pixel-identical to baseline, RGB SHA-256
`31f30fb3c18a97acbb3e58b3b7d8341e3289865420afda2a34fff77933192b5a`.

Both configurations now execute **600 logical updates in 600 physical frames**.
FastROM was already at that cadence; SlowROM improves from 1,200 physical frames.
Including waits, the averages are 357,365.93 clocks / 16.639261 ms for FastROM and
357,365.89 clocks / 16.639259 ms for SlowROM. Maximum measured update work is
282,226 and 336,348 clocks respectively. Milliseconds use the prior
21,477,272-master-clocks/second convention; cadence claims cover this 600-update
window.

Code size is the same for both speeds:

| Category | Baseline bytes | Retained bytes | Change |
| --- | ---: | ---: | ---: |
| Application code including shared support | 5,293 | 4,997 | -296 |
| Linked runtime code | 3,460 | 3,460 | 0 |
| Total linked code | 8,753 | 8,457 | -296 |
| Constants | 4,520 | 4,520 | 0 |
| Initialized data | 64 | 64 | 0 |
| Padded ROM | 65,536 | 65,536 | 0 |

Main shrinks 3,270 -> 3,010 bytes; gradient shrinks 350 -> 314 bytes.
`sy[i] += dy[i]` falls from 21 to 12 static instructions: it loads words through X
and bytes through Y, with no subscript calculation or saved destination index.
The old-value/RHS temporary handling remains; this does not adopt the complete
idealized eight-instruction sequence or additional arithmetic/store fusion.

## Focused validation

The new registered `index-retention` part passes in selected, disabled and
no-line-pass modes, plus an MSVC host reference. It covers byte/word counters,
scalar counter use, ROM reads that borrow X, nonmatching affine accesses, odd
strides, conditional bodies, break/continue, final counter values, zero trips,
upper unsigned-byte limits, wrapped 16-bit affine offsets and X-only retention
with frame accesses. It also
checks rejection/fallback for calls, helper-emitting multiplication, volatile
accesses, counter mutation/escape, wide arithmetic, dynamic bounds, negative signed
starts (including converted constants), early returns and boolean counters. Existing nested-loop and signed-cursor
selectors are exercised as compatible fallbacks.

Focused existing parts passed: indexed-operands, arithmetic-regions, region-homes,
stack-frames, dpage-access, volatile, multidimensional and scalar-values. The latter
includes NTSC/PAL hardware and instruction-boundary software interrupts. The final
boolean, signed-entry and wraparound refinements are covered by the new fixture; unaffected passing
parts were retained rather than repeating the aggregate. No existing test
expectation was relaxed for this implementation.

## Reproduction and retained evidence

```text
cmd.exe /d /c tools\build-compiler.cmd
python tests/check-compiler.py --part index-retention
```

Repeat timing for FastROM run 2 and SlowROM runs 1/2, using fresh paths.
`build/loop-index-retention/results.json` combines frozen/current compiler hashes,
source hashes, byte counts, repeated measurements and focused/control evidence.
Its `control-final/` directory retains exact assembly comparisons, `accepted-build/`
has the final compiler's staged sources/assembly/maps/ROMs, and `validated-timing/`
has Lua scripts, expected states, logs and screenshots for all four runs. The final signed-entry guard
was rebuilt and tested afterward; both final ROMs are byte-identical to these
measured ROMs, as recorded in `final_build_identity`. Earlier trial evidence is
preserved separately.

The profiler now resolves begin/end hooks from the C source and generated source
annotations instead of fixed compiler label numbers, and rejects ambiguous layouts.
The resolved hooks for the frozen baseline match its previously accepted addresses.
This keeps the same logical measurement interval after loop selection renumbers
labels. The 600-update assertions and clock collection are unchanged.
