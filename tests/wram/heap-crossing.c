#include <stdlib.h>

__xbankram unsigned storage[45000];
static far_heap_t heap;

int main(void)
{
    unsigned char * __far base = (unsigned char * __far)storage;
    unsigned char * __far edge = base + (0x7EFFEAUL - (unsigned long)base);
    unsigned char * __far p, * __far q, * __far r;
    unsigned i;

    if (!far_heap_init(&heap, edge, 4096) || far_heap_init(&heap, edge + 1, 4096))
        return 1;
    p = far_malloc(&heap, 16);
    q = far_malloc(&heap, 700);
    r = far_calloc(&heap, 3, 5);
    if (p != edge + 4 || q != edge + 24 || !r || r[0] || r[14])
        return 2;
    q[0] = 70;
    far_free(&heap, q + 2);
    if (q[0] != 70 || far_malloc(&heap, 4092))
        return 3;
    far_free(&heap, p);
    far_free(&heap, p);
    far_free(&heap, r);
    far_free(&heap, q);
    p = far_realloc(&heap, 0, 4092);
    if (p != edge + 4 || far_malloc(&heap, 1))
        return 4;
    far_free(&heap, p);

    p = far_malloc(&heap, 61);
    if (p != edge + 4)
        return 5;
    for (i = 0; i < 61; ++i)
        p[i] = (unsigned char)(i ^ 0x42);
    q = far_realloc(&heap, p, 129);
    if (!q || q == p)
        return 6;
    for (i = 0; i < 61; ++i)
        if (q[i] != (unsigned char)(i ^ 0x42))
            return 7;
    if (far_realloc(&heap, q, 5) != q || far_realloc(&heap, q, ~0UL) || q[60] != (60 ^ 0x42))
        return 8;
    if (far_realloc(&heap, q, 0))
        return 9;

    if (!far_heap_init(&heap, base, sizeof(storage)))
        return 10;
    p = base + 4;
    p[0] = 0xFF;
    p[65535UL] = 0xFF;
    p[65536UL] = 0xFF;
    p[65538UL] = 0xFF;
    p[65539UL] = 0xE1;
    q = far_calloc(&heap, 65539UL, 1);
    if (q != p || q[0] || q[65535UL] || q[65536UL] || q[65538UL] || q[65539UL] != 0xE1)
        return 11;
    far_free(&heap, q);
    p = far_malloc(&heap, sizeof(storage) - 4);
    if (p != base + 4)
        return 12;
    far_free(&heap, p);
    return 0;
}
