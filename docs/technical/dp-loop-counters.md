# Locally saved direct-page loop counters

For a loop such as `for (i=start; i<bound; ++i)`, zicc can count how many
iterations are left using a two-byte counter at $0000-$0001. The compiler
owns those bytes and puts them back the way it found them. The linker keeps
C objects out of that space. The null near pointer and register D both stay zero.

After the original entry condition succeeds, the borrowing region uses
`PEI ($00)` to preserve the incoming word and stores `bound-i` there. Its tail
uses a word `DEC z:$0000` and a zero branch. A single cleanup restores the old
word with `PLA; STA z:$0000`. Empty/negative ranges bypass the save and restore.
Each active region adds two stack bytes. Nested regions, recursive callees and
interrupt-handler regions obey the same ownership rule. Handler-wide scratch
preservation remains restricted to the arithmetic workspace; it does not acquire
a separate DP-zero save. The integer runtime, linker and public ABI are unchanged.

Selection is structural and independent of function names, dimensions and data
types in the body. The index must be a private, non-escaped 16-bit int, its update
must be `++` or `+=1`, and the comparison must be a word `<` against an integer
constant or a private invariant word home. Calls are allowed: all generated
borrowers preserve the word locally. Modified or escaped bounds/indices, other
step/condition forms, and return-containing regions keep ordinary lowering.
Older specialized loop emitters may retain their existing register counters.
With DP-home promotion active, loops with an initializer and an estimated trip
count of at most three skip borrowing $0000: their existing DP step/test avoids
the save/setup/restore overhead.

If the body needs the C index, its home receives the original updates. Affine
address uses already replaced by running pointers do not require those updates.
An index used only after the loop is reconstructed as `bound - remaining` before
restoring the borrowed word. This also handles early `break`; `continue` reaches
the ordinary step/countdown tail. Regions containing `return` are excluded so
every selected exit reaches its local restore. Full 65535-iteration ranges fit
the word countdown. `--no-dp-counters` disables this selection; disabling strength
reduction also leaves it off.

Unsigned word loops of the form `do { … } while (--count)` or
`while (--count != 0)` can borrow the same word when the body has no
reference to the private counter. The initial value is copied directly,
so zero starts a full 65,536-trip countdown. A break leaves the remaining
count available for recovery. A continue reaches the decrement before the
next iteration. A body that refers to the counter or contains a return
uses the ordinary lowering. The arithmetic-region test exercises wraparound,
nested calls, break, continue, and an observed counter.

Signed word loops with `i > bound` or `i >= bound` and a unit
decrement can use `i - bound` or `i - bound + 1` as the initial
count. The original signed comparison remains at entry. The
inclusive minimum bound tests for continuation when the count
expires so target wraparound is preserved. Fixed-array constant
word fills can also count a strict or inclusive upper bound
while keeping their byte displacement in X. Their inclusive
maximum bound uses the corresponding continuation check.

## Verification and performance

`tests/check-dp-counters.py` compares enabled/disabled execution with MSVC
references for breaks, continues, nested regions, dynamic and short ranges,
signed/unsigned 65535-iteration boundaries, recursive callees, stack arguments
and wide results. It also checks conservative fallbacks. An independent assembly
probe seeds both bytes, checks caller Y and return values, and re-enters borrowing
callees while an outer counter is live.

Real NTSC/PAL IRQ, NMI, BRK and COP delivery checks the outer word, full native
register state and stack balance in all four M/X width combinations. A second
fixture enables NMI inside a live IRQ loop: the NMI loop borrows the IRQ's count,
which itself borrowed the interrupted caller's count. Every owner restores its
own saved word. No additional handler-wide DP-zero preservation is inserted.

The separately compiled assignment kernels retain the previous opaque driver,
argument/call/write assertions and three repeated runs. The disabled kernel and
driver assembly match the saved pre-change compiler byte for byte. Measured
complete-call master clocks are:

| Traversal | Previous optimized version | Saved DP counter |
|---|---:|---:|
| Across row | 3122-3162 | 2876 |
| Down column | 1936-1976 | 1910 |
| Nested rows | 7174-7214 | 6438-6478 |
| Nested columns | 9564 | 9096-9136 |

Borrowing has entry/exit overhead; these figures include it. The previous
archived reduction experiment remains separate and its historical measurements
remain valid. Evidence for this implementation is in `build/dp-counter-check/`,
including full paired C/assembly in `assembly.md`, ROMs, raw logs and hashes.
`build/dp0-loop-change/` retains the pre-change compiler and input manifest.

Final `make check` passed 27/27 suites / 76 jobs in 277.10 seconds with the
hardware-thread default of 20 workers and all 200,873 arithmetic cases. Logs:
`build/check/20261106T140807.965303Z/`. The dedicated DP-counter checks cover
13 semantic/fallback pairs plus eight NTSC/PAL ownership configurations,
including nested NMI-inside-IRQ delivery, recursive callees and wide stack calls.
