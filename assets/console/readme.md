# Console font assets

The SNES text console draws 64 characters across by giving the even columns
to one background layer (BG1) and the odd columns to another (BG2). Both
layers use the same 8 by 8 pixel letters from the libnds font.

## Files

| File | Contents |
| --- | --- |
| `ascii8x8.2bpp` | Reference font used by the generator and display tests. It contains 128 SNES tiles, 16 bytes each, indexed by ASCII. Space and all control characters are blank. |
| `ascii8x8.1bpp` | The 752-byte ROM font. It stores eight row masks per glyph for ASCII 33 through 126, with bit seven on the left. |
| `palette.bgr555` | Four little-endian color words in eight bytes. The pixel values select transparency, black, grey, and white, in that order. The words are $0000, $0000, $4210, and $7FFF. Set CGRAM entry zero to black for the backdrop. |
| `source/default_font.1bpp` | The original 2048-byte libnds font. It has 256 characters, eight bytes per character, with bit zero on the left. |
| `source/libnds_license.txt` | The original license notice for the libnds font. |

Make rebuilds `ascii8x8.1bpp` when the input changes. To rebuild it by hand,
run `python tools/build-console-font.py` from the repository root.

## Where the font came from

The original font is the `default_font_bin` symbol in section
`.rodata.default_font_bin` of the installed libnds archive. The libnds header
`C:\devkitPro\libnds\include\nds\arm9\console.h` describes it as a one-bit
font starting at character zero. [libnds source](https://github.com/devkitPro/libnds)

These devkitARM commands extract the original bytes.

```text
arm-none-eabi-ar x C:\devkitPro\libnds\lib\libnds9.a default_font.bin.o
arm-none-eabi-objcopy -O binary default_font.bin.o default_font.1bpp
```

The SHA-256 of the extracted font is
`e9ac6bc977fc867883899f66d72191a95303373c1f5cc7412a9f8760b8f13b21`.

To make the SNES tiles, start with 2048 zero bytes. For each row of ASCII
characters 32 through 126, reverse the bits of the source byte. Write it at
`code * 16 + row * 2` and again at the next byte. Together the two copies
give each pixel its color. A set bit becomes white (index 3), and a clear bit
becomes transparent (index 0). All 8192 output pixels matched the source in
the conversion check, including blank tiles. A magnified view confirmed that
the letters faced the right way.

## How the console shows text

The console keeps two maps in WRAM, one per background. Each map holds 32 by
32 tile numbers, two bytes per entry. Together they take 4096 bytes. Startup
clears both maps. Each populated entry selects the letter in palette zero
with no flips or priority bits.

| VRAM byte range | Use |
| --- | --- |
| $0000 to $1FFF | BG1 font |
| $2000 to $2FFF | BG2 font |
| $6000 to $67FF | BG1 tile map |
| $6800 to $6FFF | BG2 tile map |

A horizontal offset of -4 moves BG2 eight high-resolution pixels to the
right. Both layers appear on the main and sub screens. SETINI is zero, so
the display has 224 lines with interlace and overscan off.

The screen shows 28 of the 32 rows at a time. To scroll, the console reuses
the oldest row as a blank bottom row and advances both vertical scroll
registers after updating the maps.

`printf` updates WRAM and marks changed rows. During the vertical blanking
interval, the NMI handler groups adjacent changed rows and copies them to
both maps using DMA channel zero. `fflush(stdout)` waits for the display
update. At most 4 KiB of map data needs copying. Updates wait for the next
interval from line 228 on NTSC or line 278 on PAL. With the screen blank,
startup clears the 12 KiB VRAM font area and writes each row mask into the
first two bitplanes of both layers. Each glyph has a transparent tile after
it, so its tile number is twice its ASCII code. Startup also uploads the
palette and initial maps, then turns on the display during vertical blanking
and enables NMI.

Mesen checks the memory contents (WRAM, VRAM, and CGRAM), DMA timing, and
all 114688 pixels for the prompt, a full page, text in different columns,
and scrolling past the last map row. Frame skipping is off. Mesen doubles
each scanline in its 512 by 448 screenshots. The tests check that each pair
matches before reducing the image to 512 by 224 without filtering.
[Console measurements and checks](../../docs/technical/console-hires-trial.md)
