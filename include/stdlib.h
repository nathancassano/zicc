#ifndef ZICC_STDLIB_H
#define ZICC_STDLIB_H
#include <stddef.h>
#define EXIT_SUCCESS 0
#define EXIT_FAILURE 1
void *malloc(size_t size);
void *calloc(size_t count, size_t size);
void *realloc(void *pointer, size_t size);
void free(void *pointer);
typedef struct {
    unsigned char * __far base;
    unsigned long size;
} far_heap_t;
/* Keep an even-aligned block of WRAM for this heap alone */
int far_heap_init(far_heap_t *heap, void * __far storage, unsigned long size);
void * __far far_malloc(far_heap_t *heap, unsigned long size);
void * __far far_calloc(far_heap_t *heap, unsigned long count, unsigned long size);
void * __far far_realloc(far_heap_t *heap, void * __far pointer, unsigned long size);
void far_free(far_heap_t *heap, void * __far pointer);
void qsort(void *base, size_t count, size_t size, int (*compare)(const void *, const void *));
void *bsearch(const void *key, const void *base, size_t count, size_t size, int (*compare)(const void *, const void *));
#if !__ZICC_BINARY64__
#define strtod __ieee_parse
#define strtold __ieee_parse
#endif
double strtod(const char * __far text, char * __far *end);
long double strtold(const char * __far text, char * __far *end);
int atoi(const char * __far text);
long atol(const char * __far text);
long strtol(const char * __far text, char * __far *end, int base);
unsigned long strtoul(const char * __far text, char * __far *end, int base);
long long strtoll(const char * __far text, char * __far *end, int base);
unsigned long long strtoull(const char * __far text, char * __far *end, int base);
int abs(int value);
long labs(long value);
void abort(void);
void exit(int status);
void quick_exit(int status);
void _Exit(int status);
#endif
