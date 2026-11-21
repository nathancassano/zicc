/* Exercise preprocessing without depending on parser or code-generation support */
#include <stdio.h>
#include <stdlib.h>
#include "../src/headers/preprocess.h"

int main(int argc, char **argv)
{
    char *text;
    if (argc != 3) return 2;
    text = preprocess(argv[1], argv[2]);
    fputs(text, stdout);
    free(text);
    return 0;
}
