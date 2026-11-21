"""Category 2 checks: widened/word power-of-2 multiply, shifts, pointer-diff div, algebraic identities and constants."""
import os
import importlib.util
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'strength-algebra-check'
SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT

SOURCE = r'''
struct Item { int a, b; };
struct Item items[32];
unsigned char oam[64];
volatile unsigned short vword;
volatile unsigned char vbyte;
unsigned short *volatile vptr;

__noinline unsigned long mul_u32_512(unsigned short x) {
    return (unsigned long)x * 512UL;
}
__noinline long mul_s32_512(short x) {
    return (long)x * 512L;
}
__noinline unsigned long mul_u32_65536(unsigned short x) {
    return (unsigned long)x * 65536UL;
}
__noinline unsigned short mul_u16_256(unsigned short x) {
    return x * 256U;
}
__noinline unsigned short mul_u16_256_lhs(unsigned short x) {
    return 256U * x;
}
__noinline unsigned short shr2_shl6(unsigned short x) {
    return (x >> 2) << 6;
}
__noinline unsigned short shr2_mul64_lhs(unsigned short x) {
    return 64U * (x >> 2);
}
__noinline unsigned short shr2_shl10(unsigned short x) {
    return (x >> 2) << 10;
}
__noinline unsigned short shl7_bit8_zero(unsigned short x) {
    return (x & 0xFEFFU) << 7;
}
__noinline unsigned short shl6_bits89_zero(unsigned short x) {
    return (x & 0xFCFFU) << 6;
}
__noinline unsigned short shl7_arbitrary(unsigned short x) {
    return x ^ (x << 7);
}
__noinline int item_index_near(struct Item *p) {
    return (int)(p - items);
}
__noinline unsigned short oam_slots_near(unsigned char *p) {
    return (unsigned short)((p - oam + 15) >> 4);
}
__noinline int ptr_diff_var(struct Item *p, struct Item *q) {
    return (int)(p - q);
}
__noinline unsigned short zero_or_shift(unsigned char vol) {
    return (unsigned short)(0 | ((unsigned short)vol << 8));
}
__noinline unsigned short algebraic_identities(unsigned short x) {
    unsigned short a = x + 0U;
    a = a - 0U;
    a = a * 1U;
    a = a / 1U;
    a = a & 0xFFFFU;
    a = a ^ 0U;
    a = a << 0;
    a = a >> 0;
    return a;
}
__noinline unsigned short volatile_add_zero(void) {
    return vword + 0U;
}
__noinline unsigned short combine_add_sub(unsigned short x) {
    return (unsigned short)((x + 14U) - 1U);
}
__noinline unsigned short combine_cancel(unsigned short x) {
    return (unsigned short)((x + 4U) - 4U);
}
__noinline int combine_cancel_nz(unsigned short x) {
    unsigned short r = (unsigned short)((x + 4U) - 4U);
    return r ? 1 : 0;
}
__noinline unsigned short combine_dec2(unsigned short x) {
    return (unsigned short)((x + 1U) - 3U);
}
__noinline unsigned long widen_nonneg_diff(struct Item *p) {
    return (unsigned long)(p - items);
}
__noinline unsigned long add_with_carry32(unsigned long a, unsigned long b) {
    return a + b;
}

int main(void) {
    unsigned short i;
    if (mul_u32_512(0U) != 0UL || mul_u32_512(1U) != 512UL || mul_u32_512(0x1234U) != 0x00246800UL) return 1;
    if (mul_s32_512(0) != 0L || mul_s32_512(5) != 2560L || mul_s32_512(-5) != -2560L || mul_s32_512(-32768) != -16777216L) return 2;
    if (mul_u32_65536(0xABCDU) != 0xABCD0000UL) return 3;
    if (mul_u16_256(0x1234U) != 0x3400U || mul_u16_256_lhs(0x00ABU) != 0xAB00U) return 4;
    if (shr2_shl6(0U) != 0U || shr2_shl6(3U) != 0U || shr2_shl6(4U) != 64U || shr2_shl6(0x0FFFU) != 0xFFC0U || shr2_shl6(0x1237U) != 0x2340U) return 5;
    if (shr2_mul64_lhs(0x1237U) != 0x2340U || shr2_shl10(0x00FFU) != 0xFC00U || shr2_shl10(0x0007U) != 0x0400U) return 6;
    if (shl7_bit8_zero(0xFFFFU) != 0x7F80U || shl7_bit8_zero(0x0101U) != 0x0080U) return 7;
    if (shl6_bits89_zero(0xFFFFU) != 0x3FC0U || shl6_bits89_zero(0x0303U) != 0x00C0U) return 8;
    if (shl7_arbitrary(0x0100U) != 0x8100U || shl7_arbitrary(0x1234U) != (unsigned short)(0x1234U ^ (0x1234U << 7))) return 9;
    if (item_index_near(&items[0]) != 0 || item_index_near(&items[17]) != 17 || item_index_near(&items[31]) != 31) return 10;
    if (oam_slots_near(&oam[0]) != 0U || oam_slots_near(&oam[1]) != 1U || oam_slots_near(&oam[16]) != 1U || oam_slots_near(&oam[17]) != 2U) return 11;
    if (ptr_diff_var(&items[0], &items[5]) != -5 || ptr_diff_var(&items[9], &items[2]) != 7) return 12;
    if (zero_or_shift(0x5AU) != 0x5A00U) return 13;
    if (algebraic_identities(0x4321U) != 0x4321U) return 14;
    vword = 0x7654U;
    if (volatile_add_zero() != 0x7654U) return 15;
    if (combine_add_sub(100U) != 113U || combine_add_sub(0xFFF3U) != 0U) return 16;
    if (combine_cancel(42U) != 42U || combine_cancel_nz(0U) != 0 || combine_cancel_nz(9U) != 1) return 17;
    if (combine_dec2(10U) != 8U || combine_dec2(0U) != 0xFFFEU) return 18;
    if (widen_nonneg_diff(&items[25]) != 25UL) return 19;
    if (add_with_carry32(0x0001FFFFUL, 1UL) != 0x00020000UL) return 20;
    for (i = 0; i < 4U; ++i) {
        vbyte = (unsigned char)i;
        if (zero_or_shift(vbyte) != (unsigned short)(i << 8)) return 21;
    }
    return 0;
}
'''


def section(asm_text, name):
    return asm_text.split(f'_{name}:\n', 1)[1].split(f'__size_{name}', 1)[0]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = support.near_fixture(SOURCE)
    host_c = OUT / 'host.c'
    host_c.write_text(re.sub(r'\b__noinline\b', '', source))
    host_exe = OUT / 'host.exe'
    support.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/W4', '/O2',
                 '/Fo' + str(OUT / 'host.obj'), '/Fe' + str(host_exe), host_c])
    assert subprocess.run([str(host_exe)], timeout=5, creationflags=subprocess.CREATE_NO_WINDOW).returncode == 0

    cfile, rom, labels = support.compile_case('strength_algebra', source, extra_objects=[ROOT / 'build/integers.o'])
    asm = cfile.with_suffix('.s').read_text()

    mu = section(asm, 'mul_u32_512')
    assert '__mul16wide' not in mu and 'xba' in mu, mu

    ms = section(asm, 'mul_s32_512')
    assert '__mul16wide' not in ms and 'xba' in ms, ms

    m65 = section(asm, 'mul_u32_65536')
    assert '__mul16wide' not in m65, m65

    m256 = section(asm, 'mul_u16_256')
    assert 'xba' in m256 and m256.count('asl a') == 0, m256

    m256l = section(asm, 'mul_u16_256_lhs')
    assert 'xba' in m256l and m256l.count('asl a') == 0, m256l

    s26 = section(asm, 'shr2_shl6')
    assert 'lsr a' not in s26 and 'and #$FFC0' in s26, s26

    s26m = section(asm, 'shr2_mul64_lhs')
    assert 'lsr a' not in s26m and 'and #$FFC0' in s26m, s26m

    s210 = section(asm, 'shr2_shl10')
    assert 'lsr a' not in s210 and 'xba' in s210 and 'and #$FC00' in s210, s210

    s7z = section(asm, 'shl7_bit8_zero')
    assert 'xba' in s7z and 'and #$FF00' in s7z and 'lsr a' in s7z, s7z

    s6z = section(asm, 'shl6_bits89_zero')
    assert 'xba' in s6z and 'and #$FF00' in s6z and s6z.count('lsr a') == 2, s6z

    s7a = section(asm, 'shl7_arbitrary')
    assert 'xba' not in s7a, s7a

    idx_near = section(asm, 'item_index_near')
    assert 'eor #' not in idx_near and 'sbc #$0800' not in idx_near and 'bpl' not in idx_near, idx_near

    oam_near = section(asm, 'oam_slots_near')
    assert 'eor #' not in oam_near and 'bpl' not in oam_near, oam_near

    zos = section(asm, 'zero_or_shift')
    assert 'pha' not in zos and 'xba' in zos, zos

    alg = section(asm, 'algebraic_identities')
    assert 'adc #' not in alg and 'sbc #' not in alg and 'eor #' not in alg, alg

    vadd = section(asm, 'volatile_add_zero')
    assert 'lda a:.loword(_vword)' in vadd and 'adc #' not in vadd, vadd

    cas = section(asm, 'combine_add_sub')
    assert 'adc #$000D' in cas and 'sbc #' not in cas, cas

    cc = section(asm, 'combine_cancel')
    assert 'adc #' not in cc and 'sbc #' not in cc, cc

    cd2 = section(asm, 'combine_dec2')
    assert 'adc #' not in cd2, cd2
    assert 'sbc #$0002' in cd2 or '    dec a\n    dec a\n' in cd2, cd2

    wnd = section(asm, 'widen_nonneg_diff')
    assert 'cmp #$8000' not in wnd and 'ldx #$0000' in wnd, wnd

    support.emulate(rom, labels, 0)
    print('PASS strength-algebra: 32/16 power-of-2 mul, shl6/7 & shift-combine, near ptr-diff div, identities, constants')


if __name__ == '__main__':
    main()
