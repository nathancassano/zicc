#ifndef ZICC_STDINT_H
#define ZICC_STDINT_H
#include <limits.h>
#include <stddef.h>
typedef signed char int8_t;
typedef unsigned char uint8_t;
typedef signed char int_least8_t;
typedef unsigned char uint_least8_t;
typedef int int_fast8_t;
typedef unsigned int uint_fast8_t;
typedef int int16_t;
typedef unsigned int uint16_t;
typedef int int_least16_t;
typedef unsigned int uint_least16_t;
typedef int int_fast16_t;
typedef unsigned int uint_fast16_t;
typedef long int32_t;
typedef unsigned long uint32_t;
typedef long int_least32_t;
typedef unsigned long uint_least32_t;
typedef long int_fast32_t;
typedef unsigned long uint_fast32_t;
typedef long long int64_t;
typedef unsigned long long uint64_t;
typedef long long int_least64_t;
typedef unsigned long long uint_least64_t;
typedef long long int_fast64_t;
typedef unsigned long long uint_fast64_t;
typedef int intptr_t;
typedef unsigned int uintptr_t;
typedef long long intmax_t;
typedef unsigned long long uintmax_t;
#define INT8_MIN SCHAR_MIN
#define INT8_MAX SCHAR_MAX
#define UINT8_MAX UCHAR_MAX
#define INT8_WIDTH 8
#define UINT8_WIDTH 8
#define INT_LEAST8_MIN INT8_MIN
#define INT_LEAST8_MAX INT8_MAX
#define UINT_LEAST8_MAX UINT8_MAX
#define INT_LEAST8_WIDTH 8
#define UINT_LEAST8_WIDTH 8
#define INT_FAST8_MIN INT16_MIN
#define INT_FAST8_MAX INT16_MAX
#define UINT_FAST8_MAX UINT16_MAX
#define INT_FAST8_WIDTH 16
#define UINT_FAST8_WIDTH 16
#define INT16_MIN INT_MIN
#define INT16_MAX INT_MAX
#define UINT16_MAX UINT_MAX
#define INT16_WIDTH 16
#define UINT16_WIDTH 16
#define INT_LEAST16_MIN INT16_MIN
#define INT_LEAST16_MAX INT16_MAX
#define UINT_LEAST16_MAX UINT16_MAX
#define INT_LEAST16_WIDTH 16
#define UINT_LEAST16_WIDTH 16
#define INT_FAST16_MIN INT16_MIN
#define INT_FAST16_MAX INT16_MAX
#define UINT_FAST16_MAX UINT16_MAX
#define INT_FAST16_WIDTH 16
#define UINT_FAST16_WIDTH 16
#define INT32_MIN LONG_MIN
#define INT32_MAX LONG_MAX
#define UINT32_MAX ULONG_MAX
#define INT32_WIDTH 32
#define UINT32_WIDTH 32
#define INT_LEAST32_MIN INT32_MIN
#define INT_LEAST32_MAX INT32_MAX
#define UINT_LEAST32_MAX UINT32_MAX
#define INT_LEAST32_WIDTH 32
#define UINT_LEAST32_WIDTH 32
#define INT_FAST32_MIN INT32_MIN
#define INT_FAST32_MAX INT32_MAX
#define UINT_FAST32_MAX UINT32_MAX
#define INT_FAST32_WIDTH 32
#define UINT_FAST32_WIDTH 32
#define INT64_MIN LLONG_MIN
#define INT64_MAX LLONG_MAX
#define UINT64_MAX ULLONG_MAX
#define INT64_WIDTH 64
#define UINT64_WIDTH 64
#define INT_LEAST64_MIN INT64_MIN
#define INT_LEAST64_MAX INT64_MAX
#define UINT_LEAST64_MAX UINT64_MAX
#define INT_LEAST64_WIDTH 64
#define UINT_LEAST64_WIDTH 64
#define INT_FAST64_MIN INT64_MIN
#define INT_FAST64_MAX INT64_MAX
#define UINT_FAST64_MAX UINT64_MAX
#define INT_FAST64_WIDTH 64
#define UINT_FAST64_WIDTH 64
#define INTPTR_MIN INT_MIN
#define INTPTR_MAX INT_MAX
#define UINTPTR_MAX UINT_MAX
#define INTPTR_WIDTH 16
#define UINTPTR_WIDTH 16
#define INTMAX_MIN LLONG_MIN
#define INTMAX_MAX LLONG_MAX
#define UINTMAX_MAX ULLONG_MAX
#define INTMAX_WIDTH 64
#define UINTMAX_WIDTH 64
#define PTRDIFF_MIN INT_MIN
#define PTRDIFF_MAX INT_MAX
#define PTRDIFF_WIDTH 16
#define SIZE_MAX UINT_MAX
#define SIZE_WIDTH 16
#define WCHAR_MIN 0
#define WCHAR_MAX 255
#define WCHAR_WIDTH 8
#define INT8_C(value) (value)
#define UINT8_C(value) (value)
#define INT16_C(value) (value)
#define UINT16_C(value) value##U
#define INT32_C(value) value##L
#define UINT32_C(value) value##UL
#define INT64_C(value) value##LL
#define UINT64_C(value) value##ULL
#define INTMAX_C(value) INT64_C(value)
#define UINTMAX_C(value) UINT64_C(value)
#endif
