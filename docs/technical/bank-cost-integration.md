# Bank-cost branch integration, 2026-11-07

This merge brought faster decimal conversion, `printf`, and reads from other memory banks into the main compiler. It kept the main branch's control over the number of digits printed and when text appears on screen.

The integrated build combined the decimal parsing changes with the newer
HiROM allocation, 512x224 Mode 5 console, NMI-owned presentation,
precision-controlled formatting and scalar compiler optimizations.

## Conflict resolution and compatibility

- Retain volatile-aware comparisons, argument evaluation and discarded updates.
  A new bus trace checks far-pointer comparisons, calls, increment and loop-step
  decrement, including exact byte order and values in both regions.
- Apply the format-cursor cache to main's invocation-local 64-byte printf frame.
  Save/restore the private cursor around every invocation, including nested NMI
  printf; preserve main's formatting, flags, padding and error behavior.
- Share one assembly raw-format body between the retained two-argument default
  entry and the precision-aware entry. The latter receives text in X, U32 bits
  at 3/5,S, then specifier/precision at 7/9,S. An 80-byte digit buffer and main's
  existing 80-byte output state retain the 0..32 precision contract.
- Add assembly dec_format_spec with main's U32-stack/specifier-A/precision-stack
  ABI. Keep complete precision-aware C implementations as references.
- Register all assembly members with the HiROM builder and export the generated
  state. Long-return transformations adjust only caller-owned homes; local
  frames keep their offsets. Allow zero spacing after od65's Name field, which
  occurs for the longer new segment names. Preserve runtime archive dependency
  order in precision-format console fixtures.

The generated C runtime object has zero executable/constant bytes and 284 BSS
bytes, retaining main's existing state layout (252 bytes on the older branch).

## Focused validation and taken cycles

390 precision fixtures per implementation and region check f/F/e/E/g/G at
precisions 0, 1, 6, 8 and 32, including zero, signed zero, subnormal, normal,
infinity and NaN cases. Results match the complete target C reference and
independent expected binary32 formatting. The 278 default-wrapper and 278
raw-entry fixtures also pass in both regions. No measured precision fixture
has a CPU-cycle regression.

Taken CPU cycles below compare complete C and assembly paths under the merged
compiler; they include callees and are not isolated wrapper-only costs:

| Input/specification | C reference | Assembly |
|---|---:|---:|
| zero, g precision 6 | 3159 | 1287 |
| 1.25, e precision 8 | 7673 | 2625 |
| 1.25, f precision 32 | 14682 | 3418 |
| maximum finite, f precision 32 | 457322 | 69330 |
| infinity, g precision 6 | 721 | 395 |

A separate cursor comparison uses main's console before/after the cache, the
same compiled driver and disabled NMI during timed calls. Both repeats agree,
including output counts and ABI assertions:

| Format length | Before CPU cycles | After CPU cycles |
|---:|---:|---:|
| 0 | 184 | 175 |
| 1 | 476 | 425 |
| 300 | 89134 | 76525 |

Evidence: `build/bank-merge/precision/`, `build/bank-merge/default/`,
`build/bank-merge/raw/` and `build/bank-merge/cursor-performance/`.

All four HiROM stages pass, extended to execute hexadecimal parsing, infinity
formatting, scientific precision 8 and fixed precision 32. The new nested printf
fixture passes nine calls, five float conversions and two nested NMIs in each
region. Volatile transfer/qualification/far-pointer/console/MMIO checks pass.
The prompt and calculator suites pass together through the shared runner:
`build/check/20261107T105152.307979Z/summary.json`.

Historical branch performance numbers in the per-port reports use their original
LoROM/console/compiler inputs; they are not substituted for measurements of this
combined main build.

## Verification scope and fixture correction

The initial full run completed 75 passing jobs and all 200873 arithmetic cases:
`build/check/20261107T105558.697110Z/summary.json`. Its compiler suite stopped
at the rounding fixture's requirement for live nested interrupts. Diagnostics
confirmed zero ISR entries inside its first long assembly call: IRQ100 and the
nested NMI had completed during caller setup instead.

Only that fixture's private enable helper now synchronizes to the start of an
active frame before arming IRQ100. The shared helper and runtime are unchanged.
All 3799 cases pass for C and assembly in NTSC/PAL, with both IRQ/NMI entries
inside each long call and two nested NMIs. No value, memory-work, ABI or live
interrupt assertion is removed: `build/bank-merge-rounded-synchronized.log`.

Passing results are retained. The compiler continuation skips its eleven
already-covered prefix checks and executes only checks not reached by the
original invocation. It verifies the compiler hash against the initial full run
before continuing. Evidence: `build/bank-merge/compiler-continuation.log` and
`build/bank-merge/compiler-continuation.json`.

Verification coverage is complete: all 27 logical suites, 76 jobs and 200873
arithmetic cases are accounted for. The compiler continuation completed all
14 previously unfinished child checks and its remaining startup, target/host,
rejection and calculator-compilation assertions. The ten decimal functions pass
all 40 implementation/region groups. Compiler and runtime inputs still match
the verified candidate. The assembled evidence is recorded explicitly in
`build/bank-merge/combined-verification.json`; this is combined coverage, not
a claim that the initial failed invocation returned success.
