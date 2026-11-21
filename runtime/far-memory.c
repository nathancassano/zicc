#include <string.h>

void * __far far_memcpy(void * __far destination, const void * __far source, unsigned long count)
{
    unsigned char * __far out = destination;
    const unsigned char * __far in = source;
    while (count) {
        *out++ = *in++;
        --count;
    }
    return destination;
}

void * __far far_memmove(void * __far destination, const void * __far source, unsigned long count)
{
    unsigned char * __far out = destination;
    const unsigned char * __far in = source;
    unsigned long to = (unsigned long)out, from = (unsigned long)in;
    if (to <= from || to - from >= count)
        return far_memcpy(destination, source, count);
    out += count;
    in += count;
    while (count) {
        *--out = *--in;
        --count;
    }
    return destination;
}

void * __far far_memset(void * __far destination, int value, unsigned long count)
{
    unsigned char * __far out = destination;
    while (count) {
        *out++ = (unsigned char)value;
        --count;
    }
    return destination;
}
