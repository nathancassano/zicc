__noinline unsigned legacy_sum(const unsigned char * __far data, unsigned size)
{
    unsigned sum = 0;
    while (size--) {
        sum += *data++;
    }
    return sum;
}
