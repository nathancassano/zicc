"""Check byte and word operations, register width changes, unused saves, bit masks and stores of zero."""
import os
import importlib.util
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'width-masks-check'
SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT

SOURCE = r'''
unsigned char arr[8];
unsigned char flags[8];
unsigned char bglobal;
unsigned g1, g2, g3;
unsigned scratch_out;
unsigned gidx;

void set_byte(unsigned i, unsigned char v) { arr[i] = v; }
void set_bit(unsigned i) { flags[i] |= 0x20U; }
void clear_bit(unsigned i) { flags[i] &= 0xDFU; }
void zero_indexed_byte(unsigned i) { arr[i] = 0; }
unsigned pack_high(unsigned x) { return (x & 0x00FFU) << 8; }
unsigned fold_shift_mask(unsigned x) { return ((x & 0xFF00U) << 1) & 0x2200U; }

unsigned bank_check(unsigned bank_word) {
    unsigned bank = bank_word & 0x00FFU;
    if (bank == 0x7EU || bank == 0x7FU || (bank & 0x7FU) < 0x40U)
        return 1;
    return 0;
}

void reset_all(void) {
    bglobal = 0;
    g1 = 0;
    g2 = 0;
    g3 = 0;
}

__noinline unsigned sink(unsigned a) { return a + 1U; }
unsigned ping_then_zero(unsigned i) {
    unsigned r = sink(i);
    scratch_out = 0;
    return r;
}

unsigned zero_after_m8_copy(unsigned v) {
    unsigned tmp = 0;
    scratch_out = 0;
    bglobal = (unsigned char)v;
    return v ? tmp : 7U;
}

void bridge_m_invariant(void) {
    bglobal = 0;
    flags[gidx] = 0;
}

int main(void) {
    unsigned k;
    reset_all();
    if (bglobal || g1 || g2 || g3) return 1;
    set_byte(3, 0xABU);
    if (arr[3] != 0xABU) return 2;
    flags[2] = 0x5AU;
    set_bit(2);
    if (flags[2] != 0x7AU) return 3;
    clear_bit(2);
    if (flags[2] != 0x5AU) return 4;
    zero_indexed_byte(3);
    if (arr[3] != 0) return 5;
    if (pack_high(0x1234U) != 0x3400U) return 6;
    if (fold_shift_mask(0xFFFFU) != 0x2200U || fold_shift_mask(0x1100U) != 0x2200U || fold_shift_mask(0x00FFU) != 0U) return 7;
    if (!bank_check(0x127EU) || !bank_check(0x997FU) || !bank_check(0xFF05U) || bank_check(0x0045U)) return 8;
    scratch_out = 99U;
    k = ping_then_zero(10U);
    if (k != 11U || scratch_out != 0) return 9;
    scratch_out = 55U;
    if (zero_after_m8_copy(0x0142U) != 0 || bglobal != 0x42U || scratch_out != 0) return 10;
    gidx = 5;
    flags[5] = 9;
    bglobal = 7;
    bridge_m_invariant();
    if (bglobal != 0 || flags[5] != 0) return 11;
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

    cfile, rom, labels = support.compile_case('width_masks', source)
    asm = cfile.with_suffix('.s').read_text()

    sb = section(asm, 'set_byte')
    assert 'phx' not in sb and 'plx' not in sb, sb
    assert 'and #$00FF' not in sb, sb

    sbit = section(asm, 'set_bit')
    assert 'phx' not in sbit and 'plx' not in sbit, sbit
    assert 'ora #$20' in sbit and 'and #$00FF' not in sbit, sbit

    cbit = section(asm, 'clear_bit')
    assert 'phx' not in cbit and 'plx' not in cbit, cbit
    assert 'and #$DF' in cbit and 'and #$00FF' not in cbit, cbit

    zb = section(asm, 'zero_indexed_byte')
    assert 'lda #$0000' not in zb and 'stz a:.loword(_arr+$0000),x' in zb, zb

    ph = section(asm, 'pack_high')
    assert 'xba' in ph and 'and #$00FF' not in ph and 'and #$FF00' in ph, ph

    fsm = section(asm, 'fold_shift_mask')
    assert 'and #$FF00' not in fsm and 'and #$2200' in fsm, fsm

    bc = section(asm, 'bank_check')
    assert bc.count('and #$00FF') <= 1, bc

    ra = section(asm, 'reset_all')
    assert 'lda #$0000' not in ra and 'stz ' in ra, ra

    zmc = section(asm, 'zero_after_m8_copy')
    assert 'stz a:.loword(_scratch_out)' in zmc, zmc

    pz = section(asm, 'ping_then_zero')
    assert 'stz a:.loword(_scratch_out)' in pz and 'lda #$0000' not in pz, pz

    bmi = section(asm, 'bridge_m_invariant')
    assert bmi.count('sep #$20') == 1 and bmi.count('rep #$20') == 1, bmi

    support.emulate(rom, labels, 0)
    print('PASS width masks: dead X save, .a8 RMW, demanded masks, multi-STZ, M-invariant bridge')


if __name__ == '__main__':
    main()
