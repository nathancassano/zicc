# Affine loop address setup

The compiler now uses the known starting index to find the first array cell in some unrolled loops. It can often reach that cell with shifts and additions and keep the address in register X. The cost-based unrolling rules select the same loops.

## Selection and ownership

Pointer arithmetic and function cursor synchronization now reuse the word
constant-multiply selector. Power-of-two strides retain their shifts; other
strides use a bounded shift/add/subtract sequence when the existing selector
accepts its cost, otherwise retaining `__mul16`. The scalar input is evaluated
once, and displacement arithmetic remains modulo the 16-bit near pointer width.

For selected unrolled regions, a single constant assignment in the loop
initializer provides the entry index. Address setup evaluates supported affine
constant subexpressions using that value, without modifying the expression tree
or substituting body reads. Existing function cursors remain reusable. Unknown
subexpressions retain ordinary lowering, and unsupported initializers retain
ordinary address setup.

Fully expanded regions form their address directly in X, removing the cursor
store/reload pair. Runtime groups retain a cursor home because counter setup
uses A before loading X. Frame allocation, parameter homes, initial index stores,
visible index recovery, arithmetic scratch preservation and interrupt contracts
are unchanged.

## Verification and evidence

The existing strength suite includes the unrolling checks. They cover MSVC and
emulator semantics, zero/nonzero/negative starts, unsigned boundaries, visible
indices, runtime tails, byte/word/wide copies and NTSC/PAL interrupt ownership.
An additional negative-start affine subscript case checks `2*j+5`, complete array
contents and the returned index. Assembly assertions require known-entry/direct-X
setup and no stride helper in the four measured constant-span kernels.

The comparison compares retained `check-loop-unroll.py` output
directories and replays their ROMs three times. It keeps the existing input,
call-count, write-count and result assertions, adding entry-to-first-write
latency. That latency includes prologue, setup and loading the first store value;
it is not a per-instruction cost ranking. Complete-call timings include return.
Drivers and kernels are identical separate translation units without LTO,
using the same FastROM/near-pointer runtime.

The comparison refuses an existing output directory, checks workload source
hashes, and retains assembly, linked sizes, ROM hashes and raw emulator logs.

The later [frame/home cleanup](frame-home-cleanup.md) plans expansion before
storage allocation and removes selected unused cursor and induction homes.
