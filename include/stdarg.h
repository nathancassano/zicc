#ifndef ZICC_STDARG_H
#define ZICC_STDARG_H
typedef unsigned char *va_list;
#define va_start(ap, last) ((void)((ap) = __builtin_va_start(last)))
#define va_arg(ap, type) (__builtin_va_arg((ap), type))
#define va_end(ap) ((void)((ap) = 0))
#define va_copy(destination, source) ((void)((destination) = (source)))
#endif
