/* Runtime counterpart of integer_operations.c. Compile integer_kernels.c as a
 * separate translation unit: zicc cannot fold these calls using the
 * driver's inputs. */
unsigned short word_add(unsigned short a, unsigned short b);
unsigned short word_sub(unsigned short a, unsigned short b);
int signed_add(short a, short b);
unsigned long unsigned_div(unsigned long a, unsigned long b);
unsigned long unsigned_mod(unsigned long a, unsigned long b);
long signed_div(long a, long b);
long signed_mod(long a, long b);
unsigned long long_add(unsigned long a, unsigned long b);
unsigned long long_and(unsigned long a, unsigned long b);
unsigned long long_shr(unsigned long a, unsigned int n);
unsigned long mix_words(unsigned long a, unsigned int n);
unsigned long long_mul(unsigned long a, unsigned long b);

int main(void)
{
    if (word_add(65535U, 1U) != 0) return 1;
    if (word_sub(0U, 1U) != 65535U) return 2;
    if (signed_add(-32767 - 1, 32767) != -1) return 3;
    if (unsigned_div(0xfedcba98UL, 0x1234UL) != 0xe0042UL ||
        unsigned_mod(0xfedcba98UL, 0x1234UL) != 0x930UL) return 4;
    if (signed_div(-1234567L, 97L) != -12727L) return 5;
    if (signed_mod(-1234567L, 97L) != -48L) return 6;
    if (long_add(0xffffffffUL, 1UL) != 0UL) return 7;
    if (long_and(0xfedcba98UL, 0xffffUL) != 0xba98UL) return 8;
    if (long_shr(0xfedcba98UL, 17U) != 0x7f6eUL) return 9;
    if (mix_words(0x12345678UL, 4U) != 0x226622e7UL) return 10;
    if (long_mul(0xfedcba98UL, 0x1234UL) != 0x49f496e0UL) return 11;
    return 0;
}
