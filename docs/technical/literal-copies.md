# Known-literal strcpy

For `strcpy(buffer, "Hi")`, zicc knows exactly how many bytes to copy. They
are the two letters and the terminating zero. It can copy that many bytes
directly when the program uses the standard near-destination, far-source
`strcpy` declaration. A cast of the literal to a far pointer also works if
it preserves the address. Copying stops at the first zero, even in a literal
with text after it. Other sources, incompatible declarations, volatile
parameters and a function defined in the same C file keep their ordinary calls.

The destination is evaluated once and saved on the invocation stack. Every path
returns that original near pointer. Nested copies and side-effecting destinations
retain ordinary expression evaluation. No runtime library changes are required.

## Selection and banks

The aggregate and literal paths share the existing weighted policy: one code
byte costs eight nominal CPU cycles, with a 128-byte inline expansion bound.
Literal candidates account for their own addressing/setup costs. Inline uses
12N+6 cycles / 8N+4 body bytes; guarded MVN uses 7N+32 cycles / 36 body bytes,
excluding common destination evaluation and result staging. The latter includes
the cold fallback's code size. Branch relaxation may shorten the final code.
Under this policy copies of one through four bytes inline; larger copies use
MVN. `--no-copy-selection` retains the ordinary library call for these literals,
while keeping its existing aggregate inline-reference behavior.

Inline copies use A8 long-address source loads and exact byte stores, explicitly
incrementing X16 between bytes. They neither overread nor overwrite a padding
byte. Full source addresses carry across banks; the near destination cursor
wraps in bank $7E just as in the library routine.

MVN saves/restores Y and DBR and copies exactly N bytes into bank $7E. Because
MVN does not carry its source bank, a guard checks the linked source low word
against 65537-N. A crossing literal falls back to the existing far-source routine,
reusing the already evaluated destination. The result and register preservation
remain invocation-owned throughout calls and interrupts. The frontend's existing
prohibition on ordinary calls in interrupt handlers is unchanged.

## Validation and measurements

`tests/check-literal-copies.py` is part of the compiler suite. It checks empty,
odd/even and high-byte literals, embedded NULs, return values, nested calls,
single-evaluation destinations, dynamic fallback and user-defined strcpy.
The selected/reference variants use the same C semantics. Boundary fixtures
place literals across $7E:FFFF/$7F:0000, testing both inline address carry and
guarded MVN fallback; normal fixtures test near-destination wrapping.

NTSC/PAL runs require actual IRQ and NMI interruption of the MVN. Separate ROMs
insert BRK/COP before every instruction of the inline/MVN/fallback functions.
Checks cover A/X/Y/D/DBR/status/stack and all arithmetic workspace words, plus
the transferred byte when Mesen reports a resumed MVN at a repeated byte fetch.
Aggregate-copy selection and interrupt tests also pass with the shared policy.

For Dhrystone's 3,000 iterations, repeated PAL profiles are identical:

| Build | Before master clocks | After | Reduction |
|---|---:|---:|---:|
| FastROM | 97,164,940 | 87,662,296 | 9.78% |
| SlowROM | 112,987,016 | 101,822,640 | 9.88% |

All original non-strcpy call, loop, array/global write, record, hardware-arithmetic
and record-copy counts remain unchanged. The timed loop now executes 3,000
31-byte MVNs and zero strcpy calls. The C sources and linked runtime hashes
match the pre-change baseline; translation units remain separate without LTO.
This compares normal optimized complete benchmarks, not opaque-kernel throughput.
CODE grows 95 bytes; ROM padding keeps the image at 32,768 bytes.

Two native runs per region reproduce NTSC 246 ticks / 4,100 ms / 731
Dhrystones per second, and PAL 206 ticks / 4,120 ms / 728. Earlier reports were
661 and 655 respectively. Complete profiles, source/compiler/runtime/ROM hashes,
console reports and verified screenshots are under `build/literal-copy-trial/`.

Final `make check CHECK_OUTPUT=build/literal-copy-trial/full-check` passed all
27 suites / 76 jobs with the hardware-thread default of 20 workers, preserving
all 200,873 arithmetic cases. The four affected preflight suites also passed.
