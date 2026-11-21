# Low WRAM and bank-$7F runtime storage evaluation

Moving the stack lower gives ordinary variables another 6,912 bytes in RAM
bank $7E. The `__loram` attribute places a variable in the low part of that
bank. This trial kept library buffers in $7E. For the current layout, see
the [target reference](operations.md) and [runtime RAM backfill](runtime-ram-backfill.md).

The original evaluation and measurements are in
`E:/archived-compiler/worktree-low-wram-evaluation.zip` under
`.worktrees/low-wram-evaluation/build/`. They predate later loop optimizations
and the separate verification of the merge into master.

Implementation validation is complete: the hardware-default 20-worker
`make check` run and focused follow-ups cover all 27 logical suites / 76 jobs /
200,873 arithmetic cases. Three legacy fixture assumptions were corrected for
the new layout; unaffected passes were retained. See
`build/wram-verification.json` and the current handoff for the complete evidence.

The initial design evaluation used isolated linker fixtures with the original
high stack and near-WRAM layout. Arithmetic scratch stayed in direct page.

The stack relocation, expanded near RAM range and `__loram` placement constraint are
compatible with DBR=$7E. Moving a symbol to $7F while retaining a DBR-relative
access targets the wrong bank.

## Capacity and stack contract

| Use | Baseline | Evaluated layout | Capacity |
|---|---|---|---:|
| Direct page, including arithmetic scratch | $0000-$00FF | unchanged | 256 bytes, with existing subdivisions |
| Declared hardware stack reservation | $1C00-$1FFF | $0100-$04FF | 1,024 bytes |
| Near RAM available to applications | $7E2000-$7EFFFF | $7E0500-$7EFFFF | 57,344 -> 64,256 bytes |
| `__loram` eligible extent | no attribute | $7E0500-$7E1FFF | 6,912 bytes shared with the near RAM range |
| Space for persistent runtime buffers | shares near RAM | top down in $7F0000-$7FFFFF | at most 65,536 bytes |

The near RAM range gains 6,912 bytes (6.75 KiB). `__loram` does not add another
6,912 bytes: it constrains where objects within that range may reside.
Bank-zero stack addresses and their $7E aliases refer to the same physical WRAM.
Near pointers to stack locals remain valid with DBR=$7E because the new stack
still lies in that mirrored range. MMIO remains explicitly bank-zero/far.

The declared stack size remains 1 KiB, but the effective failure boundary changes.
Today a stack that exceeds the declared reservation can descend into otherwise
unused low RAM. At $04FF, using more than 1 KiB immediately enters direct page.
There is no hardware stack guard. The frontend's 768-byte per-function frame
limit (`src/parser.inc`) does not bound nested calls, recursion, temporary pushes
or interrupt nesting. Account for all of these in a stack high-water validation;
do not infer safety from the existing reservation alone. Native-mode startup must
set S before any stack use, as it already does. Keep DP and stack out of the
allocatable near RAM range using physical addresses, not merely bank numbers.

## Low-RAM placement

`__loram` places static-storage objects in low WRAM. The
[target reference](../operations.md#low-ram-placement) describes the compiler's
placement rules. Examples:

```c
__loram unsigned char dma_table[256];
extern __loram unsigned char dma_table[256];
static __loram unsigned flags;
```

The fixtures check whether each object fits entirely through $7E1FFF. They
include initialized DATA, BSS, alignment gaps and exact-fit boundaries.
Startup clears both WRAM banks. MVN changes DBR, so a copy into $7F must
restore DBR=$7E on exit.

## Runtime inventory and bank-$7F implications

An unchanged calculator build was generated locally through the actual automatic
HiROM builder. Its map reports these linked persistent allocations; these are
sample-specific totals, not a claim that every program links every runtime unit.

| Storage | Bytes in calculator | Baseline access |
|---|---:|---|
| Console tilemap | 4,096 | DMA derives its source bank from the symbol. CPU reads and writes use DBR-relative absolute,X. |
| Console state, including stdout token | 94 | The code uses absolute loads/stores, STZ and read-modify-write instructions. `stdout` is exposed as a near FILE pointer. |
| Decimal digits/output/state | 284 | 200-byte digits, 80-byte output, two 2-byte words. Assembly helpers use near storage addresses and near destination pointers. |
| stdin token and errno | 4 | Public near-addressable C objects. |
| Application buffer | 128 | Application owned; remains ordinary near RAM. |
| Arithmetic work | 32 | Stays at $E0-$FF, per user instruction. |
| Console format pointer | 4 | Direct-page long-indirect addressing operand, not a bulk buffer. |
| Application direct-page pointer | 2 | Application owned; unchanged. |

The large buffers alone account for 4,376 near bytes: console map plus decimal
digit/output arrays. All listed non-DP runtime statics total 4,478 bytes, including
control state and public tokens. Clock
state (4 bytes), clock-rate cache (2 bytes) and malloc's ready flag (2 bytes) are
additional optional runtime allocations, absent from this calculator link.

In the measured build, `dec_format` and `dec_format_spec` return a near
`char *` into the static output. The same near-address restriction applies to
the stream tokens and `errno`. A truncated $7F address dereferences an object
in $7E when DBR is $7E.

The 65816 has long LDA/STA and long indexed-by-X forms, but no equivalent long
form for every existing operation (notably STZ, INC/DEC, LDX/LDY and absolute,Y).
These need appropriate sequences or a deliberately scoped DBR change. Generated
stack-frame accesses also rely on DBR=$7E, so a blanket DBR=$7F switch around a
library routine is unsafe. Preserve entry/exit DBR, D, modes and interrupt
contracts. The encoding fixture demonstrates absolute LDA is 3 bytes and long
LDA is 4; this evaluation makes no runtime timing claim.

Arithmetic scratch remains in direct page. The console's four-byte format cursor
is also an addressing operand for `[console_format_pointer]`; keeping that cursor
in DP is independent of the location of its target buffers. Per-invocation
locals, saved arguments and memcpy's executable stack thunk use the stack.
The ordinary malloc heap uses near memory.

## Bank-$7F allocation fixture

The fixture places objects downward from $800000. For an object of size N
and alignment A, it computes `start = align_down(cursor - N, A)` and uses
that start for the next cursor. A start below $7F0000 reports overflow.
Padding counts toward the occupied extent. See the
[runtime backfill report](runtime-ram-backfill.md) for the integrated allocator.

## Evidence

The WRAM layout check passed ten focused probes. Six completed
link jobs were retained after the full-bank fixture initially hit ca65's limit
on a single `.res` operand; splitting that reservation into two directives fixed
the fixture, and `--resume` reran only that unfinished job.

The probes cover zero low reservation, exact low fit including initialized DATA,
one-byte low BSS/DATA overflows, exact/overflow near capacity, full-bank $7F fit,
individual/cumulative/alignment-induced $7F overflow, descending placement and
absolute versus long load encodings. They retain sources, configs, maps, logs,
binary hashes and tool/input hashes under `build/wram-layout-evaluation/`.
The unchanged calculator build and compiler/source/runtime hashes are retained
under `build/wram-evaluation-baseline/` and its allocation manifest.

These are allocation and encoding results. They do not implement the C attribute,
execute a relocated stack, prove stack headroom or validate relocated runtime
buffers. No compiler/code-generation implementation was changed, so full
`make check` was not run for this evaluation.
