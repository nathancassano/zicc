#include <time.h>

unsigned int counts[4], irq_status, p, q, result, table[8];
unsigned long a, b, rate;
long sa, sb;
unsigned char * __far indexed_data;
int indexed_index;
int test_driver(void);

/* Helper-heavy first: the following scratch-free handler must not inherit it */
__interrupt(cop) void supervisor(void)
{
    counts[3] = counts[3] + 1;
    if(indexed_data[indexed_index]!=0x5a)counts[3]+=100;
    a = (a << p) ^ (b >> p);
    sa = sa >> p;
    result = (a < (*(volatile unsigned long *)&b ^ (unsigned long)p))
           + (sa < (*(volatile long *)&sb ^ (long)p)) + (p < q) + ((int)p < (int)q);
}

__interrupt(nmi) void vblank(void)
{
    counts[0] = counts[0] + 1;
    *(unsigned int * __far)0x4305UL = 2;
    *(unsigned char * __far)0x420bUL = 1;
}

__interrupt(irq) void raster(void)
{
    counts[1] = counts[1] + 1;
    irq_status = *(unsigned char * __far)0x4211UL;
    a = a << 3;
}

__interrupt(brk) void software_break(void)
{
    counts[2] = counts[2] + 1;
    a = a >> 3;
    result = table[p] + table[q];
}

int main(void)
{
    a = 0x87654321UL;
    indexed_data=(unsigned char * __far)0x7f0000UL;
    indexed_index=-1;
    *(unsigned char * __far)0x7effffUL=0x5a;
    b = 0x10203040UL;
    sa = -1234567L;
    sb = 123456L;
    p = 2;
    q = 5;
    table[2] = 17;
    table[5] = 29;
    rate = CLOCKS_PER_SEC;
    return test_driver();
}
