# Supported C library

To use a library function, include its header in your C file. For example,
`#include <stdlib.h>` gives you `malloc` and `free`. The tables below show
which parts of each standard header work on the SNES. The
[ROM builder](rom-allocation.md) adds the library code your program needs.

If you link by hand, put `build/libc-new/libc.a` after your application object
files for allocation, string and memory functions. Make also copies it to
`build/libc.a` and publishes it as `bin/libc.a` in the default build. Other runtime components provide console I/O, parsing and
timing. See [library internals](technical/libc.md) for the link details.

## Pointer and size conventions

- Ordinary pointers address near RAM in bank `$7E`. `__far` pointers can address
  RAM or ROM, including string literals.
- `size_t` is `unsigned int` (16 bits), supplied by `<stddef.h>` and included by
  `<stdlib.h>`, `<string.h>` and `<stdio.h>`.
- The standard memory routines write to near RAM. The entire destination must
  fit in bank `$7E`. A far source can cross a ROM or RAM bank boundary.
- To write to far RAM, use `far_memcpy`, `far_memmove` or `far_memset`. These
  take an `unsigned long` byte count. See [expanded application WRAM](operations.md#expanded-application-wram).

## `<stdlib.h>`

| Function | Supported behavior |
| --- | --- |
| `malloc` | Allocate uninitialized, two-byte-aligned near RAM. Return null on failure or a zero-size request. |
| `calloc` | Check the count × size product against `size_t`, then allocate and zero the requested bytes. Return null on failure or a zero-size request. |
| `realloc` | Resize a near allocation. A null input allocates, and size zero frees and returns null. Shrinking can retain the block. Growth allocates and copies before freeing, preserving the original on failure. |
| `free` | Release a live near allocation. A null argument is accepted. |
| `qsort` | Sort a near-RAM array in place using insertion sort. |
| `bsearch` | Search a sorted near-RAM array using binary search. Return a near pointer to a matching element or null. |
| `atoi`, `atol` | Parse signed decimal text from RAM or ROM into a 16-bit `int` or 32-bit `long`, respectively. |
| `strtol`, `strtoul` | Parse signed or unsigned 32-bit integers from RAM or ROM. Accept base 0 or 2–36. Overflow saturates and sets `errno` to `ERANGE`. |
| `strtoll`, `strtoull` | Parse signed or unsigned 64-bit integers with base 0 or 2–36. Overflow saturates and sets `errno` to `ERANGE`. |
| `strtod`, `strtold` | Parse decimal or hexadecimal RAM/ROM text, special values and subnormals into the selected floating format. Range errors set `errno` to `ERANGE`. |
| `abs`, `labs` | Return the absolute value of a 16-bit `int` or 32-bit `long`. The most negative input has no representable result. |
| `abort` | Restore the startup stack and enter the halt loop with status zero in A. |
| `exit`, `quick_exit`, `_Exit` | Restore the startup stack and enter the halt loop with the given status in A. |

The heap occupies near RAM after linked static storage through `$7E:FFFF`.
Linked console, decimal and optional frame-counter buffers use separate bank
`$7F` storage. Stream tokens, `errno` and small runtime control words remain
near. Allocation is foreground-only. Passing an invalid allocation to
`free` or `realloc` has undefined behavior.

Sort and search comparators take two near `const void *` arguments and return
a signed `int`. The comparator may reside in another ROM bank.
The `strto*` functions accept a near pointer to a far-pointer object for
the optional end position. Pass null to omit it. Floating decimal parsing
and formatting share buffers and are non-reentrant.
The termination functions skip handlers and stream cleanup.
`EXIT_SUCCESS` is 0 and `EXIT_FAILURE` is 1.

## `<assert.h>`

| Name | Supported behavior |
| --- | --- |
| `assert` | Evaluates its operand once when enabled. With `NDEBUG` defined, the operand is unevaluated. Reinclude the header after changing `NDEBUG` to update the macro. |
| `__zicc_assert_fail` | Records the expression and filename as far string pointers in `__assert_expression` and `__assert_file`, and the line as a 32-bit value in `__assert_line`, then calls `abort`. The debugger can inspect these values even in a ROM without a console. |

## `<stdarg.h>`

| Macro | Supported behavior |
| --- | --- |
| `va_start` | Initialize a near stack cursor from the last named parameter. |
| `va_arg` | Read the next argument with the requested promoted type and advance the cursor. |
| `va_copy` | Copy the cursor for an independent traversal. |
| `va_end` | End traversal and clear the cursor. |

Named arguments retain their ordinary register or stack locations. Unnamed
scalar arguments occupy consecutive two-, four- or eight-byte slots. Near pointers use
two bytes. Far data pointers and function pointers use four. Floating
arguments use the selected `double` ABI. Aggregate arguments occupy their full stack-copy size.
A cursor remains valid while its variadic function is active.

## `<string.h>`

| Function | Supported behavior |
| --- | --- |
| `memcpy` | Copy exactly the requested bytes from RAM or ROM to a nonoverlapping near destination. |
| `memmove` | Copy exactly the requested bytes to a near destination, allowing overlap. |
| `memset` | Fill near RAM with the low byte of the value. |
| `memcmp` | Compare the requested bytes as unsigned values. |
| `memchr` | Find the first matching byte within the requested span. |
| `strcpy` | Copy a string and its terminator to a near destination. |
| `strncpy` | Copy up to the specified bound and pad a short source with zero bytes. |
| `strcat` | Append a string and its terminator to a near destination. |
| `strncat` | Append at most the specified number of source bytes and add a terminator. |
| `strcmp` | Compare strings as unsigned bytes through the first difference or terminator. Return -1, 0 or 1. |
| `strncmp` | Compare strings with the specified byte limit. |
| `strlen` | Count the bytes before the terminator. |
| `strchr`, `strrchr` | Find the first or last occurrence of a byte in a string, including its terminator. |
| `strspn`, `strcspn` | Count the initial bytes drawn from or excluded by a byte set, respectively. |
| `strpbrk` | Find the first string byte in a supplied set. |
| `strstr` | Find the first occurrence of a substring. |
| `strtok` | Split a writable near string in place. A null first argument resumes the shared cursor. Delimiters may change between calls. |
| `strcoll` | Compare strings using ASCII C-locale order, equivalent to `strcmp`. |
| `strxfrm` | Copy the C-locale identity transform and return the full source length. Zero capacity permits a null destination. Insufficient capacity can leave the result unterminated. |

Copy, concatenation and fill functions return the original destination.
Destinations need sufficient space, and only `memmove` supports overlapping
copies. Zero-count memory operations access neither range. Read-only sources
may cross banks. Search functions return far pointers into their inputs or
null on a miss. `strtok` returns near pointers and uses one non-reentrant
cursor. See the public header for exact parameter and return types.

## `<stdio.h>`

This header provides an opaque `FILE` type, `stdin`, `stdout` and `EOF` (-1).
The streams represent the bundled input fixture and text console; there is no
general file system or file-opening API.

| Function | Supported behavior |
| --- | --- |
| `int printf(const char * __far format, ...)` | Write formatted text to the console; return the emitted character count or -1 on a formatting error |
| `int sprintf(char *destination, const char * __far format, ...)` | Format into near RAM and append a terminator; the caller supplies enough storage |
| `int snprintf(char *destination, size_t capacity, const char * __far format, ...)` | Store at most `capacity-1` characters and terminate when capacity is nonzero; return the length that would have been written |
| `int fflush(FILE *stream)` | Wait for pending console presentation; accept `stdout` or a null pointer; return 0 on success, -1 for an invalid stream |
| `char *fgets(char *buffer, int capacity, FILE *stream)` | Replay the fixed input fixture through `stdin`, copying at most `capacity - 1` bytes and adding a terminator |

### Formatted output

- Supported conversions include `%%`, `%d`/`%i`, `%u`, `%ld`/`%li`,
  `%lu`, `%x`/`%X`, `%lx`/`%lX`, `%lld`/`%lli`, `%llu`, `%llx`/`%llX`, the corresponding
  `j`-length conversions, and `%c`.
- `%s` takes a near RAM string; `%S` takes a far string, including a ROM literal.
  Format strings themselves are far.
- Decimal widths through 999, `-`/`0` flags, integer precision and string precision
  are supported. Integer precision overrides zero padding; string precision
  limits bytes read.
- `%f` and `%g` require the floating console build (`CALC=1`). `%g` defaults to six
  significant digits; floating precision ranges from 0 through 32.
- Unsupported formats or excessive width/precision print `?` and return -1.
- `sprintf` and `snprintf` use this same assembly formatter and conversion subset,
  including `%f`/`%g`, without linking the console or initializing the display.
  Manual links using them need the existing decimal/arithmetic runtime objects
  (`ieee_engine.o`, `tables.o`, `arithmetic.o`, `integers.o` and `io.o`, followed
  by `libc.a` and then `decimal.o`); the automatic ROM builder resolves these
  dependencies.
- `snprintf(NULL, 0, ...)` counts output without accessing a destination.
  Truncation preserves the full return length; lengths above `INT_MAX` return -1.
  A `%c` zero byte counts as output and does not end formatting. Buffer formatting
  errors still append a terminator whenever the capacity is nonzero.
- Dynamic `*` widths/precision, `+`, space and `#` flags, octal conversions,
  `%e`, `%a`, `%p`, `%n` and wide characters are unsupported.

### Stream limitations

- `fgets` starts at the beginning of the fixture on every call. It stops at a
  newline, the fixture's terminating zero or the capacity limit, retaining a
  copied newline. It returns the buffer on success and a null pointer for a
  non-`stdin` stream or nonpositive capacity.
- The fixture is not interactive controller or keyboard input. The ROM builder's
  `--input` option supplies its contents.
- `fflush` needs NMI enabled and enough VBlank time for pending presentation.
  A clean flush returns immediately.
- Linking the console initializes its display and enables NMI before `main()`.
  See [display and interrupt ownership](operations.md#display-and-interrupt-ownership)
  before combining it with game rendering.
- `fopen`, `fclose`, `fread`, `fwrite` and `scanf` are not
  currently supplied.

## `<ctype.h>`

| Function | Supported behavior |
| --- | --- |
| `isalnum` | Test ASCII letters or decimal digits. |
| `isalpha` | Test ASCII letters. |
| `islower`, `isupper` | Test ASCII lowercase or uppercase letters. |
| `isdigit` | Test ASCII decimal digits. |
| `isxdigit` | Test ASCII hexadecimal digits. |
| `iscntrl` | Test ASCII control characters, including DEL. |
| `isgraph` | Test printable ASCII excluding space. |
| `isspace` | Test ASCII space or codes 9–13. |
| `isblank` | Test ASCII space or horizontal tab. |
| `isprint` | Test printable ASCII including space. |
| `ispunct` | Test printable ASCII punctuation. |
| `tolower`, `toupper` | Convert ASCII letters to lowercase or uppercase, respectively. Leave other values unchanged. |

Classification returns 1 for a match and 0 otherwise. Inputs are unsigned byte
values or EOF. EOF classifies false and survives case conversion.

## Type and limits headers

- `<stddef.h>` supplies 16-bit `size_t`/`ptrdiff_t`, `NULL`, `offsetof` (including
  nested members and array designators), byte `wchar_t`, and two-byte-aligned
  `max_align_t`. Wide literals and wide I/O remain unsupported.
- `<stdbool.h>` supplies `bool`, `true`, `false` and
  `__bool_true_false_are_defined`. `_Bool` occupies one byte, stores 0 or 1,
  and converts integers, pointers and floating values using scalar truth rules.
- `<limits.h>` describes unsigned plain char, signed/unsigned 8-bit characters,
  16-bit short/int, 32-bit long and 64-bit long long. Width constants accompany the limits.
- `<stdint.h>` supplies exact, least and fast 8/16/32/64-bit types and limits,
  16-bit near pointer integer types, 64-bit `intmax_t`/`uintmax_t`, and integer
  constant macros. Fast 8-bit types use 16-bit int. Pointer integers describe
  ordinary near pointers; far-pointer values require an unsigned long.
- `<inttypes.h>` supplies integer printf macros for supported formats, including
  64-bit hexadecimal, and 64-bit/intmax scan macros for user-provided parsers.
  The bundled stdio API does not implement scanf.
- `<float.h>` describes the selected IEEE floating types with gradual
  underflow. `<math.h>` supplies
  `float_t`, `double_t`, `INFINITY`, `NAN`, `HUGE_VAL` and `HUGE_VALF`.
  Infinity and NaN expand to compiler constant expressions.
- In binary64 mode, `<fenv.h>` controls rounding and sticky exception flags for runtime
  binary64 arithmetic, square root, conversions, and decimal I/O.
  The startup environment uses nearest-even. Binary32 arithmetic and
  translation-time constants use nearest-even.
- No decimal floating, signal, multibyte conversion, or math-error constants
  are advertised. `nullptr_t` is
  absent because the language does not implement `nullptr`.

## `<bitops.h>`

`ffs`, `clz`, `popcount`, and `parity` operate on 16-bit values. The `l` and
`ll` forms operate on 32-bit and 64-bit values. `ffs` gives the one-based
lowest set bit (zero for no set bits), `clz` counts leading zero bits
(the width for zero), `popcount` counts set bits, and `parity` gives zero
for even counts and one for odd counts.

The corresponding GCC-style `__builtin_` forms fold supported integer
constant expressions and otherwise call the same assembly entry points.
Use nonzero inputs to the `__builtin_clz` family for GCC portability.

## `<math.h>`

`fabs(double)` and `fabsf(float)` clear the sign bit, including for negative
zero and NaNs, while preserving all other bits. `fabs` uses the selected
double format. `fabsf` always uses binary32.

`ldexp(double, int)` and `ldexpf(float, int)` scale by a signed power of two.
Binary32 rounds to nearest even. Binary64 follows the floating-point
environment and reports its exceptions. Both functions set `errno` to
`ERANGE` on overflow and inexact results that round to a subnormal or zero.

| Function | Supported behavior |
| --- | --- |
| `sin`, `sinf` | Sine of an angle in radians. |
| `cos`, `cosf` | Cosine of an angle in radians. |
| `atan`, `atanf` | Principal arctangent in radians. |
| `sqrt`, `sqrtf` | Square root. |
| `exp`, `expf` | Natural exponential. |
| `log`, `logf` | Natural logarithm. |

The `f` forms use binary32 assembly; the other forms use separately linked
binary64 assembly. Invalid domains and NaN inputs produce
a fixed quiet NaN. `log(0)` produces negative infinity. Exponential
overflow and underflow produce infinity and gradual underflow. Sine,
arctangent and square root preserve signed zero. The functions leave
`errno` and floating exception flags untouched. The deterministic corpus
observed at most two ULP error against a four-ULP test gate. This is measured
coverage. The binary64 log, exp, atan, sine and cosine tests observed at most
one ULP against high-precision Decimal references; these approximations are
not guaranteed correctly rounded. Binary64 sine and cosine use 224-bit
fractional Payne–Hanek reduction. Function scratch supports ordinary nested calls.

## `<errno.h>`

- Declares the global `int errno` and defines `ERANGE` as 34.
- `strtol`, `strtoul` and `strtod` set `ERANGE` on range errors. Clear `errno`
  before parsing when checking for a new range error.
- This is not a complete standard error catalog. Allocation failure is reported
  by a null pointer; do not assume every library failure sets `errno`.

## `<time.h>`

| Name | Supported behavior |
| --- | --- |
| `clock_t` | Unsigned 32-bit `unsigned long` |
| `clock_t clock(void)` | Count delivered NMI frames, modulo 2^32 |
| `unsigned int __clock_rate(void)` | Report the nominal 60 Hz NTSC or 50 Hz PAL frame rate |
| `CLOCKS_PER_SEC` | Runtime expression reporting nominal 60 Hz NTSC or 50 Hz PAL |

- `clock()` measures frame-quantized elapsed time, including waits. It is not a
  CPU-cycle or calendar clock.
- It does not enable NMI, initialize hardware or acknowledge interrupt flags.
  Without the console, initialize handler state and enable NMI explicitly.
- The counter does not advance while NMI is disabled. Unsigned differences wrap
  modulo 2^32; intervals spanning a complete wrap cannot be distinguished.
- Querying `CLOCKS_PER_SEC` alone does not require the frame counter or an NMI
  handler. The header declares `__clock_rate()` to implement that macro.
- `time_t`, `time()`, calendar conversion and other standard time APIs are not
  provided. See [frame timing](operations.md#frame-timing) for ownership rules.

For the complete language subset and target restrictions, see
[supported C features and target rules](operations.md).
