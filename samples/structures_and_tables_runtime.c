/* Same driver as structures_and_tables.c. Separate kernel compilation prevents
 * zicc from folding the checks or inlining away their calls. */
#include "inventory_runtime.h"

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
