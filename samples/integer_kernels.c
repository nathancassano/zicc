/* Compile separately from integer_operations_runtime.c, without LTO. Each
 * operation receives unknown inputs even when the driver supplies constants. */
unsigned short word_add(unsigned short a, unsigned short b) { return (unsigned short)(a + b); }
unsigned short word_sub(unsigned short a, unsigned short b) { return (unsigned short)(a - b); }
int signed_add(short a, short b) { return a + b; }
unsigned long unsigned_div(unsigned long a, unsigned long b) { return a / b; }
unsigned long unsigned_mod(unsigned long a, unsigned long b) { return a % b; }
long signed_div(long a, long b) { return a / b; }
long signed_mod(long a, long b) { return a % b; }
unsigned long long_add(unsigned long a, unsigned long b) { return a + b; }
unsigned long long_and(unsigned long a, unsigned long b) { return a & b; }
unsigned long long_shr(unsigned long a, unsigned int n) { return a >> n; }
unsigned long mix_words(unsigned long a, unsigned int n) { return (a >> n) ^ (a << n); }
unsigned long long_mul(unsigned long a, unsigned long b) { return a * b; }
