/* Return zero if all loops pass, or a code for the memory source and loop that failed */
#include <stdlib.h>


#define LENGTH 8
#define BYTE_END 0xe7u
#define WORD_END 0xbeefu

/* Both ends of the payload have a zero terminator and a nonzero sentinel.
 * A custom-sentinel scan must consume the intervening zero as data.
 * The final element is past the sentinel and must never enter the sum. */
static const unsigned char rom_bytes[LENGTH] = {BYTE_END, 0, 0x80, 0xff, 7, 0, BYTE_END, 0x55};
static const unsigned short rom_words[LENGTH] = {WORD_END, 0, 0x12ef, 0xbe01, 0xff00, 0, WORD_END, 0x55aa};
static unsigned char static_bytes[LENGTH];
static unsigned short static_words[LENGTH];

/* The rolling sum distinguishes traversal order and counts zero elements
 * after a nonzero value. The cursor checks identify the exact stopping point.
 * Far pointers let the same loops accept ROM and any of the WRAM sources. */
static __noinline int check_bytes(const unsigned char * __far source)
{
    const unsigned char * __far p;
    unsigned i, sum;

    sum = 0;
    for (i = 2; i < 5; ++i)
        sum = sum * 2u + source[i];
    if (sum != 1029u) return 1;

    sum = 0;
    p = source + 5;
    do {
        sum = sum * 2u + *--p;
    } while (p != source + 2);
    if (sum != 666u) return 2;

    sum = 0;
    p = source + 2;
    while (*p)
        sum = sum * 2u + *p++;
    if (sum != 1029u || p != source + 5) return 3;

    sum = 0;
    p = source + 4;
    while (*p != 0)
        sum = sum * 2u + *p--;
    if (sum != 666u || p != source + 1) return 4;

    sum = 0;
    for (p = source + 1; *p != BYTE_END; ++p)
        sum = sum * 2u + *p;
    if (sum != 2058u || p != source + 6) return 5;

    sum = 0;
    p = source + 5;
    for (;;) {
        if (*p == BYTE_END) break;
        sum = sum * 2u + *p--;
    }
    if (sum != 1332u || p != source) return 6;
    return 0;
}

static __noinline int check_words(const unsigned short * __far source)
{
    const unsigned short * __far p;
    unsigned i;
    unsigned long sum;

    sum = 0;
    for (i = 5; i > 2;)
        sum = sum * 2UL + source[--i];
    if (sum != 363249UL) return 7;

    sum = 0;
    p = source + 2;
    do {
        sum = sum * 2UL + *p++;
    } while (p != source + 5);
    if (sum != 181950UL) return 8;

    sum = 0;
    p = source + 2;
    while (*p != 0)
        sum = sum * 2UL + *p++;
    if (sum != 181950UL || p != source + 5) return 9;

    sum = 0;
    p = source + 4;
    while (*p)
        sum = sum * 2UL + *p--;
    if (sum != 363249UL || p != source + 1) return 10;

    sum = 0;
    p = source + 1;
scan_forward:
    if (*p != WORD_END) {
        sum = sum * 2UL + *p;
        ++p;
        goto scan_forward;
    }
    if (sum != 363900UL || p != source + 6) return 11;

    sum = 0;
    p = source + 5;
    while (1) {
        if (*p == WORD_END) break;
        sum = sum * 2UL + *p;
        --p;
    }
    if (sum != 726498UL || p != source) return 12;
    return 0;
}

int main(void)
{
    unsigned char stack_bytes[LENGTH];
    unsigned short stack_words[LENGTH];
    unsigned char *heap_bytes;
    unsigned short *heap_words;
    unsigned i;
    int failure;

    /* Offsets 0, 20, 40 and 60 identify ROM, static, stack and heap */
    failure = check_bytes(rom_bytes);
    if (!failure) failure = check_words(rom_words);
    if (failure) return failure;

    for (i = 0; i < LENGTH; ++i) {
        static_bytes[i] = rom_bytes[i];
        static_words[i] = rom_words[i];
        stack_bytes[i] = static_bytes[i];
        stack_words[i] = static_words[i];
    }
    failure = check_bytes(static_bytes);
    if (!failure) failure = check_words(static_words);
    if (failure) return 20 + failure;

    failure = check_bytes(stack_bytes);
    if (!failure) failure = check_words(stack_words);
    if (failure) return 40 + failure;

    heap_bytes = malloc(sizeof stack_bytes);
    heap_words = malloc(sizeof stack_words);
    if (!heap_bytes || !heap_words) {
        free(heap_bytes);
        free(heap_words);
        return 80;
    }
    for (i = 0; i < LENGTH; ++i) {
        heap_bytes[i] = stack_bytes[i];
        heap_words[i] = stack_words[i];
    }
    failure = check_bytes(heap_bytes);
    if (!failure) failure = check_words(heap_words);
    free(heap_bytes);
    free(heap_words);
    if (failure) return 60 + failure;
    return 0;
}
