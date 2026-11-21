# Indexed far-byte load trial, 2026-11-07

Using a shorter address calculation to read a byte from another memory bank saved the calculator 10,760 master clocks and 201 bytes of code. The trial used the baseline with the assembly memory routines already integrated. The main compiler later adopted the change with its newer console formatter and HiROM allocator. [Integration report](bank-cost-integration.md)

## Measured result

Both calculator forms improve 644064 -> 633304 FastROM master clocks, saving
10760 (1.67%), with total STARTUP+CODE falling 14974 -> 14773 bytes (-201).
The calculator remains 7.97% above the historical 586538-clock pre-bank result,
down from 9.81%. This is the current ABI baseline versus one compiler change;
runtime, input, C sources and parser work are matched.

| Function | Exclusive clocks before / after | Bytes before / after | Executed instructions before / after | Executed push/pull instructions before / after |
|---|---:|---:|---:|---:|
| decimal__match | 25616 / 16864 | 243 / 159 | 968 / 632 | 240 / 192 |
| decimal__render | 10680 / 8592 | 942 / 825 | 428 / 343 | 58 / 46 |
| __ieee_parse | unchanged instructions | 3543 / 3543 | 4829 / 4829 | 417 / 417 |

`decimal__match` saves 8752 exclusive clocks (34.17%). It still executes eight
calls, eight calls to tolower, and 24 indexed far-byte loads. Each selected
load loses 14 executed instructions and two stack push/pull instructions in
this workload. Its 48 A-width switches remain; this change optimizes address
calculation rather than byte-width transitions.

Rendering saves 2088 clocks; its generic variable-index far reads qualify too.
The parser's constant-offset reads retain their existing lowering. Small
40/80-clock profile shifts in other functions reflect refresh placement;
the whole-workload saving is 10760 clocks, rather than the sum of only the two
largest exclusive improvements. Calculator calls and output are unchanged.
Console VBlank waiting is unchanged in this matched trial.

Separate-TU/original strings and structures have identical ROM hashes, clocks,
call counts and hardware-product counts before and after. Their loop/private
entry selectors already handle these loads independently.

## Selection and ownership

`src/far.inc` recognizes a far byte dereference through addition of a variable
word-sized integer displacement. Signed and unsigned word indexes are accepted;
long indexes, constant indexes, scaled word/struct accesses, subtraction forms,
stores, and compound/post-increment lvalues retain their previous paths.
The named-ROM-object selector still runs first. There are no function names,
literal contents, object-bank assumptions or calculator-specific cases in the
new selector. `--no-strength-reduction` disables it for differential testing.

The sequence evaluates the far base first and pushes its four-byte value, then
evaluates the index using the original frame Y. This preserves the base through
calls or nested far loads in the index. It transfers the word index to X,
pops the base into $E0-$E3, saves Y, copies the index to Y, and issues one A8
`LDA [__arith_lhs],Y`. It restores A16 and Y and applies the existing char
sign/zero-extension code. Stack-leaf bias is updated for the temporary base
pushes. D and DBR never change. X/flags and arithmetic scratch retain their
existing caller-clobbered contracts; interrupts preserve the scratch they write.

Long-indirect indexed addressing carries the low-word sum into the bank. A
negative signed word is represented in Y modulo 65536, so the selector first
decrements the staged bank word. Thus a signed -1 becomes base-65536+65535;
unsigned 65535 remains base+65535. Only the low bank byte is consumed by the
hardware, preserving modulo-24-bit address arithmetic, including bank $00/$FF
wraps. The base and index are each evaluated once, and Y is borrowed only
after both evaluations complete.

The first trial also selected constant offsets. It improved the calculator to
633752 clocks but added 488 exclusive clocks to parsing in that profile. The
existing constant-offset path is already cheaper, so the final trial excludes
integer constants. Initial trial ROMs/assembly/profiles remain under
`build/bank-costs/indexed-after/`; final results use `indexed-final/`.

## Validation

The expanded `tests/check-bank-pointers.py` runs on NTSC and PAL as part of the
existing compiler suite. It covers signed -32768/-1/32767, unsigned 65535,
physical bank crossings, both ends of the 24-bit bank range, signed byte
extension, nested indexed loads and side-effecting base/index calls. It checks
that each side effect runs exactly once and that long/constant indexes stay
on the existing paths. The same corrected C fixture passes with the frozen
baseline compiler and with the final compiler's strength reduction disabled.

`tests/interrupt_scratch.c` now executes a negative indexed far-byte read inside
the COP handler, validating its result through the existing interrupt count
assertions. Its two DP words fit the already expected scratch preservation set.
NTSC/PAL tests retain all four incoming A/X width combinations, registers,
Y/D/DBR, stack/status and scratch sentinels.

The supplemental interrupt check checks the foreground
load itself. It traverses 32000 dynamically indexed bytes spanning $7E/$7F with
real hardware IRQ/NMI enabled, verifies the final sum, and requires an actual
interrupt return into the instructions between PHY and PLY. Every interrupt
checks all $E0-$FF words and saved registers/frame/status. Results:

| Region | Interrupt entries and returns | Interrupts while Y borrowed | Nested NMI in IRQ |
|---|---:|---:|---:|
| NTSC | 181 | 23 | 1 |
| PAL | 152 | 19 | 1 |

The probe adds labels to the generated assembly only; it does not change the
generated instructions. Its two region processes run serially and independently
of the normal shared verification queue.

Full `make check` passed 27/27 suites and 76/76 jobs, including all 200873
arithmetic cases, with the hardware-thread default of 20 workers in 385.15
seconds. Evidence: `build/check/20261107T043908.681646Z/summary.json`.
Compiler SHA256: `50e3d1949c72d659368a9f160d231180cf2b78c0714712d1981ea766540b2619`.
The compiler, sources and registered tests remain identical to the frozen
candidate used for measurement and verification.

An initial wrap test incorrectly compared two open-bus reads at $00:2000.
The probe returned its failure code 27. The fixture was corrected to wrap to
mapped WRAM $00:0080, which is explicitly seeded. That corrected fixture passes
baseline, disabled and selected paths. No failing semantic case was retried
without a change. One measurement worker failed creating its directory with
Windows access denied before execution; its log is retained and an isolated
rerun agrees with the other repetition.

## Evidence and reproduction

`build/indexed-far-loads/` contains frozen baseline/candidate compiler binaries,
runtime objects, generated assembly, source/test hashes, per-PC traces,
boundary differential results, interrupt evidence and `comparison.json`.
`build/bank-costs/indexed-before/` and `indexed-final/` each retain all six sample
builds and twelve execution-checked measurements. Source hashes, actual parser
call counts, hardware counts and ROM hashes are asserted by
the profiler. Controls must be byte-identical. No C or
runtime-library source changes are included in the measured optimization.

The stock sample harness times calculator from first printf to second printf
return, and starts the profiler slightly earlier. This start difference is
identical for the two current compiler builds. Function metrics use exclusive
rows and instruction PCs within exact generated function extents, avoiding
double counting the strtod wrapper's tail-called parser body.

Reproduce the final builds after `make all smoke`:

```text
python tests/check-bank-pointers.py
python tests/check-interrupt-scratch.py
make check
```

Use fresh evidence paths when reproducing, and retain the frozen baseline rather
than rebuilding it with the candidate compiler. The generic baseline driver and
kernels are separate translation units without LTO. Existing full arithmetic
vectors, queue boundaries, assertions and worker defaults are untouched.
