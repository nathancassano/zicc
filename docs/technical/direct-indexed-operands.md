# General direct indexed operands: isolated first implementation

For an array at a known address, the CPU can add an offset as it reads or
writes the element. zicc can put the offset in register X and use the array
address in the instruction itself. The [loop index retention results](loop-index-retention.md)
use this change as their baseline.

The trial used the arithmetic-region baseline with the existing main-entry and
signed-char typedef compatibility fixes. The compiler selects fixed-base indexed
memory operands before generic pointer materialization. It uses typed expression
shape and storage properties, never sample/function names. Loop register retention,
new range propagation, constant shifts and adjacent-store fusion are not part of
this change.

## Implementation and boundaries

`src/indexed_operands.inc` recognizes nonvolatile byte/word accesses to named near
arrays, member arrays in fixed global/static objects, and scalar fields in array
records. A plan holds the symbol base, index expression, element stride and field
byte offset. X receives the scaled displacement; the base remains in the absolute
indexed memory operand. Existing ROM direct-load selection remains in place.

Selected operations are loads/stores, word ADC/SBC/AND/ORA/EOR, and word CMP or
signed SBC comparisons with the existing overflow-aware branch logic. Signed-byte
loads retain normalization/sign extension. Byte stores remain A8. Constant indices
retain the existing direct absolute path. Structure strides reuse the general
constant-scale emitter, including non-power-of-two sizes.

Index expressions are evaluated once at each access. Stores save the selected
index before evaluating the RHS; compound assignments also read the old element
before the RHS, preserving existing alias/call snapshot behavior. Left arithmetic
values are saved while the RHS index is evaluated. Stack-leaf bias is tracked for
all such saves, and Y remains available as the current frame base.

Pointer variables, local arrays, dpage objects, volatile accesses, float/32-bit
values and unsupported shapes use existing lowering. All valid selected near-array
accesses remain in their declared near object/bank. The new selection does not
weaken arbitrary-pointer or volatile aliasing rules.

`--no-indexed-operands` disables this selection independently. The new include is
registered as a compiler build prerequisite; the focused test is registered in
`tests/check-compiler.py` as `indexed-operands`.

## BouncingSprites against the current baseline

Both versions use identical staged C, headers/assets, separate translation units,
ROM speed configuration, startup and runtime source inputs. Baseline is the
compatibility-fixed arithmetic-region build recorded in `build/bouncing-current-master`.
The frozen baseline executable is retained. Compiling both BouncingSprites C units
with the candidate's selector disabled produces byte-identical assembly to that
baseline executable, demonstrating that the default-on selection is isolated.

Average update work over 600 logical frames (startup and VBlank polling excluded):

| Build | Baseline master clocks | Candidate master clocks | Candidate ms | Fewer work clocks |
| --- | ---: | ---: | ---: | ---: |
| FastROM | 418,465.04 | 321,235.12 | 14.956979 | 23.23% |
| SlowROM | 494,350.67 | 382,674.65 | 17.817656 | 22.59% |

Two fresh candidate runs per ROM speed agree exactly. All 600 states match the
expected baseline values for ten positions and velocities, complete OAM shadow, HDMA table and
phase. State sequence SHA-256 is unchanged:
`0bad2bb9b559eb75c14a74746e26f6122a74175e2d3291d8deb1742b5576fd1d`.
All four final screenshots also match the baseline exactly, RGB SHA-256
`31f30fb3c18a97acbb3e58b3b7d8341e3289865420afda2a34fff77933192b5a`.
Milliseconds use the established 21,477,272 master clocks/second convention.

FastROM now completes the 600 logical updates across **600 physical frames**,
versus 1,200 before. Wait-inclusive average is 357,365.85 master clocks /
16.639257 ms per logical frame. Its maximum update in this window is 332,092
master clocks. SlowROM still spans 1,200 physical frames, averaging 714,732.11
master clocks / 33.278533 ms including waits. These cadence claims cover the
validated 600-update window.

Code size, identical between ROM speeds:

| Category | Baseline bytes | Candidate bytes | Change |
| --- | ---: | ---: | ---: |
| Application C code including shared support | 6,485 | 5,293 | -1,192 |
| Linked runtime code | 3,460 | 3,460 | 0 |
| Total linked code | 9,945 | 8,753 | -1,192 |
| ROM constants | 4,520 | 4,520 | 0 |
| Initialized data | 64 | 64 | 0 |
| Padded ROM | 65,536 | 65,536 | 0 |

The representative `sy[i] += dy[i]` statement shrinks from 35 to 21 static
instructions. In this build the compiler still recalculated the byte or word
index and saved temporary values. The later
[index-retention measurements](loop-index-retention.md) cover keeping those
offsets in X and eligible counters in Y.

## Focused validation only

No `make check` or aggregate runner invocation was performed, as requested.
The registered indexed-operands test executes selected, disabled and forced-general
emission modes. It covers signed bytes, signed-overflow comparisons, unsigned word
ALU operations, scaled union-member arrays, odd-stride record fields, assignment
results, index calls evaluated once, compound RHS calls that mutate the original
index/home, and a near object ending at $7EFFFF. Negative selectors cover constant
subscripts, local arrays, pointer variables, volatile elements and 32-bit values.

Focused existing parts also pass: `arithmetic-regions`, `dpage-access`,
`bank-pointers`, `volatile`, `multidimensional` and `typedef-char`. The scalar-values
semantic and instruction-boundary interrupt tests passed on the initial trial;
the final constant-index refinement restores existing lowering for constants.
An initial arithmetic-regions link failure came from a stale `build/integers.o`;
assembling the current runtime prerequisite and rerunning that part passed.
No unrelated source or test expectation was changed to accommodate failures.

## Reproduce and evidence

```text
cmd.exe /d /c tools\build-compiler.cmd
python tests/check-compiler.py --part indexed-operands
```

Repeat the timing command for FastROM run 2 and SlowROM runs 1/2. Use fresh output
paths. `build/direct-indexed-operands/results.json` combines compiler/source hashes,
size measurements, focused-check statuses, disabled-selector control and all four
candidate measurements. `final-build/` retains source/assembly/map/ROM/log inputs;
`final-logical600/` retains Lua, expected state bytes, logs, screenshots and results.
`control/` retains the exact baseline-versus-disabled assembly comparison.
Earlier `candidate/` and `logical600/` directories retain the initial trial.
The new focused fixture's ROMs/assembly are under `build/compiler-check`.

All changes remain uncommitted in the isolated checkout. The original checkout
was not edited.
