# Shared element addresses

Integer arithmetic on two member operands can share the address of their common
structure element. For example, `(unsigned long)items[i].quantity *
items[i].unit_price` computes `items + i * sizeof(*items)` once and reads fields
at fixed displacements. Nested dotted fields combine their member offsets.
Equivalent indexed/dereferenced and arrow forms can share the same address.

The selector in `src/shared_elements.inc` compares typed address expressions
structurally. Eligible addresses contain scalar/array names, integer literals,
casts and pure arithmetic. Calls, assignments, increments and indirect loads in
address expressions are barriers. Different bases or indices retain separate
computations. Existing fixed memory operands are kept when both fields already
have fixed addresses. This selection is local to one binary expression's member
operands; it does not cache addresses between statements or loop iterations.

The base in X is saved across the first load/cast because sign extension and wide
values use X as their high word. After staging that value, X is restored for the
second field load. Both operands are then consumed by the existing arithmetic
emitter. Word/long arithmetic, signed/unsigned conversions and narrow casts keep
their previous behavior. The widened-word multiply helper is retained when its
existing operand proof applies. Floating fields, comparisons and more complex
operands keep their existing paths. No frame slots or persistent cache are added.

## Matched inventory measurement

The baseline includes scalar compound assignments through direct homes. Both compilers
build the unchanged catalog sample with the same startup, integer runtime and
FastROM layout. Two fresh MesenCE runs each agree exactly, return zero, restore
the stack and retain identical function/helper call counts. Timing begins at
main entry and ends after return; startup/exit cleanup is excluded.

| Metric | Scalar homes | Plus shared elements |
| --- | ---: | ---: |
| Master clocks | 22,826 | 21,282 |
| Microseconds at 21.477272 MHz | 1,062.80 | 990.91 |
| Application code bytes | 437 | 414 |
| All linked code bytes | 1,713 | 1,690 |
| Used non-asset ROM bytes | 1,801 | 1,778 |

This saves another 1,544 master clocks (6.76% elapsed time) and 23 code bytes.
These are master clocks. The measured compiler keeps the original C index.

`build/shared-element-trial/measurements.json` retains source/compiler/ROM hashes,
commands, section sizes, timings and raw profiler records. Its baseline/candidate
subdirectories retain emitted assembly, maps, labels, ROMs, Lua and logs. The
private baseline compiler is `build/shared-element-trial/baseline.exe`.

`tests/check-shared-elements.py` runs five MSVC/Mesen programs covering six/eight/
twelve-byte and larger strides, negative indices, local arrays, nested fields,
affine indices, casts/truncation, arithmetic/bitwise/division/remainder, byte
fields and recursion. Side-effecting calls/indices, distinct bases/indices,
indirect indices, fixed homes and floating fields exercise fallback paths.
Shape checks require one stride calculation and fixed displacements, and retain
`__mul16wide` for widened word products. `--baseline PATH` runs the same source
cases through a saved compiler. The default tests are included in `make check`.

Validation completed: full `make check` passed. Final paired focused tests and
two-run measurements match the final compiler hash. The shared-address changes
remain uncommitted.
