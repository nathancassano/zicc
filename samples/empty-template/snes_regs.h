#ifndef SNES_REGS_H
#define SNES_REGS_H

#include <stdint.h>

// Read or write a register by name. Use NAME_ADDR for its numeric address
// The far pointer selects bank zero while ordinary data stays in work RAM
#define SNES_REG8(address)  (*(volatile uint8_t * __far)(address))
#define SNES_REG16(address) (*(volatile uint16_t * __far)(address))
// 16-bit accesses span consecutive ports. Double-write ports remain 8-bit:
// write their low byte, then high byte, to the same register
// For a combined DMA mode/PPU-port write, use SNES_REG16(DMAP0_ADDR)

// S-CPU and S-PPU MMIO port definitions for Super NES
// and useful 65816 macros
//
/* Copyright 2014-2015 Damian Yerrick
 *
 * Copying and distribution of this file, with or without
 * modification, are permitted in any medium without royalty provided
 * the copyright notice and this notice are preserved in all source
 * code copies.  This file is offered as-is, without any warranty.
 */

//
// This header summarizes some of the Super NES MMIO ports
// For more details, see these web pages:
// http://wiki.superfamicom.org/
// http://problemkaputt.de/fullsnes.htm
//
//

// S-PPU configuration -----------------------------------------------

#define INIDISP_ADDR             0x2100
#define INIDISP                  SNES_REG8(INIDISP_ADDR)
// INIDISP
// 76543210
// |   ++++- brightness (F: max)
// +-------- 1: disable rendering
//
// Rendering on when bit 7 is false is the opposite sense from bit 7
// of LCDC on Game Boy, but the same sense as bit 7 of DISPCNT on GBA
// Think of it as two's complement: rendering is on when brightness
// is positive or off when brightness is negative
// "Is the PPU on?"
// "Negative."
#define FORCEBLANK           0x80

#define SETINI_ADDR              0x2133
#define SETINI                   SNES_REG8(SETINI_ADDR)
// SETINI
// 76543210
// ||  |||+- Screen interlace
// ||  ||+-- Shrink sprites vertically during interlace
// ||  |+--- 0: show lines 1-224; 1: show lines 1-239
// ||  +---- Show subscreen in left half of each pixel
// ||        (modes 012347; forced on in modes 56)
// |+------- In mode 7, use bit 7 of pixel color as priority
// +-------- External genlock, intended for SFC Titler. Use 0 on SNES
#define INTERLACE            0x01
#define INTERLACEOBJ         0x02
#define BG_TALL              0x04
#define SUB_HIRES            0x08
#define M7_EXTBG             0x40

#define STAT77_ADDR              0x213e
#define STAT77                   SNES_REG8(STAT77_ADDR)
// STAT77
// 76543210  PPU address generator status
// ||  ++++- PPU1 version (always 1)
// |+------- 1: sprite overflow (>32 on a line) since the last vblank end
// +-------- 1: sliver overflow (>34 on a line) since the last vblank end
// this parallels bit 5 of $2002 on NES

#define STAT78_ADDR              0x213f
#define STAT78                   SNES_REG8(STAT78_ADDR)
// STAT78
// 76543210  PPU compositor status
// || |++++- PPU2 version (1-3, not counting minor versions of 3)
// || +----- 1: PPU is configured for 50 Hz (PAL)
// |+------- 1: SLHV has happened since last STAT78 read
// +-------- Toggles every vblank; reflects top/bottom interlace field

// S-PPU sprites -----------------------------------------------------

#define OBSEL_ADDR               0x2101
#define OBSEL                    SNES_REG8(OBSEL_ADDR)
// OBSEL
// 76543210
// ||||| ++- Sprite main pattern table (0=$0000, 1=$2000, 2=$4000, 3=$6000)
// |||++---- Alt pattern table offset (0=$1000, 1=$2000, 2=$3000, 3=$4000)
// +++------ 0: 8/16; 1: 8/32; 2: 8/64; 3: 16/32; 4: 16/32; 5: 32/64
//           (all sprites are square and 2D-mapped)
#define OBSIZE_8_16          0x00
#define OBSIZE_8_32          0x20
#define OBSIZE_8_64          0x40
#define OBSIZE_16_32         0x60
#define OBSIZE_16_64         0x80
#define OBSIZE_32_64         0xA0

// OAMADD and OAMADDH: 16-bit, 128 sprites followed by high-X/size table
#define OAMADD_ADDR              0x2102
#define OAMADD                   SNES_REG16(OAMADD_ADDR)
#define OAMDATA_ADDR             0x2104
#define OAMDATA                  SNES_REG8(OAMDATA_ADDR)
#define OAMDATAREAD_ADDR         0x2138
#define OAMDATAREAD              SNES_REG8(OAMDATAREAD_ADDR)
// OAMADD, OAMDATA and OAMDATAREAD
// Parallels NES $2003, except apparently word-addressed
// OAM random access is working here, unlike on NES
// If bit 15 is set, value at start of frame apparently also
// controls which sprites are in front

// S-PPU background configuration ------------------------------------

#define BGMODE_ADDR              0x2105
#define BGMODE                   SNES_REG8(BGMODE_ADDR)
// BGMODE
// 76543210
// |||||+++- 0: 4 planes 2 bpp
// |||||     1: 2 planes 4 bpp, 1 plane 2 bpp
// |||||     2: 2 planes 4 bpp, OPT
// |||||     3: 1 plane 8 bpp, 1 plane 4 bpp
// |||||     4: 1 plane 8 bpp, 1 plane 2 bpp, OPT
// |||||     5: 1 plane 4 bpp, 1 plane 2 bpp, hires
// |||||     6: 1 plane 4 bpp, OPT, hires
// |||||     7: 1 plane rot/scale
// ||||+---- In mode 1, set plane 2 high-prio in front of all others
// |||+----- Plane 0 tile size (0: 8x8, 1: 16x16)
// ||+------ Plane 1 tile size (0: 8x8, 1: 16x16)
// |+------- Plane 2 tile size (0: 8x8, 1: 16x16)
// +-------- Plane 3 tile size (0: 8x8, 1: 16x16)
//           Modes 5 and 6 use 16x8 instead of 8x8
//           Mode 7 always uses 8x8

#define MOSAIC_ADDR              0x2106
#define MOSAIC                   SNES_REG8(MOSAIC_ADDR)
// MOSAIC
// 76543210
// |||||||+- Apply mosaic to plane 0 (or mode 7 high-prio horizontal)
// ||||||+-- Apply mosaic to plane 1 (or mode 7 high-prio vertical)
// |||||+--- Apply mosaic to plane 2
// ||||+---- Apply mosaic to plane 3
// ++++----- Pixel size minus 1 (0=1x1, 15=16x16)

// BG1SC through BG4SC: through $210A
#define BG1SC_ADDR               0x2107
#define BG1SC                    SNES_REG8(BG1SC_ADDR)
// BG1SC through BG4SC
// 76543210
//  ||||||+- Nametable width (0: 1 screen, 1: 2 screens)
//  |||||+-- Nametable height (0: 1 screen, 1: 2 screens)
//  +++++--- Nametable base address in $400 units
// Each nametable in modes 0-6 is 32 rows, each 32 spaces long
#define NTXY(xc,yc) ((xc)|((yc)<<5))

#define BG12NBA_ADDR             0x210b
#define BG12NBA                  SNES_REG8(BG12NBA_ADDR)
// BG12NBA and BG34NBA
// FEDCBA98 76543210
//  ||| |||  ||| +++- Pattern table base address for plane 0
//  ||| |||  +++----- Same for plane 1
//  ||| +++---------- Same for plane 2
//  +++-------------- Same for plane 3

#define M7SEL_ADDR               0x211a
#define M7SEL                    SNES_REG8(M7SEL_ADDR)
// M7SEL
// 76543210
// ||    ||
// ||    |+- Flip screen horizontally
// ||    +-- Flip screen vertically
// ++------- 0: repeat entire mode 7 plane
//           2: transparent outside; 3: tile $00 repeating outside
#define M7_HFLIP             0x01
#define M7_VFLIP             0x02
#define M7_WRAP              0x00
#define M7_NOWRAP            0x80
#define M7_BORDER00          0xC0

// S-PPU scrolling ---------------------------------------------------

// BG1HOFS through BG4VOFS: double write low then high (000-3FF m0-6, 000-7FF m7)
#define BG1HOFS_ADDR             0x210d
#define BG1HOFS                  SNES_REG8(BG1HOFS_ADDR)
// BG1HOFS through BG4VOFS: similar. reg 210F-2114 are same for other planes
#define BG1VOFS_ADDR             0x210e
#define BG1VOFS                  SNES_REG8(BG1VOFS_ADDR)
// Hi-res scrolling in modes 5-6 moves by whole (sub+main) pixels in X
// but half scanlines in Y
// The top visible line is the line below the value written here
// For example, in 224-line mode, if 12 is written, lines 13 through
// 237 of the background are visible.  This differs from the NES
//
// Mode 7 uses this value as the center of rotation.  This differs
// from the GBA, which fixes the center of rotation at the top left

// 211B-2120 control mode 7 matrix; to be documented later

// S-PPU VRAM data port ----------------------------------------------

#define VMAIN_ADDR               0x2115
#define VMAIN                    SNES_REG8(VMAIN_ADDR)
// VMAIN
// 76543210
// |   ||++- VRAM address increment (1, 32, 128, 128)
// |   ++--- Rotate low bits of address left by 3 (off, 8, 9, or 10)
// +-------- 0: Increment after low data port access; 1: after high
// Corresponds to bit 2 of $2000 on NES
#define VRAM_DOWN            0x01
#define VRAM_M7DOWN          0x02
#define INC_DATAHI           0x80

// VMADD: Word address, not double-write anymore
#define VMADD_ADDR               0x2116
#define VMADD                    SNES_REG16(VMADD_ADDR)
#define VMDATAL_ADDR             0x2118
#define VMDATAL                  SNES_REG8(VMDATAL_ADDR)
#define VMDATAH_ADDR             0x2119
#define VMDATAH                  SNES_REG8(VMDATAH_ADDR)
// VMDATAREADL: Same dummy read as on NES is needed
#define VMDATAREADL_ADDR         0x2139
#define VMDATAREADL              SNES_REG8(VMDATAREADL_ADDR)
#define VMDATAREADH_ADDR         0x213a
#define VMDATAREADH              SNES_REG8(VMDATAREADH_ADDR)

// S-PPU palette -----------------------------------------------------

#define CGADD_ADDR               0x2121
#define CGADD                    SNES_REG8(CGADD_ADDR)
// CGDATA: 5-bit BGR, write twice, low byte first
#define CGDATA_ADDR              0x2122
#define CGDATA                   SNES_REG8(CGDATA_ADDR)
// CGDATAREAD: 5-bit BGR, read twice, low byte first
#define CGDATAREAD_ADDR          0x213b
#define CGDATAREAD               SNES_REG8(CGDATAREAD_ADDR)
#define RGB(r,g,b) ((r)|((g)<<5)|((b)<<10))

// S-PPU window ------------------------------------------------------

#define W12SEL_ADDR              0x2123
#define W12SEL                   SNES_REG8(W12SEL_ADDR)
#define W34SEL_ADDR              0x2124
#define W34SEL                   SNES_REG8(W34SEL_ADDR)
#define WOBJSEL_ADDR             0x2125
#define WOBJSEL                  SNES_REG8(WOBJSEL_ADDR)
// WOBJSEL
// 76543210
// ||||||++- 0: disable window 1 on BG1/BG3/OBJ; 2: enable; 3: enable outside
// ||||++--- 0: disable window 2 on BG1/BG3/OBJ; 2: enable; 3: enable outside
// ||++----- 0: disable window 1 on BG2/BG4; 2: enable; 3: enable outside
// ++------- 0: disable window 2 on BG2/BG4; 2: enable; 3: enable outside

#define WH0_ADDR                 0x2126
#define WH0                      SNES_REG8(WH0_ADDR)
#define WH1_ADDR                 0x2127
#define WH1                      SNES_REG8(WH1_ADDR)
#define WH2_ADDR                 0x2128
#define WH2                      SNES_REG8(WH2_ADDR)
#define WH3_ADDR                 0x2129
#define WH3                      SNES_REG8(WH3_ADDR)

// WBGLOG: Window op is how windows are combined when both
#define WBGLOG_ADDR              0x212a
#define WBGLOG                   SNES_REG8(WBGLOG_ADDR)
// WOBJLOG: windows 1 and 2 are enabled
#define WOBJLOG_ADDR             0x212b
#define WOBJLOG                  SNES_REG8(WOBJLOG_ADDR)
// WOBJLOG
// 76543210
// ||||||++- Window op for plane 0 or sprites (0: or, 1: and, 2: xor, 3: xnor)
// ||||++--- Window op for plane 1 or color window
// ||++----- Window op for plane 2
// ++------- Window op for plane 3

// S-PPU blending (or "color math") ----------------------------------

// The main layer enable reg, corresponding to PPUMASK on the NES,
// is TM
// TM: Layers enabled for main input of blending
#define TM_ADDR                  0x212c
#define TM                       SNES_REG8(TM_ADDR)
// TS: Layers enabled for sub input of blending
#define TS_ADDR                  0x212d
#define TS                       SNES_REG8(TS_ADDR)
// TMW: Windows enabled for main input of blending
#define TMW_ADDR                 0x212e
#define TMW                      SNES_REG8(TMW_ADDR)
// TSW: Windows enabled for sub input of blending
#define TSW_ADDR                 0x212f
#define TSW                      SNES_REG8(TSW_ADDR)
// TSW
// 76543210
//    ||||+- plane 0
//    |||+-- plane 1
//    ||+--- plane 2
//    |+---- plane 3
//    +----- sprites
// TM roughly parallels NES $2001 bits 4-3,
// except that turning off both bits doesn't disable rendering
// (Use INIDISP for that.)

// PPU1 appears to generate a stream of (main, sub) pairs, which
// PPU2 combines to form output colors

// Blending parameters not documented yet.  Wait for a future demo

// When BGMODE is 0-6 (or during vblank in mode 7), a fast 16x8
// signed multiply is available, finishing by the next CPU cycle
// M7A and M7B: write low then high
#define M7A_ADDR                 0x211b
#define M7A                      SNES_REG8(M7A_ADDR)
// M7B: 8-bit factor
#define M7B_ADDR                 0x211c
#define M7B                      SNES_REG8(M7B_ADDR)
#define MPYL_ADDR                0x2134
#define MPYL                     SNES_REG8(MPYL_ADDR)
#define MPYM_ADDR                0x2135
#define MPYM                     SNES_REG8(MPYM_ADDR)
#define MPYH_ADDR                0x2136
#define MPYH                     SNES_REG8(MPYH_ADDR)

// SLHV: read while $4201 D7 is set: populate x and y coords
#define SLHV_ADDR                0x2137
#define SLHV                     SNES_REG8(SLHV_ADDR)
// OPHCT: used with light guns, read twice
#define OPHCT_ADDR               0x213c
#define OPHCT                    SNES_REG8(OPHCT_ADDR)
// OPVCT: also read twice
#define OPVCT_ADDR               0x213d
#define OPVCT                    SNES_REG8(OPVCT_ADDR)

// SPC700 communication ports ----------------------------------------

#define APUIO0_ADDR              0x2140
#define APUIO0                   SNES_REG8(APUIO0_ADDR)
#define APUIO1_ADDR              0x2141
#define APUIO1                   SNES_REG8(APUIO1_ADDR)
#define APUIO2_ADDR              0x2142
#define APUIO2                   SNES_REG8(APUIO2_ADDR)
#define APUIO3_ADDR              0x2143
#define APUIO3                   SNES_REG8(APUIO3_ADDR)

// S-CPU interrupt control -------------------------------------------

#define NMITIMEN_ADDR            0x4200
#define NMITIMEN                 SNES_REG8(NMITIMEN_ADDR)
// NMITIMEN
// 76543210
// | ||   +- Automatically read controllers in first 4 lines of vblank
// | ++----- 0: no IRQ (and acknowledge any pending); 1: IRQs at HTIME;
// |         2: one IRQ at (0, VTIME); 3: one IRQ at (HTIME, VTIME)
// +-------- 1: Enable NMI at start of vblank
#define VBLANK_NMI           0x80
#define HTIME_IRQ            0x10
#define VTIME_IRQ            0x20
#define HVTIME_IRQ           0x30
#define AUTOREAD             0x01

#define HTIME_ADDR               0x4207
#define HTIME                    SNES_REG16(HTIME_ADDR)
#define HTIMEH_ADDR              0x4208
#define HTIMEH                   SNES_REG8(HTIMEH_ADDR)
#define VTIME_ADDR               0x4209
#define VTIME                    SNES_REG16(VTIME_ADDR)
#define VTIMEH_ADDR              0x420a
#define VTIMEH                   SNES_REG8(VTIMEH_ADDR)

// RDNMI: read to acknowledge NMI
#define RDNMI_ADDR               0x4210
#define RDNMI                    SNES_REG8(RDNMI_ADDR)
// RDNMI
// 76543210
// |   ||||
// |   ++++- DMA controller version (1, 2) where v1 has an HDMA glitch
// +-------- 1: Vblank has started since last read (like $2002.d7 on NES)

// TIMEUP: bit 7: htime/vtime IRQ occurred since last read;
#define TIMEUP_ADDR              0x4211
#define TIMEUP                   SNES_REG8(TIMEUP_ADDR)
// read to acknowledge

#define HVBJOY_ADDR              0x4212
#define HVBJOY                   SNES_REG8(HVBJOY_ADDR)
// HVBJOY
// 76543210
// ||     +- 0: Controller reading finished; 1: busy
// |+------- 1: In hblank (including hblank of vblank)
// +-------- 1: In vblank

// MEMSEL: 0: slow ROM everywhere; 1: fast ROM in banks 80-FF
#define MEMSEL_ADDR              0x420d
#define MEMSEL                   SNES_REG8(MEMSEL_ADDR)
// (requires 120ns or faster PRG ROM)

// S-CPU controller I/O ----------------------------------------------

// Manual controller reading behaves almost exactly as on Famicom
// For games using up to 2 standard controllers, these aren't needed,
// as you can enable controller autoreading along with vblank NMIs
// But for games using (multitap, mouse, etc.), you will need to
// read the extra bits separately after the autoreader finishes
#define JOYA_ADDR                0x4016
#define JOYA                     SNES_REG8(JOYA_ADDR)
#define JOYB_ADDR                0x4017
#define JOYB                     SNES_REG8(JOYB_ADDR)

// In addition to the common strobe, each controller port has an
// additional output bit that can be used as, say, a chip select
// for SPI peripherals
#define WRIO_ADDR                0x4201
#define WRIO                     SNES_REG8(WRIO_ADDR)
// WRIO
// 76543210
// |+------- Controller 1 pin 6 output
// +-------- Controller 2 pin 6 output

// Results of the autoreader
// JOY1 and JOY2 contain the auto-read results for serial data bit 0
#define JOY1_ADDR                0x4218
#define JOY1                     SNES_REG16(JOY1_ADDR)
#define JOY2_ADDR                0x421a
#define JOY2                     SNES_REG16(JOY2_ADDR)
// JOY3 and JOY4 contain the auto-read results for serial data bit 1
#define JOY3_ADDR                0x421c
#define JOY3                     SNES_REG16(JOY3_ADDR)
#define JOY4_ADDR                0x421e
#define JOY4                     SNES_REG16(JOY4_ADDR)
// JOY1 through JOY4
// FEDCBA98 76543210
// BYSRUDLR AXLRTTTT
// |||||||| ||||++++- controller type (0: controller, 1: mouse)
// |||||||| ||++----- shoulder buttons
// ++-------++------- right face buttons
//   ||++++---------- Control Pad
//   ++-------------- center face buttons
#define KEY_B                0x8000
#define KEY_Y                0x4000
#define KEY_SELECT           0x2000
#define KEY_START            0x1000
#define KEY_UP               0x0800
#define KEY_DOWN             0x0400
#define KEY_LEFT             0x0200
#define KEY_RIGHT            0x0100
#define KEY_A                0x0080
#define KEY_X                0x0040
#define KEY_L                0x0020
#define KEY_R                0x0010

// It is also possible to read the controller by reading only the
// upper 8 bits in 8-bit mode (m=1).  This may be the path of least
// resistance for porting NES software to the Super NES.  Be careful
// not to mix _HI addresses with non-_HI constants or vice versa
// A, X, L, and R cannot be read this way
#define JOY1H_ADDR               0x4219
#define JOY1H                    SNES_REG8(JOY1H_ADDR)
#define JOY2H_ADDR               0x421b
#define JOY2H                    SNES_REG8(JOY2H_ADDR)
#define KEY_HI_B             (((KEY_B >> 8) & 0xFF))
#define KEY_HI_Y             (((KEY_Y >> 8) & 0xFF))
#define KEY_HI_SELECT        (((KEY_SELECT >> 8) & 0xFF))
#define KEY_HI_START         (((KEY_START >> 8) & 0xFF))
#define KEY_HI_UP            (((KEY_UP >> 8) & 0xFF))
#define KEY_HI_DOWN          (((KEY_DOWN >> 8) & 0xFF))
#define KEY_HI_LEFT          (((KEY_LEFT >> 8) & 0xFF))
#define KEY_HI_RIGHT         (((KEY_RIGHT >> 8) & 0xFF))

// S-CPU multiply and divide -----------------------------------------

// Multiply unit.  Also good for shifting pixels when drawing
// text in a proportional font
// WRMPYA: unchanged by multiplications
#define WRMPYA_ADDR              0x4202
#define WRMPYA                   SNES_REG8(WRMPYA_ADDR)
// WRMPYB: write here to fill RDMPY 8 cycles later
#define WRMPYB_ADDR              0x4203
#define WRMPYB                   SNES_REG8(WRMPYB_ADDR)
#define RDMPY_ADDR               0x4216
#define RDMPY                    SNES_REG16(RDMPY_ADDR)
#define RDMPYH_ADDR              0x4217
#define RDMPYH                   SNES_REG8(RDMPYH_ADDR)

// Divide unit
#define WRDIV_ADDR               0x4204
#define WRDIV                    SNES_REG16(WRDIV_ADDR)
#define WRDIVH_ADDR              0x4205
#define WRDIVH                   SNES_REG8(WRDIVH_ADDR)
// WRDIVB: write divisor to fill RDDIV/RDMPY 16 cycles later
#define WRDIVB_ADDR              0x4206
#define WRDIVB                   SNES_REG8(WRDIVB_ADDR)
#define RDDIV_ADDR               0x4214
#define RDDIV                    SNES_REG16(RDDIV_ADDR)
#define RDDIVH_ADDR              0x4215
#define RDDIVH                   SNES_REG8(RDDIVH_ADDR)

// S-CPU DMA ---------------------------------------------------------

// MDMAEN: writes of 1 << n start a DMA copy on channel n
#define MDMAEN_ADDR              0x420b
#define MDMAEN                   SNES_REG8(MDMAEN_ADDR)
// HDMAEN: writes of 1 << n start HDMA on channel n
#define HDMAEN_ADDR              0x420c
#define HDMAEN                   SNES_REG8(HDMAEN_ADDR)
// Don't run a DMA copy while HDMA is enabled, or you might run into
// a defect in revision 1 of the S-CPU that causes crashing

// There are 8 DMA channels
// Each channel starts $10 bytes after the previous one, from $4300 to $4370
#define DMAP0_ADDR               0x4300
#define DMAP0                    SNES_REG8(DMAP0_ADDR)
// DMAP0
// 76543210
// || ||+++- PPU address offset pattern
// || ||     0: 0     1: 01    2: 00    3: 0011  4: 0123  5: 0101
// || ++---- Memcpy only: 0: increment; 1: fixed; 2: decrement
// |+------- HDMA only: 1: Table contains pointers
// +-------- Direction (0: read CPU write PPU; 1: read PPU write CPU)
#define DMA_LINEAR           0x00
#define DMA_01               0x01
#define DMA_00               0x02  // For HDMA to double write ports; copies can use linear
#define DMA_0011             0x03  // For HDMA to scroll positions and mode 7 matrices
#define DMA_0123             0x04  // For HDMA to window registers
#define DMA_0101             0x05  // Not sure how this would be useful for HDMA
#define DMA_FORWARD          0x00
#define DMA_CONST            0x08
#define DMA_BACKWARD         0x10
#define DMA_INDIRECT         0x40
#define DMA_READPPU          0x80

#define BBAD0_ADDR               0x4301
#define BBAD0                    SNES_REG8(BBAD0_ADDR)
#define A1T0_ADDR                0x4302
#define A1T0                     SNES_REG16(A1T0_ADDR)
#define A1T0L_ADDR               0x4302
#define A1T0L                    SNES_REG8(A1T0L_ADDR)
#define A1T0H_ADDR               0x4303
#define A1T0H                    SNES_REG8(A1T0H_ADDR)
#define A1B0_ADDR                0x4304
#define A1B0                     SNES_REG8(A1B0_ADDR)
// DAS0: number of bytes, not number of transfers; 0 means 65536
#define DAS0_ADDR                0x4305
#define DAS0                     SNES_REG16(DAS0_ADDR)
#define DAS0L_ADDR               0x4305
#define DAS0L                    SNES_REG8(DAS0L_ADDR)
#define DAS0H_ADDR               0x4306
#define DAS0H                    SNES_REG8(DAS0H_ADDR)

// A future demo that includes HDMA effects would include port definitions
//HDMAINDBANK := $4307
//HDMATABLELO := $4308
//HDMATABLEHI := $4309
//HDMALINE    := $430A

// composite values for use with 16-bit writes to DMAP0
#define DMAP0_VMDATAL_FILL    (((VMDATAL_ADDR & 0xFF) << 8)       | DMA_LINEAR | DMA_CONST)
#define DMAP0_VMDATAH_FILL    ((((VMDATAL_ADDR + 1) & 0xFF) << 8) | DMA_LINEAR | DMA_CONST)
#define DMAP0_VMDATA_FILL      (((VMDATAL_ADDR & 0xFF) << 8)       | DMA_01     | DMA_CONST)
#define DMAP0_VMDATAL_COPY    (((VMDATAL_ADDR & 0xFF) << 8)       | DMA_LINEAR | DMA_FORWARD)
#define DMAP0_VMDATAH_COPY    ((((VMDATAL_ADDR + 1) & 0xFF) << 8) | DMA_LINEAR | DMA_FORWARD)
#define DMAP0_VMDATA_COPY      (((VMDATAL_ADDR & 0xFF) << 8)       | DMA_01     | DMA_FORWARD)
#define DMAP0_CGDATA       (((CGDATA_ADDR & 0xFF) << 8)        | DMA_00     | DMA_FORWARD)
#define DMAP0_OAMDATA      (((OAMDATA_ADDR & 0xFF) << 8)       | DMA_00     | DMA_FORWARD)

// FULLSNES NAMES ----------------------------------------------------
//
// These aliases match the names presented in Fullsnes

// S-PPU write
#define OAMADDL_ADDR             0x2102
#define OAMADDL                  SNES_REG8(OAMADDL_ADDR)
#define OAMADDH_ADDR             0x2103
#define OAMADDH                  SNES_REG8(OAMADDH_ADDR)
#define BG2SC_ADDR               0x2108
#define BG2SC                    SNES_REG8(BG2SC_ADDR)
#define BG3SC_ADDR               0x2109
#define BG3SC                    SNES_REG8(BG3SC_ADDR)
#define BG4SC_ADDR               0x210a
#define BG4SC                    SNES_REG8(BG4SC_ADDR)
// BG34NBA: BG34NBA JAM!!!
#define BG34NBA_ADDR             0x210c
#define BG34NBA                  SNES_REG8(BG34NBA_ADDR)
#define BG2HOFS_ADDR             0x210f
#define BG2HOFS                  SNES_REG8(BG2HOFS_ADDR)
#define BG2VOFS_ADDR             0x2110
#define BG2VOFS                  SNES_REG8(BG2VOFS_ADDR)
#define BG3HOFS_ADDR             0x2111
#define BG3HOFS                  SNES_REG8(BG3HOFS_ADDR)
#define BG3VOFS_ADDR             0x2112
#define BG3VOFS                  SNES_REG8(BG3VOFS_ADDR)
#define BG4HOFS_ADDR             0x2113
#define BG4HOFS                  SNES_REG8(BG4HOFS_ADDR)
#define BG4VOFS_ADDR             0x2114
#define BG4VOFS                  SNES_REG8(BG4VOFS_ADDR)
#define VMADDL_ADDR              0x2116
#define VMADDL                   SNES_REG8(VMADDL_ADDR)
#define VMADDH_ADDR              0x2117
#define VMADDH                   SNES_REG8(VMADDH_ADDR)
#define M7C_ADDR                 0x211d
#define M7C                      SNES_REG8(M7C_ADDR)
#define M7D_ADDR                 0x211e
#define M7D                      SNES_REG8(M7D_ADDR)
#define M7X_ADDR                 0x211f
#define M7X                      SNES_REG8(M7X_ADDR)
#define M7Y_ADDR                 0x2120
#define M7Y                      SNES_REG8(M7Y_ADDR)
#define CGWSEL_ADDR              0x2130
#define CGWSEL                   SNES_REG8(CGWSEL_ADDR)
#define CGADSUB_ADDR             0x2131
#define CGADSUB                  SNES_REG8(CGADSUB_ADDR)
#define COLDATA_ADDR             0x2132
#define COLDATA                  SNES_REG8(COLDATA_ADDR)

// S-PPU read

// other B bus devices
#define WMDATA_ADDR              0x2180
#define WMDATA                   SNES_REG8(WMDATA_ADDR)
#define WMADD_ADDR               0x2181
#define WMADD                    SNES_REG16(WMADD_ADDR)
#define WMADDL_ADDR              0x2181
#define WMADDL                   SNES_REG8(WMADDL_ADDR)
#define WMADDM_ADDR              0x2182
#define WMADDM                   SNES_REG8(WMADDM_ADDR)
#define WMADDH_ADDR              0x2183
#define WMADDH                   SNES_REG8(WMADDH_ADDR)

// S-CPU I/O write
#define WRDIVL_ADDR              0x4204
#define WRDIVL                   SNES_REG8(WRDIVL_ADDR)
#define HTIMEL_ADDR              0x4207
#define HTIMEL                   SNES_REG8(HTIMEL_ADDR)
#define VTIMEL_ADDR              0x4209
#define VTIMEL                   SNES_REG8(VTIMEL_ADDR)

// S-CPU I/O read
#define RDIO_ADDR                0x4213
#define RDIO                     SNES_REG8(RDIO_ADDR)
#define RDDIVL_ADDR              0x4214
#define RDDIVL                   SNES_REG8(RDDIVL_ADDR)
#define RDMPYL_ADDR              0x4216
#define RDMPYL                   SNES_REG8(RDMPYL_ADDR)
#define JOY1L_ADDR               0x4218
#define JOY1L                    SNES_REG8(JOY1L_ADDR)
#define JOY2L_ADDR               0x421a
#define JOY2L                    SNES_REG8(JOY2L_ADDR)
#define JOY3L_ADDR               0x421c
#define JOY3L                    SNES_REG8(JOY3L_ADDR)
#define JOY3H_ADDR               0x421d
#define JOY3H                    SNES_REG8(JOY3H_ADDR)
#define JOY4L_ADDR               0x421e
#define JOY4L                    SNES_REG8(JOY4L_ADDR)
#define JOY4H_ADDR               0x421f
#define JOY4H                    SNES_REG8(JOY4H_ADDR)

#endif // SNES_REGS_H
