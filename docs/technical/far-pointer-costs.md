# Far-pointer comparisons, updates and call setup, 2026-11-07

A far pointer holds a bank number as well as an address. Comparing two such
pointers, stepping one to the next byte, or passing it to a function can take
several instructions. These trials measured shorter instruction sequences for
those operations on the calculator and string samples.

The trials used the build with cached printf format cursors. The measured
builds used the existing C parsing and decimal code, assembly printf and
arithmetic runtime. The changes later joined main alongside its newer console
and HiROM allocator. The timings below belong to the original builds.
See [the integration report](bank-cost-integration.md).

## Measured changes

All rows use FastROM, identical C sources and runtime inputs, with two matching
execution-checked runs per original/separate-TU form. Separate units have no LTO.

| Incremental trial | Calculator clocks, both forms | Calculator STARTUP+CODE bytes | Separate-TU strings clocks / bytes |
|---|---:|---:|---:|
| Format-cursor baseline | 630010 | 14745 | 15964 / 602 |
| Direct far-pointer comparisons | 625204 | 14673 | 15964 / 602 |
| Plus discarded byte-pointer updates | 618226 | 14137 | 15964 / 602 |
| Plus argument staging and cleanup | 617238 | 14133 | 15404 / 588 |

Comparison lowering saves 4806 calculator clocks; discarded updates save another
6978; argument staging/cleanup save another 988. Together this is 12772 clocks
(-2.03%) and 612 code bytes. Separate-TU strings save 560 clocks (-3.51%) and
14 bytes. Separate-TU structures improve 15702 / 1939 -> 15690 / 1938.
Original strings and structures are byte-identical to the baseline: their private
entries already use independent call/lowering paths. ROM files remain 32768 bytes.

Historical pre-bank clocks were calculator 586538, strings 13122 and structures
13884. Current gaps are 5.23%, 17.39% for separate-TU strings and 13.01% for
separate-TU structures. This trial does not remove the general ABI/bank costs.

## 1. Strtod pointer and comparison work

`strtod` in `runtime/io.s` jumps to `__ieee_parse`, implemented in
`runtime/ieee32/decimal.c` and compiled by zicc. Improving its emitted pointer
operations therefore helps the library without rewriting its parsing algorithm.

Simple far-pointer scalar homes now compare their bank words first, and their
low words only if banks match. All six relations use unsigned address ordering.
Qualifier-only far casts can expose these homes; conversions, calls, indirect
reads and other complex operands retain the helper path. No scratch or stack
staging is needed for the selected comparison, and Y/D/DBR are unchanged.

Discarded prefix/postfix updates of byte-stride far pointer variables now update
the low word directly and repair the bank only on a carry/borrow. Frame homes,
ordinary globals and direct-page globals use their normal addressing. This
selection applies to expression statements and for-loop steps. Used postfix
results, other strides and more complex lvalues retain their existing paths.
Bank repairs mask to eight bits, preserving four-byte pointer values with a zero top byte
and modulo-24-bit wrapping. `--no-strength-reduction` disables these selections.

| Parser metric | Before | Combined candidate |
|---|---:|---:|
| strtod calls | 4 | 4 |
| strtod exclusive clocks | 134796 | 124072 |
| strtod inclusive clocks | 169184 | 156648 |
| __ieee_parse code bytes | 3543 | 3190 |
| __ieee_parse executed instructions | 4829 | 4428 |
| __ieee_parse executed stack operations | 417 | 299 |
| __ieee_parse long-indirect byte reads | 47 | 47 |
| Whole-workload __ucmp32 calls | 103 | 94 |

The trace requires nine actual inline parser comparisons: the nine missing helper
calls are replaced with executed comparison instructions. The parser consumes
the same bytes, makes the same requested number/parser calls and produces the
same checked output. Decimal matching remains 632 executed instructions and
24 long-indirect reads; the earlier indexed-load optimization is intact.

Raw profiler rows use a wider window than the calculator timer (which begins
at the first printf). Their sums are 630176 and 617358 versus timed 630010 and
617238. Caller setup and opcode-boundary accounting differ at the window edges;
use the directly timed whole-workload difference, not a sum of selected exclusive
rows. Refresh also moves small 40/80-clock amounts among functions.

## 2. Generic argument setup and equality

The public ABI remains near-$7E / four-byte-padded far pointers, word arguments
in the existing X/A positions, and other arguments on the stack. Unknown banks
still use the crossing-capable public kernels. No LTO, inlining, public signature
changes or caller bank guesses are introduced.

The retained caller changes are:

* Strip only representation-preserving pointer casts when selecting immediate
  argument pushes. Far string constants hidden by qualifier casts can use two
  PEA instructions, retaining linker bank/low-word relocations.
* Push a simple far scalar home's high and low words directly, avoiding the
  intermediate TAX. Other expressions retain their normal evaluation.
* For the existing proven-non-NULL near-object promotion, push bank $7E with PEA
  rather than materializing it in X first. Nullable pointer variables still use
  the general NULL-preserving conversion, including direct-page object cases.
* For a word result and at least six stack-argument bytes, keep A in caller-
  clobbered X while TSC/ADC/TCS removes the arguments, then restore A with TXA.
  Smaller cleanups retain their pulls. Wide results retain their prior cleanup.
  TXA supplies full-word N/Z, so the existing flag reuse can also omit CMP #0.

Argument evaluation order and pushed values remain unchanged. No live caller
value is moved into arithmetic scratch. Side-effecting/converting arguments
retain their general evaluation, and frame Y remains available while arguments
are formed. Stack-leaf bias is tracked for the direct home pushes.

| Separate-TU string metric | Before | Candidate |
|---|---:|---:|
| Driver code bytes | 372 | 358 |
| Driver executed instructions | 171 | 157 |
| Driver executed stack operations, including PEA | 50 | 34 |
| Actual driver JSR calls | 11 | 11 |
| Equality code bytes | 55 | 55 |
| Equality executed instructions | 206 | 206 |
| Equality far-byte reads/comparisons | 50 | 50 |
| Copy code bytes / executed instructions | 37 / 108 | 37 / 108 |
| Copy far-byte reads | 14 | 14 |

The four equality calls, three copies and four reversals retain their inputs and
results. The equality body is unchanged; its caller setup/cleanup accounts for
the speed gain. Full-address carries and Y wrapping remain intact. Public-kernel
instruction counts and memory-read counts show that this result comes from lower
overhead rather than removed string work.

### Rejected equality-body experiment

The stack-page trial tests an assembly prototype that points D
at the existing stack arguments instead of copying the far bases into $E0/$E4.
It saves initial setup but pays an extra cycle per long-indirect byte access
because D is unaligned. Actual calls/returns, all 630 data reads, results,
stack, Y/D/DBR and crossing data are checked. Repeated measurements agree:

| String length | Generic clocks / CPU cycles | Stack-D clocks / CPU cycles |
|---|---:|---:|
| 0 | 598 / 83 | 478 / 67 |
| 1 | 700 / 104 | 592 / 90 |
| 10, crossing a physical bank | 2018 / 293 | 2058 / 297 |
| 300 | 44478 / 6383 | 48038 / 6967 |

The cycle model is 18 saved fixed cycles minus one cycle for each of 2*(n+1)
byte reads. It loses steady-state throughput; the 300-byte case is 8.0% slower
in master clocks. This prototype is rejected and never emitted by the compiler.
It has focused sample/ABI validation only, not full general-kernel verification.
Reducing the public argument width or assuming a bank span without proof would
change the supported contract, so neither is used to improve this benchmark.

## Validation and retained failures

`tests/check-far-pointer-costs.py`, included in the existing compiler suite,
compiles the driver and kernels as separate units. Selected and disabled paths
pass on NTSC/PAL. A focused run also passes with the saved format-cursor baseline compiler.
The Python-derived table checks six relations for 256 pairs spanning banks $00,
$7E/$7F/$80 and $FF, low-word boundaries and NULL. Updates cover carries, borrows,
24-bit wraps, global/DP/frame homes, loop steps and used postfix results. Caller
checks cover nullable conversions, qualifier casts, near/direct-page objects,
high-bit word results, six/eight-byte cleanup and side-effecting operands.

The coverage check independently hooks the retained ROMs. Each
selected/disabled/baseline run must execute and complete 257 comparison calls;
16 each of increment, decrement, used-postfix, loop, global update and global
comparison calls; both side-effect calls; and the argument/byte probes. This
distinguishes correct expected values from work accidentally disappearing.

The first full run completed 26/27 suites: the unoptimized NTSC far-loop interrupt
test hit its 60-second wall-clock limit under load. It reported no assertion
failure. Its exact ROM passed in isolation with 2922 interrupts and a nested NMI.
The failed run (`build/check/20261107T052347.163500Z/`) and ROM/log/source snapshot
are retained. Only that unoptimized test's wall allowance changes to 120 seconds,
its subprocess allowance to 150, and its containing test allowance to 600. The
optimized allowances, target workload, assertions and shared queue are unchanged.

Full `make check` after the deadline adjustment passed 27/27 suites / 76 jobs
in 390.95 seconds with the default 20 workers. Evidence:
`build/check/20261107T053213.980116Z/summary.json`. The failed and passing
unoptimized ROM hashes are identical, and measured compiler/source inputs
remain frozen. Compiler SHA256: `ef6e4166a19fe5a9803468b5b02c3006371cb00c118ad000cc50fc32251b677a`.
The machine's hardware-thread default is retained, including all 200873 arithmetic
cases and existing 50 batch boundaries. No nested arithmetic worker pool is added.

The first new fixture attempted a direct-page aggregate initializer, which the
compiler rejects. It was changed to ordinary runtime initialization before
measurements; all three compiler modes pass the corrected identical source.

## Evidence

`build/far-pointer-costs/` retains the frozen baseline, intermediate compiler/
decimal artifacts, final candidate, verification-only deadline changes, SHA256
inventories, raw PC traces, comparison summary, differential/coverage reports,
timeout and exact-ROM replay evidence, and the rejected stack-D experiment.
`build/bank-costs/far-before/`, `far-compare/`, `far-updates/` and `far-calls/`
retain all 24 sample builds and 48 checked repeated executions, their commands,
assembly, maps, debug symbols, source/compiler/runtime hashes and ROMs.

The profiling run asserts paired measurements, source hashes,
runtime call/hardware counts and original-form control-ROM identity. It groups
instruction PCs by exact generated function extent, handles strtod's tail jump,
and counts executed inline bank/low comparisons in the parser. Library C source,
assembly runtime objects and input data are matched across all retained trials.

Reproduce with the frozen baseline compiler/runtime retained and fresh paths:

```text
make all smoke
python tests/check-far-pointer-costs.py --baseline build/far-pointer-costs/baseline-inputs/zicc.exe
make check
```
