# Private-home effects and liveness around volatile regions

A function that reads hardware can also have ordinary local variables. zicc
can remove an unused local copy if nothing else can read it, while still
performing each required hardware access. The later
[value and comparison reuse changes](value-reuse.md) build on this work.

The saved compiler and ROMs from the
[byte-shuffle and store-fusion trial](byte-shuffle-stores.md) are the baseline.
Focused checks covered the initial measurements. The later run added full
verification.

## General implementation

The existing private-value passes retain their whole-function safety guards.
`src/private_regions.inc` adds a bounded extension for functions those passes
exclude because they contain volatile operations. Selection depends on storage,
types and emitted effects, with no sample/function-name checks.

The extension classifies each access as compiler workspace, a proven private
frame home, a distinct named object, a fixed peripheral fence, or unknown memory.
It forwards private copies within basic blocks and runs byte-accurate backward
liveness over the resolved function CFG. Dead imports, spills and other private
stores can disappear even when another region polls hardware. Named nonvolatile
objects cannot alias these homes; aggregates are checked recursively for volatile
members. Unknown indirect accesses are barriers. Calls clear forwarding facts;
workspace liveness uses existing audited helper contracts or an unknown-call
barrier. Unescaped C frame homes are not inputs to an arbitrary callee.

Fixed peripheral addresses in SNES I/O banks remain forwarding/workspace fences;
their accesses are preserved. They cannot directly alias an unescaped stack
object, so they do not artificially keep dead C frame stores live. Volatile or
escaped frame objects are never eligible. No user-visible memory access is
deleted or coalesced by these passes.

Frame identity is not inferred merely from an `a:$offset,y` spelling. A CFG
analysis tracks when Y is the ordinary frame base, including a bounded stack
suffix of saved Y values. Joins intersect proofs; temporary cursors, retained
counters, partial index-width restores and unknown effects lose frame identity.
This distinguishes aggregate/cursor accesses from C homes and recovers the frame
after a proven PHY/PLY pair. Unresolved indirect control flow is left unchanged.

Forwarding observes access widths, overlapping stores, A/flag liveness, index
changes and barriers. Accumulator-form shifts/rotates/increments/decrements
invalidate A's value identity. The focused store-fusion check caught an early
mistake in that distinction; a new host regression covers all six opcodes and
the corrected implementation passes the original check unchanged.

`--no-private-regions` independently disables the extension and restores baseline
assembly for both sample C units. `--no-line-passes` and
`--no-body-optimizations` also disable it. Existing nonvolatile-function handling,
frame trimming and stack-relative-home restrictions remain conservative.

## BouncingSprites against the byte-shuffle/store baseline

Average work over 600 logical updates, excluding startup and VBlank waiting:

| Build | Baseline clocks | New clocks | New ms | Fewer work clocks |
| --- | ---: | ---: | ---: | ---: |
| FastROM | 235,208.24 | 234,587.32 | 10.922585 | 0.2640% |
| SlowROM | 279,555.70 | 278,831.43 | 12.982628 | 0.2591% |

Two fresh runs per speed agree exactly. Both remain at 600 logical updates in
600 physical frames. Maximum update work is 244,428 FastROM and 290,588 SlowROM
clocks. Milliseconds use 21,477,272 master clocks per second. Including waits,
FastROM averages 357,366.05 clocks and SlowROM 357,365.89 clocks per update.

| Category | Baseline bytes | New bytes | Change |
| --- | ---: | ---: | ---: |
| Application and shared support code | 4,892 | 4,833 | -59 |
| Runtime code | 3,460 | 3,460 | 0 |
| Total linked code | 8,352 | 8,293 | -59 |
| Constants | 4,520 | 4,520 | 0 |
| Initialized data | 64 | 64 | 0 |
| Padded ROM | 65,536 | 65,536 | 0 |

Main shrinks 3,004 -> 2,945 bytes; gradient remains 241 bytes. The generated main
loses dead counter imports/spills and redundant reloads in initialization and
per-frame regions. Its 30-byte frame remains. The modest recurring speed gain
does not remove the larger arithmetic, collision and live-home costs.

All staged C, shared headers and asset bytes match baseline. Startup/runtime,
separate translation units, ABI, memory speeds, NTSC emulator configuration and
measurement hooks retain the same contracts. Disabling this pass reproduces
byte-identical baseline assembly for both C units using identical input paths.

Every update matches the expected positions, velocities, OAM shadow, HDMA table and phase. All four state sequences retain SHA-256
`0bad2bb9b559eb75c14a74746e26f6122a74175e2d3291d8deb1742b5576fd1d`.
Final screenshots are pixel-identical to baseline, RGB SHA-256
`31f30fb3c18a97acbb3e58b3b7d8341e3289865420afda2a34fff77933192b5a`.

## Focused verification and evidence

The registered `private-regions` compiler part passes a host-level effect/CFG
harness and five emulated modes: selected, disabled, no-line-pass, no-retention
and explicit Y-frame mode. The C fixture uses 128 opaque word inputs and checks
loop joins, break/continue, globals, volatile locals, escaped homes, unknown
pointer aliases, calls and aggregate copies. An MSVC /Od reference passes.

`tests/private-regions-host.c` directly checks byte overlap and partial stores,
unknown-access and MMIO fences, private versus escaped/volatile homes, helper-call
boundaries, CFG/Y-stack joins, partial-width restores, unresolved transfers,
copy invalidation and accumulator-form mutations. Assertions stay enabled.

Final existing focused parts passed: region-homes, stack-frames, volatile,
arithmetic-regions, index-retention, store-fusion, byte-shuffles, body-codegen and
scalar-values. Scalar-values includes NTSC/PAL hardware and instruction-boundary
software interrupts. These checks ran sequentially against one unchanged compiler;
no existing assertion was relaxed. The earlier failing trial/log remains retained
separately from the corrected final results.

`build/private-regions/results.json` combines frozen/current compiler and source
hashes, disabled controls, matching staged-input hashes, code sizes, focused
checks and repeated timing/state/pixel results. `final-build/` retains assembly,
maps and ROMs; `final-timing/` retains four sets of Lua scripts, expected states, logs and screenshots. `control/`
retains exact assembly comparisons; `focused-final/` retains the final existing
part logs, with the successful standalone store-fusion/private-regions reports
under `build/compiler-check/`.

```text
cmd.exe /d /c tools\build-compiler.cmd
python tests/check-compiler.py --part private-regions
```

Use fresh paths and repeat timing for FastROM run 2 and SlowROM runs 1/2.
