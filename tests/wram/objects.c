struct record {
    unsigned long value;
    unsigned check;
};

__farram unsigned char pixels[4096] = {9, 1, 3};
__hiram volatile unsigned long stamp = 0x10203040UL;
__hiram const unsigned char palette[5] = {0, 4, 5, 6, 7};
__hiram struct record saved;
__hiram unsigned char * __far initial_pointer = pixels + 2;
struct color { unsigned first, second; };
static __hiram const struct color fixed_palette[] = {{1, 2}, {1, 3}};

__noinline void write_byte(unsigned char * __far p, unsigned char value)
{
    *p = value;
}

__noinline unsigned local_storage(void)
{
    static __hiram unsigned local = 7;
    static __loram const unsigned low = 3;
    ++local;
    return local + low + fixed_palette[local & 1u].first;
}
