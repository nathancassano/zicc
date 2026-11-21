/* Checks that nested and recursive calls return the expected values and keep
 * the caller's local variables intact. Zero means all checks passed. */

int combine(int a, int b, int c, int d)
{
    return a + b * 2 + c * 3 + d * 4;
}

int factorial(int n)
{
    if (n < 2) return 1;
    return n * factorial(n - 1);
}

int fibonacci(int n)
{
    int left, right;
    if (n < 2) return n;
    left = fibonacci(n - 1);
    right = fibonacci(n - 2);
    return left + right;
}

unsigned long add_scaled(unsigned long base, int amount, int scale)
{
    return base + (unsigned long)amount * (unsigned long)scale;
}

int main(void)
{
    int saved = 1234;
    int result;
    result = combine(factorial(3), fibonacci(6), factorial(4), fibonacci(5));
    if (result != 114) return 1;
    if (saved != 1234) return 2;
    if (factorial(6) != 720 || fibonacci(10) != 55) return 3;
    if (add_scaled(0x12340000UL, 7, 9) != 0x1234003fUL) return 4;
    return 0;
}
