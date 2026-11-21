#ifndef _SRAM_H
#define _SRAM_H

unsigned long sram_capacity(void);
/* Foreground transfers. The caller supplies a valid near WRAM buffer */
int sram_read(unsigned long offset, void *dst, unsigned int count);
int sram_write(unsigned long offset, const void *src, unsigned int count);

#endif
