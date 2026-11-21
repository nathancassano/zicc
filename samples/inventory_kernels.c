/* Compile separately from structures_and_tables_runtime.c, without LTO */
#include "inventory_runtime.h"

const struct Item catalog[3] = {
    { 10, 2, 125UL },
    { 20, 3, 200UL },
    { 30, 1, 999UL }
};

unsigned long inventory_value(const struct Item * __far items, int count)
{
    unsigned long total = 0;
    int i;
    for (i = 0; i < count; ++i)
        total += (unsigned long)items[i].quantity * items[i].unit_price;
    return total;
}

int adjust_quantity(struct Item *item, short change)
{
    short next = (short)(item->quantity + change);
    if (next < 0) return 0;
    item->quantity = next;
    return 1;
}
