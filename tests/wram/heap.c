#include <stdlib.h>
#include <string.h>

__hiram unsigned int storage[32768u];
static far_heap_t heap;

int main(void)
{
    unsigned *near = malloc(20);
    unsigned char * __far p, * __far q;
    if (!near || !far_heap_init(&heap, 0, 0) || far_malloc(&heap, 1))
        return 1;
    if (far_heap_init(&heap, near, 20) || !far_heap_init(&heap, storage, sizeof(storage)))
        return 2;
    if ((unsigned long)storage != 0x7F0000UL || sizeof(storage) != 65536UL)
        return 3;
    p = far_malloc(&heap, 65532UL);
    if (!p || far_malloc(&heap, 1))
        return 4;
    p[65531u] = 11;
    far_free(&heap, p);
    p = far_calloc(&heap, 4, 5);
    if (!p || p[0] || p[19] || far_calloc(&heap, 65536UL, 65536UL))
        return 5;
    far_memset(p, 23, 20);
    p[4] = 33;
    far_memmove(p + 1, p, 19);
    if (p[5] != 33)
        return 6;
    q = far_realloc(&heap, p, 30);
    if (!q || q[5] != 33 || q[19] != 23 || far_realloc(&heap, q, 65532UL) || q[5] != 33)
        return 7;
    far_free(&heap, q);
    p = far_malloc(&heap, 65532UL);
    if (!p)
        return 8;
    far_free(&heap, p);
    *near = 42;
    if (*near != 42)
        return 9;
    free(near);
    return 0;
}
