#include "snes_regs.h"

// Set up the graphics chip while the screen is blank
static void init_regs(void)
{

    WRIO = 0xff;

    OBSEL = 0;
    BGMODE = 0;
    MOSAIC = 0;
    BG1SC = 0;
    BG2SC = 0;
    BG3SC = 0;
    BG4SC = 0;
    BG12NBA = 0;
    BG34NBA = 0;
    // Each scroll register takes two writes, low byte first
    BG1HOFS = 0;
    BG1HOFS = 0;
    BG1VOFS = 0xff;
    BG1VOFS = 0xff;
    BG2HOFS = 0;
    BG2HOFS = 0;
    BG2VOFS = 0xff;
    BG2VOFS = 0xff;
    BG3HOFS = 0;
    BG3HOFS = 0;
    BG3VOFS = 0xff;
    BG3VOFS = 0xff;
    BG4HOFS = 0;
    BG4HOFS = 0;
    BG4VOFS = 0xff;
    BG4VOFS = 0xff;
    VMAIN = 0x80;
    M7SEL = 0;
    // Start Mode 7 with no scaling or rotation
    M7A = 0;
    M7A = 0x01;
    M7B = 0;
    M7B = 0;
    M7C = 0;
    M7C = 0;
    M7D = 0;
    M7D = 0x01;
    M7X = 0;
    M7X = 0;
    M7Y = 0;
    M7Y = 0;
    W12SEL = 0;
    W34SEL = 0;
    WOBJSEL = 0;
    WH0 = 0;
    WH1 = 0;
    WH2 = 0;
    WH3 = 0;
    WBGLOG = 0;
    WOBJLOG = 0;
    TM = 0;
    TS = 0;
    TMW = 0;
    TSW = 0;
    CGWSEL = 0x30;
    CGADSUB = 0;
    COLDATA = 0xe0;
    SETINI = 0;
}

static uint8_t s_oam[544];
static const uint8_t d_zero = 0;

static void wait_for_vblank_start(void)
{
    while (HVBJOY & 0x80)
    {
    }

    while (!(HVBJOY & 0x80))
    {
    }
}

static void dma0_to_ppu(uint8_t mode, uint8_t port,
                        const uint8_t * __far source, uint16_t length)
{
    unsigned long address = (unsigned long)source;

    DMAP0 = mode;
    BBAD0 = port;
    A1T0 = (uint16_t)address;
    A1B0 = (uint8_t)(address >> 16);
    DAS0 = length;
    MDMAEN = 1;
}

int main(void)
{
    init_regs();

    VMADD = 0;
    // A zero DMA count transfers all 65,536 bytes of VRAM
    dma0_to_ppu(DMA_CONST | DMA_01, VMDATAL_ADDR & 0xff, &d_zero, 0);

    OAMADD = 0;
    dma0_to_ppu(DMA_CONST, OAMDATA_ADDR & 0xff, &d_zero, sizeof s_oam);

    CGADD = 0;
    dma0_to_ppu(DMA_CONST, CGDATA_ADDR & 0xff, &d_zero, 512);

    wait_for_vblank_start();
    INIDISP = 0x0f;

    while (1)
    {
        OAMADD = 0;
        dma0_to_ppu(DMA_FORWARD, OAMDATA_ADDR & 0xff, s_oam, sizeof s_oam);

        wait_for_vblank_start();
    }
}
