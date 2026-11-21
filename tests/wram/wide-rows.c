struct row {
    unsigned long value;
    unsigned check;
};

typedef struct row rows_t[16001];
__xbankram rows_t rows;
volatile unsigned index = 11000;

int main(void)
{
    rows_t * __far first = &rows;
    rows_t * __far last = first;
    struct row replacement = {0x12345678UL, 42};
    unsigned i = index;
    if (rows[i].value || rows[i].check || sizeof(rows) != 96006UL)
        return 1;
    rows[i] = replacement;
    if (rows[i].value != 0x12345678UL || rows[i].check != 42 || rows[0].value)
        return 2;
    ++last;
    if (last - first != 1 || (unsigned long)last - (unsigned long)first != sizeof(rows))
        return 3;
    return 0;
}
