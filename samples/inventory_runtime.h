#ifndef INVENTORY_RUNTIME_H
#define INVENTORY_RUNTIME_H

struct Item {
    unsigned short id;
    short quantity;
    unsigned long unit_price;
};

extern const struct Item catalog[3];
unsigned long inventory_value(const struct Item * __far items, int count);
int adjust_quantity(struct Item *item, short change);

#endif
