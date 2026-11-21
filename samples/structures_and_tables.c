/* Reads item records from a table in ROM and updates a record in RAM. Zero
 * means all checks passed. */

struct Item {
    unsigned short id;
    short quantity;
    unsigned long unit_price;
};

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

int main(void)
{
    struct Item item;
    if (inventory_value(catalog, 0) != 0UL) return 1;
    if (inventory_value(catalog, 3) != 1849UL) return 2;
    item.id = catalog[1].id;
    item.quantity = catalog[1].quantity;
    item.unit_price = catalog[1].unit_price;
    if (!adjust_quantity(&item, -2) || item.quantity != 1) return 3;
    if (adjust_quantity(&item, -2) || item.quantity != 1) return 4;
    if (item.id != 20 || inventory_value(&item, 1) != 200UL) return 5;
    return 0;
}
