#ifndef ZICC_STDIO_H
#define ZICC_STDIO_H
#include <stddef.h>
typedef struct __snes_file FILE;
extern FILE __stdout;
extern FILE __stdin;
#define stdout (&__stdout)
#define stdin (&__stdin)
#define EOF (-1)
/* %s consumes a near char pointer; %S consumes a four-byte __far pointer.
 * %f/%g require the floating console runtime (CALC=1). */
int printf(const char * __far format, ...);
int sprintf(char *destination, const char * __far format, ...);
int snprintf(char *destination, size_t capacity, const char * __far format, ...);
/* Wait for pending console output to be presented by NMI; NULL means stdout */
int fflush(FILE *stream);
char *fgets(char *buffer, int capacity, FILE *stream);
#endif
