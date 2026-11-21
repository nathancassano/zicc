#include <stdlib.h>

struct record {
    unsigned long value;
    unsigned check;
};

extern __hiram unsigned char pixels[4096];
extern __hiram volatile unsigned long stamp;
extern __farram const unsigned char palette[5];
extern __hiram struct record saved;
extern __hiram unsigned char * __far initial_pointer;
void write_byte(unsigned char * __far p, unsigned char value);
unsigned local_storage(void);

static volatile unsigned index = 1;

__noinline unsigned read_pixel(unsigned i)
{
    return pixels[i];
}

__noinline unsigned update_pixel(unsigned i)
{
    return ++pixels[i];
}

int main(void)
{
    struct record snapshot = {0xABCDEF01UL, 0x2948};
    unsigned i = index;
    if (sizeof(&pixels[0]) != 4 || sizeof(&saved.check) != 4 || sizeof(initial_pointer) != 4)
        return 1;
    if (palette[i] != 4 || *initial_pointer != 3 || pixels[4095] != 0 || stamp != 0x10203040UL)
        return 2;
    if (saved.value || saved.check || local_storage() != 12 || local_storage() != 13)
        return 3;
    if (read_pixel(i) != 1 || update_pixel(i) != 2)
        return 4;
    write_byte(pixels + i, 42);
    if (read_pixel(i) != 42 || pixels[i] != 42)
        return 5;
    pixels[i] = 27;
    stamp = 0x87654321UL;
    if (pixels[i] != 27 || stamp != 0x87654321UL)
        return 6;
    saved = snapshot;
    snapshot = saved;
    if (snapshot.value != 0xABCDEF01UL || snapshot.check != 0x2948)
        return 7;
    return 0;
}
