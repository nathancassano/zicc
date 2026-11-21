/* Copies and reverses strings, including empty strings and bytes above 127.
 * Zero means all checks passed. */

int copy_text(char *destination, const char * __far source)
{
    int length = 0;
    while (*source) {
        *destination++ = *source++;
        ++length;
    }
    *destination = 0;
    return length;
}

void reverse_text(char *text, int length)
{
    int left = 0, right = length - 1;
    char saved;
    while (left < right) {
        saved = text[left];
        text[left] = text[right];
        text[right] = saved;
        ++left;
        --right;
    }
}

int text_equal(const char * __far left, const char * __far right)
{
    while (*left && *left == *right) {
        ++left;
        ++right;
    }
    return (unsigned char)*left == (unsigned char)*right;
}

int main(void)
{
    char text[16];
    unsigned char bytes[3];
    int length;
    length = copy_text(text, "SNES 65816");
    if (length != 10 || text[10] != 0) return 1;
    reverse_text(text, length);
    if (!text_equal(text, "61856 SENS")) return 2;
    reverse_text(text, length);
    if (!text_equal(text, "SNES 65816")) return 3;
    if (copy_text(text, "") != 0 || text[0] != 0) return 4;
    reverse_text(text, 0);
    if (!text_equal(text, "")) return 5;
    copy_text(text, "x");
    reverse_text(text, 1);
    if (!text_equal(text, "x")) return 6;
    bytes[0] = 255;
    bytes[1] = 128;
    bytes[2] = 7;
    if (bytes[0] != 255 || bytes[1] != 128 || bytes[2] != 7) return 7;
    return 0;
}
