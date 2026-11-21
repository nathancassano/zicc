#ifndef ZICC_TIME_H
#define ZICC_TIME_H

/* NMI frames, modulo 2^32. Console startup enables NMI; other apps enable it */
typedef unsigned long clock_t;
clock_t clock(void);

/* Runtime region detection: nominal frames per second, 60 NTSC or 50 PAL */
unsigned int __clock_rate(void);
#define CLOCKS_PER_SEC ((clock_t)__clock_rate())

#endif
