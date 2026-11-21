/* The host checks binary32 results. Target C checks endptr and errno */
#include <stdlib.h>
#include <string.h>

__declspec(dllexport) unsigned long native_bits(const char *text)
{
    float value = strtof(text, 0);
    unsigned long bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}
