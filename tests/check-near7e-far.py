"""Check when a far pointer can safely use a shorter address in bank $7E and when the compiler can skip a null check."""
import os
import importlib.util
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'near7e-far-check'
SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT

SOURCE = r'''
#ifdef _MSC_VER
#include <stdint.h>
typedef uintptr_t uaddr_t;
#else
#include <stdint.h>
typedef unsigned long uaddr_t;
#endif

struct Sub {
    uint8_t tag;
    uint16_t extra;
};

struct Node {
    uint16_t val;
    struct Sub sub;
};

const uint8_t rom_bytes[8] = {10, 20, 30, 40, 50, 60, 70, 80};
uint8_t near_grid[16] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16};
uint8_t alt_grid[4] = {21, 22, 23, 24};
struct Node near_nodes[4] = {
    {100, {7, 700}},
    {200, {8, 800}},
    {300, {9, 900}},
    {400, {10, 1000}}
};

__noinline uint16_t far_node_read(const struct Node * __far p, uint16_t bias) {
    if (!p) return 0xDEADu;
#ifdef _MSC_VER
    return p->val + p->sub.tag + bias;
#else
    return p->val + p->sub.tag + bias + (uint16_t)((unsigned long)p >> 16);
#endif
}

__noinline uint16_t far_ptr_read(const uint8_t * __far p) {
    if (!p) return 0xBEEFu;
#ifdef _MSC_VER
    return p[1];
#else
    return p[1] + (uint16_t)((unsigned long)p >> 16);
#endif
}

static inline uint16_t slot_hash_inline(const struct Node * __far e) {
    return ((uint16_t)(unsigned long)e ^ (uint16_t)(e != 0 ? 1u : 0u));
}

static inline uint16_t deref_byte_inline(const uint8_t * __far p, uint16_t idx) {
    return p ? p[idx] : 0u;
}

__noinline uint16_t local_far_array_sum(uint16_t row, uint16_t col_idx) {
    const uint8_t * __far col = (const uint8_t * __far)near_grid;
    const uint8_t * __far cell = (const uint8_t * __far)near_grid + (row << 2);
    return (uint16_t)(col[col_idx] + cell[0] + cell[1] + cell[2] + cell[3]);
}

__noinline uint16_t local_far_struct_walk(uint16_t count, uint16_t use_alt) {
    const struct Node * __far p = use_alt ? (const struct Node * __far)&near_nodes[1]
                                          : (const struct Node * __far)&near_nodes[0];
    const struct Node * __far q = p;
    uint16_t total = 0;
    if (p == 0 || p != q) return 0xFFFFu;
    while (count--) {
        total += p->val + p->sub.tag;
        p++;
    }
    return total;
}

__noinline uint16_t local_far_nullable(uint16_t nonnull) {
    const uint8_t * __far p = nonnull ? (const uint8_t * __far)alt_grid : (const uint8_t * __far)0;
    const uint8_t * __far q = p;
    if (!p) return 99u;
    if (q == (const uint8_t * __far)alt_grid) return q[2];
    return 0u;
}

__noinline uint16_t local_far_mixed_rom(uint16_t use_rom, uint16_t idx) {
    const uint8_t * __far mix = use_rom ? rom_bytes : (const uint8_t * __far)near_grid;
    return mix[idx];
}

__noinline uint16_t local_far_inspect_bank(uint16_t nonnull) {
    const uint8_t * __far p = nonnull ? (const uint8_t * __far)alt_grid : (const uint8_t * __far)0;
    return (uint16_t)((unsigned long)p >> 16);
}

__noinline uint16_t call_inline_narrowed(struct Node *e, uint16_t idx) {
    uint16_t h1 = slot_hash_inline(e);
    uint16_t h2 = slot_hash_inline((struct Node *)0);
    uint16_t b1 = deref_byte_inline(near_grid, idx);
    uint16_t b2 = deref_byte_inline(rom_bytes, idx);
    return (uint16_t)((h1 ^ h2) + b1 + b2);
}

__noinline uint16_t nonnull_after_deref(struct Node *p, uint16_t old_val) {
    if (p->val != old_val || p->sub.tag == 0) {
        return far_node_read(p, 1u);
    }
    return far_node_read(p, 2u);
}

__noinline uint16_t nonnull_after_guard(struct Node *p) {
    if (!p) return 77u;
    return far_node_read(p, 3u);
}

__noinline uint16_t nullable_passthrough(struct Node *p) {
    return far_node_read(p, 5u);
}

__noinline uint16_t nullable_join(struct Node *p, uint16_t drop) {
    if (drop) {
        p = 0;
    }
    return far_node_read(p, 4u);
}

__noinline uint16_t nullable_and_rhs_clear(struct Node *p, uint16_t drop) {
    if (p && !(drop && (p = 0))) {
        return far_node_read(p, 4u);
    }
    return 77u;
}

__noinline uint16_t nullable_or_neg_clear(struct Node *p, uint16_t drop) {
    if (!((p == (struct Node *)0) || (drop && ((p = 0) != 0)))) {
        return far_node_read(p, 4u);
    }
    return 77u;
}

__noinline uint16_t nullable_choose_clear(struct Node *p, uint16_t drop) {
    return (p && (drop ? ((p = 0) == 0) : 1)) ? far_node_read(p, 5u) : 88u;
}

__noinline uint16_t nullable_land_expr_clear(struct Node *p, uint16_t drop) {
    uint16_t ans = 88u;
    (void)(p && (drop ? ((p = 0) == 0) : 1) && ((ans = far_node_read(p, 6u)) || 1));
    return ans;
}

__noinline uint16_t direct_cast_deref(const uint8_t *p, uint16_t idx) {
    return *((const uint8_t * __far)p) + *(((const uint8_t * __far)p) + idx);
}

__noinline uint16_t local_far_displaced(uint16_t base) {
    const uint8_t * __far cell = near_grid + base;
    return (uint16_t)cell[10] + (uint16_t)cell[1] + (uint16_t)cell[-1];
}

int main(void) {
#ifdef _MSC_VER
    const uint16_t bank7e = 0u;
#else
    const uint16_t bank7e = 0x7Eu;
#endif
    if (local_far_array_sum(2u, 3u) != (uint16_t)(4u + 9u + 10u + 11u + 12u)) return 1;
    if (local_far_struct_walk(2u, 0u) != (100u + 7u + 200u + 8u)) return 2;
    if (local_far_struct_walk(2u, 1u) != (200u + 8u + 300u + 9u)) return 3;
    if (local_far_nullable(0u) != 99u || local_far_nullable(1u) != 23u) return 4;
    if (local_far_mixed_rom(1u, 3u) != 40u || local_far_mixed_rom(0u, 3u) != 4u) return 5;
#ifndef _MSC_VER
    if (local_far_inspect_bank(1u) != 0x7Eu || local_far_inspect_bank(0u) != 0u) return 6;
#endif
    if (call_inline_narrowed(&near_nodes[1], 2u) !=
        (uint16_t)((((uint16_t)(uaddr_t)&near_nodes[1]) ^ 1u) + 3u + 30u)) return 7;
    if (nonnull_after_deref(&near_nodes[0], 999u) != (100u + 7u + 1u + bank7e)) return 8;
    if (nonnull_after_deref(&near_nodes[0], 100u) != (100u + 7u + 2u + bank7e)) return 9;
    if (nonnull_after_guard(&near_nodes[2]) != (300u + 9u + 3u + bank7e)) return 10;
    if (nonnull_after_guard((struct Node *)0) != 77u) return 11;
    if (nullable_passthrough(&near_nodes[1]) != (200u + 8u + 5u + bank7e)) return 12;
    if (nullable_passthrough((struct Node *)0) != 0xDEADu) return 13;
    if (nullable_join(&near_nodes[0], 0u) != (100u + 7u + 4u + bank7e)) return 14;
    if (nullable_join(&near_nodes[0], 1u) != 0xDEADu) return 15;
    if (direct_cast_deref(near_grid, 5u) != (1u + 6u)) return 16;
    if (far_ptr_read((const uint8_t * __far)alt_grid) != (uint16_t)(22u + bank7e)) return 17;
    if (far_ptr_read((const uint8_t * __far)0) != 0xBEEFu) return 18;
    if (local_far_displaced(2u) != (uint16_t)(13u + 4u + 2u)) return 19;
    if (nullable_and_rhs_clear(&near_nodes[0], 0u) != (100u + 7u + 4u + bank7e)) return 20;
    if (nullable_and_rhs_clear(&near_nodes[0], 1u) != 0xDEADu) return 21;
    if (nullable_and_rhs_clear((struct Node *)0, 0u) != 77u) return 22;
    if (nullable_or_neg_clear(&near_nodes[1], 0u) != (200u + 8u + 4u + bank7e)) return 23;
    if (nullable_or_neg_clear(&near_nodes[1], 1u) != 0xDEADu) return 24;
    if (nullable_or_neg_clear((struct Node *)0, 0u) != 77u) return 25;
    if (nullable_choose_clear(&near_nodes[2], 0u) != (300u + 9u + 5u + bank7e)) return 26;
    if (nullable_choose_clear(&near_nodes[2], 1u) != 0xDEADu) return 27;
    if (nullable_choose_clear((struct Node *)0, 0u) != 88u) return 28;
    if (nullable_land_expr_clear(&near_nodes[0], 0u) != (100u + 7u + 6u + bank7e)) return 29;
    if (nullable_land_expr_clear(&near_nodes[0], 1u) != 0xDEADu) return 30;
    if (nullable_land_expr_clear((struct Node *)0, 0u) != 88u) return 31;
    return 0;
}
'''


def section(asm_text, name):
    return asm_text.split(f'_{name}:\n', 1)[1].split(f'__size_{name}', 1)[0]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    host_c = OUT / 'host.c'
    host_c.write_text(re.sub(r'\b(__noinline|__far)\b', '', SOURCE))
    host_exe = OUT / 'host.exe'
    support.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/W4', '/O2',
                 '/Fo' + str(OUT / 'host.obj'), '/Fe' + str(host_exe), host_c])
    res = subprocess.run([str(host_exe)], timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
    assert res.returncode == 0, f'host exited with {res.returncode}'

    cfile, rom, labels = support.compile_case(
        'near7e_far', SOURCE, extra_objects=[ROOT / 'build/integers.o']
    )
    asm = cfile.with_suffix('.s').read_text()

    for fn in ('local_far_array_sum', 'local_far_struct_walk', 'local_far_nullable', 'direct_cast_deref', 'local_far_displaced'):
        sec = section(asm, fn)
        assert '[__arith_lhs' not in sec and 'ldx #$007E' not in sec and 'cmp #0' not in sec, (fn, sec)

    disp = section(asm, 'local_far_displaced')
    assert 'lda a:$000A,x' in disp and 'lda a:$0001,x' in disp and 'lda #$000A' not in disp and 'dex' in disp, disp

    # ROM + near local must retain far addressing to read banked ROM safely
    mixed = section(asm, 'local_far_mixed_rom')
    assert '[__arith_lhs' in mixed or 'bankbyte' in mixed, mixed

    # Inlined slot_hash / deref_byte must narrow near arguments without null check; ROM read must still read banked
    cinl = section(asm, 'call_inline_narrowed')
    assert 'ldx #$007E' not in cinl and 'cmp #0\n    beq' not in cinl, cinl
    assert 'f:_rom_bytes' in cinl, cinl

    # Non-null proven pointers omit the runtime NULL branch when converting to __far
    for fn in ('nonnull_after_deref', 'nonnull_after_guard'):
        sec = section(asm, fn)
        assert 'ldx #$007E' in sec or 'pea $007E' in sec, (fn, sec)
        assert 'ldx #$0000\n    cmp #0\n    beq' not in sec, (fn, sec)

    # Genuinely nullable pointers MUST preserve the runtime NULL check
    for fn in (
        'nullable_passthrough',
        'nullable_join',
        'nullable_and_rhs_clear',
        'nullable_or_neg_clear',
        'nullable_choose_clear',
        'nullable_land_expr_clear',
    ):
        sec = section(asm, fn)
        assert 'cmp #0\n    beq' in sec and 'ldx #$007E' in sec, (fn, sec)

    support.emulate(rom, labels, 0)
    print('PASS near7e far: local far narrowing, inline low-word/deref narrowing, and known_nonnull check elimination')


if __name__ == '__main__':
    main()
