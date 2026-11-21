#ifndef ZICC_STRING_H
#define ZICC_STRING_H
#include <stddef.h>
void *memcpy(void *destination, const void * __far source, size_t count);
void *memset(void *destination, int value, size_t count);
void *memmove(void *destination, const void * __far source, size_t count);
void * __far far_memcpy(void * __far destination, const void * __far source, unsigned long count);
void * __far far_memmove(void * __far destination, const void * __far source, unsigned long count);
void * __far far_memset(void * __far destination, int value, unsigned long count);
char *strcpy(char *destination, const char * __far source);
char *strncpy(char *destination, const char * __far source, size_t count);
char *strcat(char *destination, const char * __far source);
char *strncat(char *destination, const char * __far source, size_t count);
int strcmp(const char * __far left, const char * __far right);
int strncmp(const char * __far left, const char * __far right, size_t count);
int strcoll(const char * __far left, const char * __far right);
size_t strxfrm(char *destination, const char * __far source, size_t count);
size_t strlen(const char * __far text);
char * __far strchr(const char * __far text, int c);
char * __far strrchr(const char * __far text, int c);
char * __far strpbrk(const char * __far text, const char * __far accept);
char * __far strstr(const char * __far text, const char * __far needle);
size_t strspn(const char * __far text, const char * __far accept);
size_t strcspn(const char * __far text, const char * __far reject);
char *strtok(char *text, const char * __far delimiters);
void * __far memchr(const void * __far source, int c, size_t count);
int memcmp(const void * __far left, const void * __far right, size_t count);
#endif
