# Fixed multidimensional arrays

Fixed dimensions are preserved as nested array types. `int a[3][5]` occupies
30 bytes on this target, and `a[i][j]` addresses `a + i*10 + j*2` in byte units.
Each index is evaluated once for reads, writes, compound updates and increments.
Three or more dimensions apply the same rule recursively.

```c
typedef int Row[5];
typedef Row Matrix[3];
int read(int a[][5], int i, int j) { return a[i][j]; }
int also_read(Matrix a, int i, int j) { return a[i][j]; }
int via_pointer(int (*a)[5], int i, int j) { return a[i][j]; }
```

Only the outer parameter dimension is adjusted to a near pointer. All three
functions above receive a pointer to a five-element row. `int **` has a different
type and representation. `a[i]` decays to an element pointer; `&a[i]` points to a
whole row, and incrementing that pointer advances ten bytes. `&a` points to the
whole matrix. Pointer subtraction produces element counts, including row counts.
`sizeof(a)`, `sizeof(a[i])` and `sizeof(a[i][j])` retain their respective shapes
for actual array objects; `sizeof` on an adjusted parameter is pointer size.

File/block typedefs, local/global arrays, structure members, arrays of pointers,
and arrays of structures use the same type representation. Const qualification
of an array typedef or containing structure reaches its elements. Const ROM
initializers accept nested braces and zero-fill omitted elements. Existing
restrictions on local aggregate initialization, writable initialized globals,
string initializers and designated initializers remain.

Dimensions must be positive integer constant expressions, at most 16384 each.
Only an outer parameter dimension may be omitted. Oversized products saturate
before size validation, preventing nested products from wrapping. Existing
65534-byte object/layout and 768-byte function-frame limits still apply; the
linker also enforces the smaller physical RAM regions. VLAs are unsupported.

## Verification and loop assembly

`tests/multidimensional_cases.c` executes constant/variable row and column
accesses, all-variable 3D indexing, scalar widths, structure elements/members,
typedef and explicit parameters, row/whole-array addresses, row stepping and
subtraction, nested initializers, and indices with calls/postincrements. It also
checks the complete results of row, column, nested-row and nested-column loops.
`tests/check-multidimensional.py` runs the fixture on SNES and under MSVC and
checks malformed dimensions, incompatible shapes and const violations. It runs
inside the existing compiler suite in the shared `make check` queue.

The loop bodies use only `m[i][j]=value`. The generated assembly is retained in
`build/multidimensional-check/semantics.s`; the same test extracts complete
functions to `build/multidimensional-check/loop-assembly.md`. These are actual
compiler output, including loop conditions, index updates and frame setup.

Eligible loops now hoist invariant row addresses and use running byte pointers.
Straight two-byte assignment loops retain their cursor in X: across-row traversal
advances by two bytes and down-column traversal by ten bytes for these examples.
Nested traversals reset the inner cursor at each outer iteration. More complex
safe regions use frame cursors. See [affine array loops](affine-array-loops.md)
for selection rules, fallback behavior, differential checks and measurements.
