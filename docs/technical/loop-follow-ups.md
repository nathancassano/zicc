# Loop follow-up milestones

These changes let more loops use short runs of direct stores. They cover different value sizes, nested loops, and loops whose index is still needed after the last store. Each section shows when the compiler can take the shortcut.

These measurements use the ABI and memory layout of the earlier entry-only
cursor implementation.

## 1. Byte/wide stores and incoming register values

The existing full-unroll cost selection now admits integer byte and wide stores.
Byte regions set M=8 only around the stores and restore M=16 before returning.
Wide regions write each low/high pair in source iteration order. Private incoming
stack objects and literals can supply wide values; floating conversions and
widening a narrower runtime value retain ordinary lowering.

Formal 1 can supply a byte/word store value while also contributing to the
address. Its incoming A is preserved in caller-clobbered arithmetic scratch
before the bounded inline address selector runs. No helper or call intervenes.
There is no frame or additional stack traffic. Global/aliased reloads retain the
ordinary path.

The expanded entry-cursor fixture checks byte truncation, a high-bit wide literal,
wide stack arguments and A used simultaneously as row and store value. Both the
frozen baseline and candidate execute the same fixture; its timings are ABI and
correctness evidence, not opaque kernel throughput. Generated assembly assertions
check the width restoration, six ordered wide stores and absence of prologues.

Evidence: `build/leaf-width-evidence/` retains the baseline compiler/source,
matched fixture outputs, candidate compiler, replay logs and full verification.

The byte/wide example frames shrink from six bytes to zero; measured peak stack
below their call entries drops from eight/ten bytes to zero. The matched ABI
fixture shrinks from 3743 to 3524 application code bytes. Three repeated replays
pass with identical source/runtime inputs and call counts.
`make check`: 27/27 suites, 76/76 jobs, 200,873 arithmetic cases; default 20 workers, 280.27 seconds. Full log: `build/check/20261106T183123.681821Z/`.

## 2. Visible final indices

A selected full-unroll leaf may now return its local induction index directly.
The final value is `(initial + span) mod 65536`; an empty region returns the
initializer, not the bound. The tail must be exactly `return index`, the return
must be a word integer, and the body must retain the existing private-input and
unobserved-body-index proofs. Other post-loop statements or observations keep
ordinary homes/recovery. No AST or externally visible index object is rewritten.

Added cases exercise nonzero empty starts, negative starts and unsigned high-bit
final values as well as the existing visible-index example. All use the same
baseline/candidate driver with full matrix and ABI assertions. Evidence is in
`build/final-index-evidence/`.

The visible-index example drops from an eight-byte frame and ten bytes of peak
stack below call entry to zero. The expanded fixture shrinks from 3837 to 3656
code bytes; three independent-process Core replays pass with matched source,
runtime and calls. The first full run exposed a stale negative-start assembly
expectation (26/27 suites); it is retained. The replay utility now runs one Core
instance per process and pauses explicitly at completion, avoiding GUI footer
repetitions and unsupported repeated DLL initialization.
`make check` finally passed 27/27 suites, 76/76 jobs and 200,873 cases in 281.35 seconds, default 20 workers (`build/check/20261106T184812.007462Z/`). Both earlier assertion failures are retained; the second was an overbroad test update for the body-visible unsigned index.

## 3. Nested and runtime-count regions

Constant rectangular whole-function regions may expand both loops when the inner
region already passes affine/full-unroll selection, both indices are private,
the outer bounds are constant, and total work fits 32 stores and 128 estimated
bytes. The address evaluator substitutes each proven outer entry value. Regions
retain source iteration/store order, including column-major traversal; they do
not flatten or reorder memory operations. The incoming value may be A, a private
stack object or a literal. Width changes and wide pairs follow milestone 1.
Empty regions evaluate neither an address nor a value. Visible indices,
nonrectangular bodies, side effects and oversized regions keep ordinary lowering.

Runtime groups save/initialize the DP counter before forming the entry cursor
directly in X. No affine cursor home is allocated for a selected unroll plan;
the trip count is reloaded from DP after address formation. Entry guards, zero
writes for zero trips, grouped/tail policy and saved-counter ownership remain.
Counter setup cannot call or alter the private address inputs. Ordinary affine
regions still have their required homes.

The expanded ABI fixture checks negative outer/inner starts, byte/wide regions,
empty outer loops and oversized fallback. The existing opaque separate-TU drivers
assert every call/input/write and full matrix contents, with runtime counts 0..65.
Evidence: `build/region-evidence/` (frozen source/executable, before/after assembly,
ROMs, execution assertions, hashes and repeated profiles).

Opaque nested-row calls fall from 2592–2632 to 860–900 master clocks and shrink
from 118 to 66 bytes; nested columns fall from 4626–4666 to 1000–1040 clocks,
116 to 74 bytes. Both frames drop from eight bytes to zero, and measured peak
stack below entry drops from twelve/fourteen bytes to zero. Three repetitions
assert the expected calls, inputs, individual writes and complete matrices.

Runtime-row frame storage falls from eight to six bytes. Calls at counts 1, 32
and 64 change from 1318/3014/4658 to 1278/2974/4618 clocks in the retained driver.
All 66 trip counts pass three repetitions. Controlled-phase zero-count replay
is unchanged: 1024 calls, 331 phases, three repeats, 27 instructions / 92 CPU
cycles, 567 samples at 592 clocks and 457 at 632. Unchanged single-loop leaf
instructions can shift by a 40-clock refresh stall as preceding calls shorten.
The expanded ABI fixture shrinks from 5096 to 4733 code bytes; its whole-driver
time is not a throughput claim.
`make check` passed 27/27 suites, 76/76 jobs and 200,873 cases in 279.90 seconds with 20 default workers (`build/check/20261106T185507.898478Z/`).

## 4. Function-cursor storage and general address staging

A use scan excludes addresses already owned by selected affine/unroll regions.
A function cursor with no remaining consumer is removed before induction-home
compaction and divmod planning. Its symbol/cursor/region offsets are compacted,
and its entry/assignment synchronization disappears. A consumer elsewhere keeps
the cursor. This can also remove an otherwise artificial incoming-parameter
liveness dependency. Selected regions then form their address from the original
private inputs, rather than reading an unnecessary function-wide cache.

General pointer addition/subtraction with a simple word scalar now saves the
pointer in arithmetic lhs scratch while the bounded inline scale uses A and rhs
scratch. It reads the scalar once and never calls. Complex expressions/calls
retain recursive stack staging; the existing faster direct-add selector remains
preferred. This is not general register allocation.

A new fallback test exposed a baseline defect: comparison with a decaying row
array selected its first element as a memory operand. The retained instruction
trace proves the call returns the correct pointer (256), then generated code
compares it with the matrix contents. An array operand guard and separate
semantic regression cover global and local row-address comparisons. The matched
ABI inventory uses explicit address operands and remains identical source for
both compilers. Initial failed fixture/trace artifacts are retained.

Evidence: `build/cursor-staging-evidence/`, including frozen baseline sources,
matched fixture builds, pointer/address assembly and repeated profiles.

The matched staged-row frame shrinks from six to four bytes and measured stack
depth below entry from eight to six. Pointer subtraction and struct-pointer
scaling each remove two measured stack bytes; the call-containing fallback
retains its fourteen-byte peak. A function with another cursor consumer retains
its ten-byte frame. Three independent-process replays pass. The matched fixture
shrinks from 5663 to 5489 code bytes, without interpreting its total time as
kernel throughput. The pre-guard full run passed all 27 suites; the first guarded
run exposed only the new regression's harness classification (it has no loop),
which is corrected in the retained final run.
`make check` passed 27/27 suites, 76/76 jobs and 200,873 cases in 276.27 seconds with the 20-worker default (`build/check/20261106T191446.062895Z/`). Earlier runs and the harness-only failure are retained.

## 5. Parameter liveness across control flow and later escapes

Incoming-value liveness now propagates backward through statement lists and
branches. Full plain assignments kill the old value; reads and address formation
require it. Loop analysis finds a Boolean fixed point across conditions, steps,
back edges, break and continue targets; returns discard fallthrough requirements.
A for initializer can kill the input before a zero-trip loop, while a while-body
write cannot. A do-body write may kill it on every path unless break/continue
bypass that write. Complex expression sequencing remains conservative. Analysis
has a 4096-statement-visit budget per query and retains liveness on exhaustion.

An address escape after a definite overwrite retains the object's home and
identity without requiring its incoming contents. Escapes before a write, reads
in conditions, self/compound assignments and paths without a definite write keep
the spill. Function cursors whose incoming index is dead now defer initial setup
to the defining writes; cursors with live incoming inputs keep entry setup.

The register-argument fixture adds both-branch writes, early returns, for
initializers, do/while zero-count distinctions, break/continue paths, conditional
early escapes, later escapes and a retained cursor initialized by both branches.
The cursor is tested with initially invalid row inputs (32767 and -32768) which
must be overwritten before a destination is consumed. Frozen baseline and candidate use
identical source, MSVC reference results and per-call Y/D/DBR/stack assertions.
Evidence is in `build/liveness-evidence/`; exploratory builds are separately
retained under `build/liveness-trial/`.

Three independent-process ABI replays pass all 1313 calls. The matched fixture
shrinks from 3103 to 3055 code bytes. Frame sizes and peak stack are unchanged:
these objects still need homes for their new values and later address identity.
Larger-frame branch/cursor examples drop actual entry save/store instructions;
small-frame PHA allocation may still incidentally write A while reserving space.
The retained cursor skips its old-value entry address setup entirely.
`make check` passed 27/27 suites, 76/76 jobs and all 200,873 arithmetic cases in 278.54 seconds with the default 20 workers (`build/check/20261106T192106.284112Z/`). The retained executable matches the summary compiler hash. Opaque-kernel output is unchanged by milestone 5; the final 1024-call, 331-phase zero-count replay is identical over three repetitions (27 instructions / 92 CPU cycles).
