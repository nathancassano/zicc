/* Checks integer arithmetic on the SNES and on Windows. Both use 16-bit short
 * and 32-bit long. The casts make unsigned results wrap at the same width.
 * Signed results stay in range and all shift counts are valid. */

unsigned long mix_words(unsigned long value, unsigned int shift)
{
    return (value >> shift) ^ (value << shift);
}

int main(void)
{
    unsigned short word = 65535U;
    short minimum = -32767 - 1;
    unsigned long a = 0xfedcba98UL;
    unsigned long b = 0x1234UL;
    long negative = -1234567L;
    unsigned int shift = 4;

    word = (unsigned short)(word + 1U);
    if (word != 0) return 1;
    word = (unsigned short)(word - 1U);
    if (word != 65535U) return 2;
    if (minimum >= 0 || minimum + 32767 != -1) return 3;
    if (a / b != 0xe0042UL || a % b != 0x930UL) return 4;
    if (negative / 97L != -12727L) return 5;
    if (negative % 97L != -48L) return 6;
    if (0xffffffffUL + 1UL != 0UL) return 7;
    if ((a & 0xffffUL) != 0xba98UL) return 8;
    if ((a >> 17) != 0x7f6eUL) return 9;
    if (mix_words(0x12345678UL, shift) != 0x226622e7UL) return 10;
    if (a * b != 0x49f496e0UL) return 11;
    return 0;
}
