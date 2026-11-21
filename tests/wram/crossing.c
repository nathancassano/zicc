#include <string.h>

struct record {
    unsigned long value;
    unsigned word;
};

__xbankram unsigned char area[80001] = {7};
unsigned char * __far tail = area + 80001UL;
volatile unsigned word_index = 32768u;
volatile unsigned long offset = 65536UL;
volatile unsigned nmies;

__interrupt(nmi) void crossing_nmi(void)
{
    ++nmies;
}

__noinline int check_fill(void)
{
    return area[0] == 7 && area[1] == 0x22 && area[offset] == 0x22 && area[65537UL] == 0xCC;
}

int main(void)
{
    unsigned char * __far crossing = area + (0x7EFFFFUL - (unsigned long)area);
    unsigned * __far words = (unsigned * __far)area;
    volatile unsigned * __far at = (volatile unsigned * __far)crossing;
    struct record * __far record = (struct record * __far)crossing;
    struct record reference = {0x12345678UL, 0xABCD};
    if (sizeof(area) != 80001UL || sizeof(&area[0]) != 4 || tail - area != 80001L)
        return 1;
    if (area[0] != 7 || area[80000UL] != 0)
        return 2;
    *at = 0xABCD;
    if (*at != 0xABCD || crossing[0] != 0xCD || crossing[1] != 0xAB)
        return 3;
    *record = reference;
    if (record->value != 0x12345678UL || record->word != 0xABCD)
        return 4;
    area[65535u] = 31;
    words[word_index] = 0xCC75;
    area[offset + 2] = 55;
    if (area[65535u] != 31 || area[offset] != 0x75 || area[65537UL] != 0xCC || area[65538UL] != 55)
        return 5;
    if (words[word_index] != 0xCC75)
        return 6;
    *(volatile unsigned char * __far)0x004200UL = 0x80;
    far_memset(area + 1, 0x22, 65536UL);
    if (!check_fill() || !nmies)
        return 7;
    return 0;
}
