#ifndef ZICC_MATH_H
#define ZICC_MATH_H
typedef float float_t;
typedef double double_t;
#define INFINITY __builtin_inff()
#define NAN __builtin_nanf()
#define HUGE_VALF INFINITY
#define HUGE_VAL INFINITY
#if !__ZICC_BINARY64__
#define sin sinf
#define cos cosf
#define atan atanf
#define sqrt sqrtf
#define exp expf
#define log logf
#endif
double sin(double);
double cos(double);
double atan(double);
double fabs(double);
double ldexp(double, int);
double sqrt(double);
double exp(double);
double log(double);
float sinf(float);
float cosf(float);
float atanf(float);
float fabsf(float);
float ldexpf(float, int);
float sqrtf(float);
float expf(float);
float logf(float);
#endif
