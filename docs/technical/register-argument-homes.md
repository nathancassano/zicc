# Unnecessary register-argument homes and entry spills

A function can receive an argument in a register and never use its original value. The compiler skips the initial stack write if it can prove the function overwrites that value before reading it. An argument the function never uses needs no space at all.

This step followed the removal of duplicate frame reservations for stack arguments.

## Selection

Existing specialized leaves select their independent lowering first. In the
ordinary path, the first two word-width parameters are classified separately:

- A parameter absent from the retained body and early cursor setup needs no home.
- A referenced parameter retains its home. Its incoming spill may be omitted if
  a straight-line prefix reaches a plain assignment before any read, and the
  assignment RHS does not mention that parameter.
- Escaped addresses, self/compound updates, branches, loops and returns stop
  that overwrite proof conservatively. A leading call can be crossed when the
  parameter remains private and the prefix subsequently overwrites it.

Early function-cursor setup is checked explicitly. It may read a parameter
before the first body statement, even when that statement overwrites it. Those
incoming values retain their spills. Stack-argument homes and calling rules stay
unchanged, and caller argument evaluation still runs for unused parameters.

## Storage and prologue

Unused register reservations are compacted with duplicate stack reservations,
using complete word holes. Retained symbols, function/affine cursors and div/mod
cache offsets all move consistently. Referenced parameters that acquire a new
value still own distinct writable homes. Emitter guards reject reads/writes
through an omitted home.

The entry-spill mask controls the large-frame A backup and register-to-home
stores. Small frames still allocate their required words through pushes, using
X only when its incoming value is needed. An allocation push can incidentally
copy A into a home whose initial contents are irrelevant; it is not removed
while the storage itself remains required.

Unused X with live A, unused A with live X, zero allocated bytes with incoming
stack arguments, signed-byte normalization, pointer assignment and wide returns
are covered by focused checks. Existing Y-base, stack offset and return rules
apply. Parser/type layout and union work are separate.

Comments on changed ordinary functions expose the masks as
`register entry: homes $HH, spills $SS`: bit 0 denotes parameter 0 in X and bit 1
parameter 1 in A. These describe storage/entry preservation, not global register
allocation. No marker is added when the ordinary entry requirements are unchanged.

## Verification and measurements

`tests/register_argument_cases.c` passes MSVC reference execution and target
execution. The existing frame suite now also asserts its home/spill masks,
small-frame push ordering, absence of unnecessary large-frame stores, and
conservative address-escape/branch/self-read/cursor fallbacks. Target hooks check
449 C calls, return order, Y/D/DBR and stack restoration, global side effects,
results and instruction-boundary stack minima. Three retained-ROM replays for
each compiler reproduce the same assertions and stack measurements, with matched
source/runtime hashes.

| Case | Allocated frame before/after | Inclusive peak stack below function entry before/after |
|---|---:|---:|
| Both register parameters unused | 4 / 0 | 6 / 0 |
| X unused, A live with a retained local/call | 6 / 4 | 14 / 12 |
| A unused, X live with a retained local/call | 6 / 4 | 14 / 12 |
| Both unused, incoming stack argument read | 4 / 0 | 6 / 2 |
| X unused, A live, wide return | 4 / 2 | 6 / 4 |
| Overwritten signed-byte parameter, other argument unused | 4 / 2 | 6 / 4 |
| Both entry values overwritten, retained array/call | 12 / 12 | 20 / 20 |

The overwrite cases retain their homes but omit unnecessary entry preservation.
For example, overwriting both register parameters removes the initial A backup
and both initial home stores; later body assignments still initialize the homes.
When only one entry value is dead, the other register's preservation remains.

The complete ABI fixture's application CODE shrinks from 1566 to 1480 bytes.
Its global minimum observed SP remains 8156, because the larger retained frames
still determine that maximum. This is a whole-program ABI fixture, not a matched
kernel/arithmetic throughput comparison; raw elapsed times are retained without
using them as throughput claims.

The existing opaque assignment kernels need both incoming values. Their emitted
kernel assembly, static/dynamic driver ROM hashes, code sizes, allocated frames,
peak stack depths and all repeated timings are unchanged. Thus this stage makes
no performance claim for those loop kernels. Their byte-identical dynamic ROM
also retains the previously verified zero-count refresh behavior.

Final `make check` passed 27/27 suites, 76/76 jobs and all 200,873 arithmetic
cases in 289.87 seconds, using the hardware-thread default of 20 workers. The
new fixture runs inside the existing sequential frame suite; the shared queue
and arithmetic batches are unchanged. Full logs and summary are in
`build/check/20261106T164822.495637Z/` (UTC naming; November 7 locally).

## Evidence

`build/register-home-evidence/` contains the frozen baseline compiler and source
archive, original loop/frame outputs, baseline and candidate fixture artifacts,
source/compiler/runtime hashes, assembly, objects, ROMs, raw logs and full-check
results.


Both output directories retain `results.json` and every raw replay. The baseline
and candidate sources/patch are archived alongside the executable evidence.

The later [entry-only cursor leaf](entry-only-cursors.md) consumes X/A directly
for selected single fully unrolled word-store regions, without ordinary homes.
