/* Sorts a list in place, then checks the order. Zero means all checks passed */

void insertion_sort(int *values, int count)
{
    int i, j, value;
    for (i = 1; i < count; ++i) {
        value = values[i];
        j = i;
        while (j > 0 && values[j - 1] > value) {
            values[j] = values[j - 1];
            --j;
        }
        values[j] = value;
    }
}

int main(void)
{
    int values[8];
    values[0] = 9;
    values[1] = -4;
    values[2] = 32000;
    values[3] = 0;
    values[4] = -30000;
    values[5] = 9;
    values[6] = 1;
    values[7] = -4;

    insertion_sort(values, 0);
    if (values[0] != 9) return 1;
    insertion_sort(values, 1);
    if (values[0] != 9) return 2;
    insertion_sort(values, 8);
    if (values[0] != -30000 || values[1] != -4) return 3;
    if (values[2] != -4 || values[3] != 0) return 4;
    if (values[4] != 1 || values[5] != 9) return 5;
    if (values[6] != 9 || values[7] != 32000) return 6;
    insertion_sort(values, 8);
    if (values[0] != -30000 || values[7] != 32000) return 7;
    return 0;
}
