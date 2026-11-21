# Direct accesses through direct-page pointers

A `__dpage` pointer stores an address in a small area the CPU can read
directly. The data at that address can live elsewhere. zicc can read or write
through a named pointer in that area without first copying the pointer.
`src/dpage_access.inc` checks for eligible static-storage pointers before
emitting instructions. A near pointer holds two address bytes. A far pointer
holds three plus padding. The linker checks that the entire pointer fits in
$0022-$00FF, including pointers defined in external assembly.

The recognizer returns the pointer symbol, address kind, transfer type/width,
offset and scaled index, and whether the transfer borrows Y. Recognition emits
no assembly and does not mark symbols or scratch as used. Constant-address and
named-ROM accesses retain priority, as do whole-loop/address-cursor selectors.

## Selection

- Plain near byte/word loads use `(pointer)`. Existing nonvolatile byte loads
  retain their LDA/narrow sequence; volatile bytes use A8 for one byte exactly.
- Far byte/word loads use `[pointer]`; four-byte integer, pointer and floating
  values use indexed long-indirect transfers, preserving Y and the A/X result.
  Volatile wide values read low word then high word; ordinary wide values keep
  the fallback's high-word-first ordering. Address lookup consumes three bytes,
  not the far pointer's padding byte.
- Nonnegative far offsets, indexed accesses and nested fields can use
  `[pointer],y`. An unsigned byte/word index, or a bounded nonnegative mask,
  must prove that scaling and field offset fit Y. Wide values additionally
  leave room for the second word's offset. Scaling and offsets are applied once.
- Byte/word simple assignments can store through the original pointer when
  index/RHS evaluation has no calls, writes, updates or volatile observations.
  Indexed stores evaluate operands while Y still owns the normal frame, then
  borrow Y for the transfer. Assignment results and divmod invalidation are
  preserved. A single transfer may overwrite its own pointer storage because
  address fetch finishes before the store begins.

Volatile pointees are distinct from volatile pointer objects. Pointer objects
qualified volatile stay on the original lowering, preserving their value-read
width/order. Arrays, ordinary pointers, automatic pointer objects, effectful
bases/indices, and cast bases are not candidates. Placing an ordinary pointer's
target in DP does not make the pointer eligible.

Near nonzero offsets/indexing retain the existing lowering: near pointer
arithmetic truncates its base modulo 65536, while indirect,Y can carry into
the next bank. Near wide loads also retain the existing X-based lowering
because direct indirect transfers lose after the required Y saves. Wide stores
keep a captured address because their first component could overwrite the
pointer needed by the second. Negative/unbounded/scaling-overflow offsets,
compound updates and new post-increment patterns remain on fallback. The
existing simple near byte post-increment selector is retained.

`--no-direct-dpage` disables this selection, including the established simple
near cases, for paired tests. It is independent of the DP,X array-cursor switch
`--no-indexed-dpage`; neither option changes the ABI or DP allocation.

## Verification

The registered `dpage-access` compiler part compiles identical drivers and
opaque kernels as separate translation units without LTO, enabled/disabled.
It checks function-local assembly, actual object-reported function sizes,
executed calls, return values and Y/D/DBR/SP preservation. Eligible fixture
functions must be smaller than their fallback. Two fresh emulator runs per
configuration must agree on clocks and ROM/compiler hashes.

Additional fixtures compare target read/write traces at WRAM bank edges and
24-bit wrap, unsigned scaled-index overflow, signed negative offsets, near
wrapping and wide stores overlapping the DP pointer itself. Volatile byte/wide
reads and writes and volatile pointer-object reads require exact widths/order.
These explicit machine-address probes supplement ordinary C object tests;
they do not enlarge the documented near-object address range.

A far pointer at $DC tests the allocation limit and a bad external pointer at
$DF must fail the placement assertion. The regular fixture covers external
definitions, signed bytes, floating transfers, fields, locals and assignment
results. Evidence is retained under `build/dpage-access-check/`: assembly,
objects, debug-symbol sizes, ROMs, scripts, input hashes and repeated results.

No runtime source change is required. Production ROM and generated runtime
assembly equivalence is checked separately against the pre-change snapshot;
the existing calculator near-DP path is deliberately preserved.

## Final results, 2026-11-08

The final compiler SHA-256 is
`745c9531f68232ce886319c931b1ca8739f4ae1d530e142cc917d082c2b8fa88`.
`make check` passed 27/27 suites and 762 jobs at the 20-worker hardware-thread
limit in 64.78 seconds, retaining all 200,873 arithmetic cases. Summary:
`build/check/20261108T031902.599499Z/summary.json`. Focused volatile, pointer-cost,
member, struct and DP,X checks also passed before the full run.

The new fixture executes 47 opaque kernel entry points. All 29 positively
selected functions are smaller than their disabled-selector versions, based
on ca65 object debug-symbol sizes. Examples, in bytes:

| Function | Direct | Fallback |
|---|---:|---:|
| Near byte load | 6 | 9 |
| Far byte load | 10 | 18 |
| Far word load | 3 | 11 |
| Far long load | 11 | 19 |
| Indexed far word load | 11 | 64 |
| Indexed far structure field load | 24 | 86 |
| Far word store | 4 | 27 |
| Indexed far word store | 24 | 80 |

The complete fixture takes 30,230 versus 40,518 master clocks in two agreeing
fresh emulator processes per configuration. This compares the whole fixture;
the disable switch includes the established near cases, so that difference is
not presented as solely the new far selector's gain or as isolated arithmetic
throughput. Exact call coverage, C results and the 22 paired bank/wrap/overlap
traces passed. Placement tests exercise a far DP pointer at $DC and reject a
four-byte external pointer at $DF.

`build/dpage-access-baseline/inputs.json` records the pre-change compiler and
runtime/input hashes. `build/dpage-access-check/runtime-equivalence.json`
confirms unchanged runtime sources, byte-identical generated `build/decimal.s`,
and identical normal minimal, prompt, calculator and Dhrystone ROM bytes.
The fixture report retains compiler/runtime/source/tool hashes and the actual
per-function assembly and object sizes. The ordinary existing workload does
not exercise the newly added far forms; no runtime source was changed.
