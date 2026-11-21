# Standalone compiler examples

Build each example in the table as a separate program. Each has its own
`main` and checks its own answers. You can run these checks without a console
or input device. On the SNES, pause at `main_exit` and look at register A.
Zero means every check passed. For any other value, find the matching return
code in the source to see what failed.

| Source | Main purpose | Current zicc subset |
| --- | --- | --- |
| `insertion_sort.c` | Array indexing, signed comparisons, nested loops, empty/single-element inputs and duplicate keys | Supported |
| `string_processing.c` | ROM strings, packed byte writes, pointer updates, reversal, empty strings and unsigned bytes | Supported |
| `integer_operations.c` | 16-bit wrapping, signed/unsigned 32-bit arithmetic, variable shifts, division and remainder | Supported |
| `function_calls.c` | Nested calls, recursion, preserved locals, stack arguments and 32-bit returns | Supported |
| `structures_and_tables.c` | Structure members, structure pointers, arrays of structures and initialized ROM tables | Supported |
| `loop_access.c` | Byte and word loops over static RAM, stack, heap and ROM; indexed and pointer traversal; zero terminators and nonzero sentinels | Supported |

The first four examples set up their data at run time. The structures example
starts with a table of items stored in ROM and updates a structure in RAM.

`short` and `long` are used where the integer example needs exactly 16 and 32
bits. The other examples avoid assumptions
about host pointer size or structure padding. No check relies on signed overflow
or shifting a negative value.

Run `make samples` at the repository root to build the ROMs in `build/`, including
the examples above, the separate-file integer and inventory variants, and
the starter template.

To run the loop example in Mesen, use

```text
python tests/check-compiler.py --part loop-access
```

The check leaves a ROM and log in `logs/loop-access-check/`. The sample uses
`for`, `while`, `do ... while`, and a backward `goto`. Return codes 1–12
identify the loop that failed in ROM. Add 20 for static RAM, 40 for stack, or 60 for
heap. Code 80 indicates an allocation failure.
