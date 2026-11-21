/* LoROM, HiROM, and ExHiROM header and checksum finalizer */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MIB (1024u * 1024u)
#define MAX_ROM_SIZE (8u * MIB)
#define LOROM_HEADER 0x7FC0u
#define HIROM_HEADER 0xFFC0u
#define EXHIROM_HEADER 0x40FFC0u
static unsigned char rom[MAX_ROM_SIZE];
static unsigned rom_size, header_offset;
static unsigned char map_mode;

static int check_sram(const char *path)
{
    unsigned type = rom[header_offset + 22];
    unsigned exponent = rom[header_offset + 24];
    unsigned maximum = rom_size > 4u * MIB ? 9 : 8;
    /* Older raw LoROM links can leave the header unstamped */
    if (rom[header_offset + 21] != map_mode) {
        rom[header_offset + 22] = 0;
        rom[header_offset + 24] = 0;
        return 1;
    }
    if (type == 0 && exponent == 0) return 1;
    if (type != 2 || exponent < 1 || exponent > maximum) {
        fprintf(stderr, "%s: unsupported cartridge type $%02X and SRAM size byte $%02X\n",
                path, type, exponent);
        return 0;
    }
    if (map_mode == 0x30 && exponent > 5 && rom_size < 2u * MIB) {
        fprintf(stderr, "%s: LoROM SRAM above 32 KiB requires a ROM of at least 2 MiB\n", path);
        return 0;
    }
    return 1;
}

static int has_vectors(unsigned offset)
{
    unsigned i;
    for (i = offset + 33; i < offset + 64; i += 2)
        if (rom[i] < 0x80) return 0;
    return 1;
}

static int read_rom(const char *path)
{
    FILE *file = fopen(path, "rb");
    size_t count;
    int extra;
    int failed, standard_size;
    if (!file) {
        perror(path);
        return 0;
    }
    count = fread(rom, 1, sizeof rom, file);
    extra = fgetc(file);
    failed = ferror(file);
    if (fclose(file) != 0) failed = 1;
    standard_size = count >= 32768 && count <= 4u * MIB && (count & (count - 1)) == 0;
    if (extra != EOF || failed || (!standard_size && count != 6u * MIB && count != MAX_ROM_SIZE)) {
        fprintf(stderr, "%s: expected a power-of-two ROM from 32 KiB through 4 MiB or a 6/8 MiB ExHiROM\n", path);
        return 0;
    }
    rom_size = (unsigned)count;
    if (rom_size > 4u * MIB) {
        header_offset = EXHIROM_HEADER;
        map_mode = rom[header_offset + 21];
        if (map_mode != 0x25 && map_mode != 0x35) {
            fprintf(stderr, "%s: expected explicit ExHiROM map mode at file offset $40FFD5\n", path);
            return 0;
        }
    } else {
        int lorom_sram = rom[LOROM_HEADER + 21] == 0x30 && rom[LOROM_HEADER + 22] == 2
                       && has_vectors(LOROM_HEADER);
        map_mode = !lorom_sram && rom_size >= 65536 && rom[HIROM_HEADER + 21] == 0x31
                 ? 0x31 : 0x30;
        header_offset = map_mode == 0x31 ? HIROM_HEADER : LOROM_HEADER;
    }
    return check_sram(path);
}

static int read_title(const char *path, unsigned char title[21])
{
    unsigned char input[24];
    FILE *file = fopen(path, "rb");
    size_t count, i;
    int extra, failed;
    if (!file) {
        perror(path);
        return 0;
    }
    count = fread(input, 1, sizeof input, file);
    extra = fgetc(file);
    failed = ferror(file);
    if (fclose(file) != 0) failed = 1;
    if (failed || extra != EOF || count == sizeof input) {
        fprintf(stderr, "%s: title must be at most 21 printable ASCII characters\n", path);
        return 0;
    }
    if (count && input[count - 1] == '\n') {
        --count;
        if (count && input[count - 1] == '\r') --count;
    }
    if (count > 21) {
        fprintf(stderr, "%s: title exceeds 21 characters\n", path);
        return 0;
    }
    for (i = 0; i < count; ++i) {
        if (input[i] < 0x20 || input[i] > 0x7E) {
            fprintf(stderr, "%s: title must contain printable ASCII only\n", path);
            return 0;
        }
    }
    memset(title, ' ', 21);
    memcpy(title, input, count);
    return 1;
}

static void put_word(unsigned offset, unsigned value)
{
    rom[offset] = (unsigned char)value;
    rom[offset + 1] = (unsigned char)(value >> 8);
}

int main(int argc, char **argv)
{
    unsigned char title[21];
    unsigned checksum = 0, i, declared_size;
    FILE *file;
    int failed;
    if (argc != 4) {
        fprintf(stderr, "usage: romtool input.raw output.sfc title.txt\n");
        return EXIT_FAILURE;
    }
    if (!read_title(argv[3], title) || !read_rom(argv[1])) return EXIT_FAILURE;
    for (i = header_offset + 32; i < header_offset + 64; i += 2) {
        unsigned vector = (unsigned)rom[i] | ((unsigned)rom[i + 1] << 8);
        if (vector < 0x8000) {
            fprintf(stderr, "invalid ROM vector at file offset $%04X\n", i);
            return EXIT_FAILURE;
        }
    }
    memcpy(rom + header_offset, title, sizeof title);
    rom[header_offset + 21] = map_mode;
    declared_size = rom_size == 6u * MIB ? 8u * MIB : rom_size;
    for (i = declared_size / 1024, rom[header_offset + 23] = 0; i > 1; i >>= 1) ++rom[header_offset + 23];
    rom[header_offset + 25] = 0x00; /* Japan */
    rom[header_offset + 26] = 0x00; /* Developer ID */
    rom[header_offset + 27] = 0x00; /* Version */
    put_word(header_offset + 28, 0xFFFF);
    put_word(header_offset + 30, 0x0000);
    for (i = 0; i < rom_size; ++i) checksum = (checksum + rom[i]) & 0xFFFFu;
    if (rom_size == 6u * MIB) {
        for (i = 4u * MIB; i < rom_size; ++i) checksum = (checksum + rom[i]) & 0xFFFFu;
    }
    put_word(header_offset + 28, checksum ^ 0xFFFFu);
    put_word(header_offset + 30, checksum);
    file = fopen(argv[2], "wb");
    if (!file) {
        perror(argv[2]);
        return EXIT_FAILURE;
    }
    failed = fwrite(rom, 1, rom_size, file) != rom_size;
    if (fclose(file) != 0) failed = 1;
    if (failed) {
        fprintf(stderr, "%s: failed to write complete ROM\n", argv[2]);
        return EXIT_FAILURE;
    }
    printf("%s: %u bytes, checksum $%04X, complement $%04X\n",
           argv[2], rom_size, checksum, checksum ^ 0xFFFFu);
    return EXIT_SUCCESS;
}
