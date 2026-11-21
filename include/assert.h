/* Check NDEBUG each time this header is included */
#undef assert
#ifdef NDEBUG
#define assert(expression) ((void)0)
#else
#ifndef __ZICC_ASSERT_DECLARED
#define __ZICC_ASSERT_DECLARED
void __zicc_assert_fail(const char * __far expression, const char * __far file, unsigned long line);
#endif
#define assert(expression) ((expression) ? (void)0 : __zicc_assert_fail(#expression, __FILE__, __LINE__))
#endif
