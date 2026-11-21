# Direct scalar-home compound updates

For an update such as `total += amount`, the compiler can write directly to a local or global variable. If the program never uses the result of a wide assignment as an expression, there is no need to save its low word or reload the result.

For side-effect-free RHS expressions, same-width word/long `+=`, `-=`, `&=`, `|=`
and `^=` evaluate the RHS and combine it with the fixed home. Wide addition carries
from the low store into the high update. Subtraction stages the RHS and propagates
borrow in the original operand order. Used wide results restore A low/X high.

RHS C calls, assignments and increments retain the established snapshot-before-RHS
order. Byte, pointer, floating, widening and other compound operations also use
the direct home store with the existing expression/conversion machinery. No
purity assumptions about user functions are needed. Scalar-only selection excludes
member/dereference destinations; their existing single-evaluation paths remain.
Statements and `for` step expressions discard results explicitly. Existing
strength-reduction handling and division-cache invalidation still run.

In `inventory_value`, after the multiply the new code is:

```asm
jsr .loword(__mul32)
clc
adc a:$0005,y
sta a:$0005,y
txa
adc a:$0007,y
sta a:$0007,y
```

The two independent `items + i*8` calculations and constant-zero initialization
remain unchanged.

| Unchanged catalog sample | Before | After |
| --- | ---: | ---: |
| Main entry through return, master clocks | 25,638 | 22,826 |
| Microseconds at 21.477272 MHz | 1,193.73 | 1,062.80 |
| Application code bytes | 479 | 437 |
| All linked code bytes | 1,755 | 1,713 |
| Used non-asset ROM bytes | 1,843 | 1,801 |

This is 2,812 fewer master clocks (10.97% less elapsed time), with 42 fewer code
bytes. Existing branch relaxation also benefits from the smaller body. Same
source, startup, integer runtime and FastROM layout; two fresh MesenCE runs per
compiler agree exactly, return zero and balance the stack. Function/helper call
counts match. Startup/exit cleanup is excluded. These are master clocks, not
CPU instruction cycles.

Evidence: `build/scalar-home-trial/measurements.json` combines source/compiler/ROM
hashes, commands, section sizes, profiler records and timings. Baseline/candidate
subdirectories retain assembly, maps, labels, ROMs, Lua and logs. The private
baseline compiler is `build/scalar-home-trial/baseline.exe`.

`tests/check-scalar-homes.py` runs five MSVC/Mesen source cases covering word/long
boundaries, used and discarded results, aliased RHS calls, byte/float/pointer and
widening fallbacks, recursion and loop steps. `--baseline PATH` additionally runs
the same cases through a saved compiler. A mixed integer/float compound-update
case now checks the supported conversion fallback. It checks the direct carry/store shape
and is included in `make check`. The full-suite log is
`build/scalar-home-trial/check.log`.

Validation completed: full `make check` passed. The final focused paired run
and two-run inventory measurements match the final compiler hash. Changes remain
uncommitted.
