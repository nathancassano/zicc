"""Category 3 checks: subscript CSE, LICM, .a8 increment, pointer store sequence, CFG index reuse, jump threading, carry reuse, and bool slot test."""
import os
import importlib.util
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'reuse-licm-check'
SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT

SOURCE = r'''
#ifdef _MSC_VER
#include <stdint.h>
typedef uintptr_t uaddr_t;
#else
typedef unsigned long uaddr_t;
#endif

struct FiveByte {
    unsigned char tag;
    unsigned short a;
    unsigned short b;
};

struct OamEntry {
    unsigned char x;
    unsigned char y;
    unsigned char tile;
    unsigned char attr;
};

struct OamWriter {
    struct OamEntry *entry;
};

const struct FiveByte rom_items[8] = {
    {1, 10, 100}, {2, 20, 200}, {3, 30, 300}, {4, 40, 400},
    {5, 50, 500}, {6, 60, 600}, {7, 70, 700}, {8, 80, 800}
};

const unsigned char rom_bytes[8] = {10, 20, 30, 40, 50, 60, 70, 80};
struct FiveByte near_items[8];
struct OamEntry oam_buf[8];
struct OamWriter oam_writer;
unsigned short grid[16];
unsigned char spawn_group;
volatile unsigned char vflag;
volatile unsigned short dma_lo_out;
volatile unsigned char dma_hi_out;
unsigned short jt_state;
unsigned short word_input[8] = {0, 1, 2, 3, 4, 5, 6, 7};
unsigned short word_output[8];

__noinline void word_range(unsigned short start, unsigned short count) {
    unsigned short end = start + count;
    for (; start < end; ++start)
        word_output[start] = word_input[start] ^ 16U;
}

__noinline unsigned short optional_word_range(unsigned short start, unsigned short end) {
    unsigned short sum = 0;
    for (; start < end; ++start) {
        if (start < 8U)
            sum += word_input[start];
        sum += 1U;
    }
    return sum;
}

__noinline unsigned short scale_helper(unsigned short v) {
    return v + 3U;
}

__noinline unsigned short scaled_rom_sum(unsigned short idx) {
    unsigned short s = rom_items[idx].tag;
    s += rom_items[idx].a;
    s += rom_items[idx].b;
    return s;
}

__noinline unsigned short licm_sq_offset(unsigned short dx, unsigned short dy, unsigned short *out) {
    unsigned short i;
    unsigned short acc = 0;
    for (i = 0; i < 4U; i++) {
        unsigned short sq = dy * dy;
        acc += sq + dx + i;
        out[i] = acc;
    }
    return acc;
}

__noinline unsigned short licm_for_init_cond(unsigned short n, unsigned short *out) {
    unsigned short i = 0U;
    unsigned short acc = 0U;
    unsigned short k = 99U;
    for (k = n + 1U; i < k * k; i++) {
        acc += i + 1U;
        out[i] = acc;
    }
    return acc + k;
}

__noinline unsigned short licm_for_decl_init_cond(unsigned short n) {
    unsigned short i = 0U;
    unsigned short acc = 0U;
    for (unsigned short limit = n + 1U; i < limit * limit; i++) {
        acc += i + 1U;
    }
    return acc;
}

__noinline unsigned short licm_for_init_zero(unsigned short n) {
    unsigned short i = 10U;
    unsigned short acc = 0U;
    unsigned short k = 99U;
    for (k = n + 1U; i < k * k; i++) {
        acc += 1U;
    }
    return acc + k;
}

__noinline unsigned char inc_byte_global(void) {
    unsigned char prev = spawn_group++;
    spawn_group++;
    return prev;
}

__noinline void write_oam_pair(unsigned char x0, unsigned char y0, unsigned char t0,
                               unsigned char x1, unsigned char y1, unsigned char t1) {
    struct OamEntry *p = oam_writer.entry;
    p->x = x0;
    p->y = y0;
    p->tile = t0;
    p->attr = 0x20U;
    oam_writer.entry = p + 1;
    oam_writer.entry->x = x1;
    oam_writer.entry->y = y1;
    oam_writer.entry->tile = t1;
    oam_writer.entry->attr = 0x21U;
    oam_writer.entry++;
}

__noinline void writer_advance_const(void) {
    oam_writer.entry += 2;
}

__noinline unsigned short cfg_scaled_index_branch(unsigned short cond, unsigned short idx) {
    unsigned short a = (unsigned short)spawn_group;
    a += grid[idx];
    if (cond) {
        a += 10U;
    }
    return grid[idx] + a;
}

__noinline unsigned short thread_zero_check(unsigned short *cur) {
    unsigned short sum = 0;
    if (jt_state == 0U) return 99U;
    sum += *cur;
    if (jt_state == 0U) return 77U;
    return sum;
}

__noinline unsigned short carry_only_reuse(unsigned short pad, unsigned char k) {
    dma_lo_out = pad;
    dma_lo_out = (unsigned short)(uaddr_t)(rom_bytes + k);
    dma_hi_out = (unsigned char)(((uaddr_t)(rom_bytes + k)) >> 16);
    return rom_bytes[k];
}

__noinline unsigned short bool_slot_branch(unsigned short x, unsigned short y, unsigned short cond) {
    unsigned char flag = 0;
    unsigned short a, b, c, d, e, f, g, h, j, k, m, n, p, q;
    if (cond) flag = 1U;
    a = scale_helper(x);
    b = scale_helper(y);
    c = scale_helper(a + b);
    d = scale_helper(b + c);
    e = scale_helper(c + d);
    f = scale_helper(d + e);
    g = scale_helper(e + f);
    h = scale_helper(f + g);
    j = scale_helper(g + h);
    k = scale_helper(h + j);
    m = scale_helper(j + k);
    n = scale_helper(k + m);
    p = scale_helper(m + n);
    q = scale_helper(n + p);
    {
        unsigned short acc = a + b + c + d + e + f + g + h + j + k + m + n + p + q;
        if (flag) {
            return acc + 10U;
        }
        return acc + 20U;
    }
}

int main(void) {
    unsigned short out[4];
    unsigned short i;

    for (i = 0; i < 16U; i++) grid[i] = i * 3U + 1U;
    for (i = 0; i < 8U; i++) {
        near_items[i].tag = (unsigned char)(i + 1U);
        near_items[i].a = (unsigned short)(i * 10U);
        near_items[i].b = (unsigned short)(i * 100U);
    }

    if (scaled_rom_sum(3U) != 444U) return 1;
    if (licm_sq_offset(2U, 5U, out) != 114U || out[3] != 114U) return 2;

    spawn_group = 4U;
    if (inc_byte_global() != 4U || spawn_group != 6U) return 3;

    oam_writer.entry = &oam_buf[0];
    write_oam_pair(10U, 20U, 30U, 40U, 50U, 60U);
    if (oam_writer.entry != &oam_buf[2]) return 4;
    if (oam_buf[0].x != 10U || oam_buf[0].attr != 0x20U || oam_buf[1].tile != 60U || oam_buf[1].attr != 0x21U) return 5;
    writer_advance_const();
    if (oam_writer.entry != &oam_buf[4]) return 6;

    spawn_group = 2U;
    if (cfg_scaled_index_branch(1U, 5U) != (2U + 16U + 10U + 16U)) return 7;
    if (cfg_scaled_index_branch(0U, 5U) != (2U + 16U + 16U)) return 13;
    jt_state = 0U;
    if (thread_zero_check(&grid[2]) != 99U) return 8;
    jt_state = 1U;
    if (thread_zero_check(&grid[2]) != 7U) return 9;

    if (carry_only_reuse(1U, 3U) != 40U || dma_lo_out == 0) return 10;

    if (bool_slot_branch(5U, 9U, 1U) + 10U != bool_slot_branch(5U, 9U, 0U)) return 11;
    if (bool_slot_branch(5U, 9U, 1U) == 0U) return 12;

    if (licm_for_init_cond(1U, grid) != 12U || grid[3] != 10U) return 14;
    if (licm_for_decl_init_cond(1U) != 10U) return 15;
    if (licm_for_init_zero(1U) != 2U) return 16;
    word_range(3U, 5U);
    word_range(2U, 0U);
#ifndef _MSC_VER
    word_range(7U, 65531U);
#endif
    if (word_output[2] != 0U || word_output[3] != 19U ||
        word_output[4] != 20U || word_output[7] != 23U) return 17;
    if (optional_word_range(0U, 32769U) != 32797U) return 18;
    return 0;
}
'''


def section(asm_text, name):
    return asm_text.split(f'_{name}:\n', 1)[1].split(f'__size_{name}', 1)[0]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = SOURCE
    host_c = OUT / 'host.c'
    host_c.write_text(re.sub(r'\b(__noinline|__far)\b', '', SOURCE))
    host_exe = OUT / 'host.exe'
    support.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/W4', '/O2',
                 '/Fo' + str(OUT / 'host.obj'), '/Fe' + str(host_exe), host_c])
    assert subprocess.run([str(host_exe)], timeout=5, creationflags=subprocess.CREATE_NO_WINDOW).returncode == 0

    cfile, rom, labels = support.compile_case(
        'reuse_licm', source, extra_objects=[ROOT / 'build/integers.o']
    )
    asm = cfile.with_suffix('.s').read_text()

    srs = section(asm, 'scaled_rom_sum')
    assert srs.count('__mul16') <= 1, srs

    lsq = section(asm, 'licm_sq_offset')
    assert lsq.count('__mul16') == 1, lsq
    mul_pos = lsq.index('__mul16')
    # The hoisted multiply must appear before the loop body backward-branch label
    loop_labels = re.findall(r'^(cg_[A-Za-z0-9_]+)\s*=\s*\*$', lsq, re.M)
    assert any(lsq.index(lbl + ' = *') > mul_pos for lbl in loop_labels), lsq

    ibg = section(asm, 'inc_byte_global')
    assert 'inc a:.loword(_spawn_group)' in ibg, ibg

    wac = section(asm, 'writer_advance_const')
    assert 'adc #$0008' in wac and 'ldx ' not in wac, wac

    csi = section(asm, 'cfg_scaled_index_branch')
    assert csi.count('asl a') == 1, csi

    scaled = section(asm, 'word_range')
    assert re.search(r'inx\n    inx\n(?:;[^\n]*\n)*    cpx z:__arith_lhs\+\d+\n    bne ', scaled), scaled
    assert 'pei ($00)' not in scaled, scaled
    optional = section(asm, 'optional_word_range')
    assert 'dec z:$0000' in optional, optional

    tzc = section(asm, 'thread_zero_check')
    assert tzc.count('beq ') + tzc.count('bne ') == 1, tzc

    cor = section(asm, 'carry_only_reuse')
    assert cor.count('adc #.loword(_rom_bytes)') == 1, cor

    bsb = section(asm, 'bool_slot_branch')
    assert 'sep #$20' not in bsb, bsb

    for fn in ('licm_for_init_cond', 'licm_for_decl_init_cond', 'licm_for_init_zero'):
        sec = section(asm, fn)
        assert sec.count('__mul16') == 1, sec
        fn_mul = sec.index('__mul16')
        fn_labels = re.findall(r'^(cg_[A-Za-z0-9_]+)\s*=\s*\*$', sec, re.M)
        assert any(sec.index(lbl + ' = *') > fn_mul for lbl in fn_labels), sec

    support.emulate(rom, labels, 0)
    print('PASS reuse licm: subscript CSE, LICM, .a8 inc, const ptr adv, CFG scaled X, jump threading, carry reuse, bool slot')


if __name__ == '__main__':
    main()
