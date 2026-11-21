#include <stdlib.h>

unsigned legacy_sum(const unsigned char * __far data, unsigned size);
static const unsigned char table[] = {1, 3, 5, 7};
static volatile unsigned nmies;

__interrupt(nmi) void legacy_nmi(void)
{
    ++nmies;
}

int main(void)
{
    unsigned *data = malloc(sizeof(*data));
    unsigned result;
    if (!data)
        return 1;
    *data = 16;
    *(volatile unsigned char * __far)0x004200UL = 0x80;
    while (!nmies) {
    }
    result = legacy_sum(table, sizeof(table));
    if (result != *data)
        return 2;
    free(data);
    return 0;
}
