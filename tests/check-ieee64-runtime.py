"""Exercise assembly binary64 comparison, negation and binary32 widening."""
import os
import importlib.util
import json
import math
from pathlib import Path
import random
import re
import struct
import sys
from binary64_rounding_reference import (
    DOWNWARD, NEAREST, TOWARDZERO, UPWARD, add_finite, finite_fraction,
    round_fraction,
)
from fractions import Fraction

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compiler_check', ROOT/'tests/check-compiler.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
c.OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-runtime-check'
c.OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(0x1eee64)
MASK = (1 << 64) - 1


def words(value):
    return ','.join('$%04x' % ((value >> n) & 0xffff) for n in (0, 16, 32, 48))


def double(bits):
    return struct.unpack('<d', struct.pack('<Q', bits))[0]


def extend(bits):
    # Use Python to compute the expected bits when widening to binary64
    # Build NaNs by hand because platforms differ in how they quiet them
    if bits & 0x7f800000 == 0x7f800000 and bits & 0x007fffff:
        return ((bits & 0x80000000) << 32) | 0x7ff8000000000000 | ((bits & 0x007fffff) << 29)
    f = struct.unpack('<f', struct.pack('<I', bits))[0]
    return struct.unpack('<Q', struct.pack('<d', f))[0]


def int_double(bits, signed):
    n = bits - (1 << 32) if signed and bits & 0x80000000 else bits
    return struct.unpack('<Q', struct.pack('<d', float(n)))[0]


def double_bits(value):
    return struct.unpack('<Q', struct.pack('<d', value))[0]


def truncate(bits):
    sign = (bits >> 32) & 0x80000000
    fraction = bits & 0x000fffffffffffff
    if bits & 0x7ff0000000000000 == 0x7ff0000000000000 and fraction:
        return sign | 0x7fc00000 | (fraction >> 29)
    try:
        return struct.unpack('<I', struct.pack('<f', double(bits)))[0]
    except OverflowError:
        return sign | 0x7f800000


def addsub(a,b,subtract):
    x,y = double(a),double(b)
    z = x-y if subtract else x+y
    if math.isfinite(x) and math.isfinite(y):
        exact = add_finite(a, b, NEAREST, subtract=subtract)
        assert exact == double_bits(z), (hex(a), hex(b), subtract)
        return exact
    return 0x7ff8000000000000 if math.isnan(z) else double_bits(z)


def rounded_product_or_quotient(a, b, host_result, *, quotient=False):
    left, right = finite_fraction(a), finite_fraction(b)
    result = left / right if quotient else left * right
    exact = round_fraction(result, NEAREST, zero_negative=bool((a ^ b) >> 63))
    assert exact == double_bits(host_result), (hex(a), hex(b), quotient)
    return exact


def multiply(a,b):
    x, y = double(a), double(b)
    z = x*y
    if math.isfinite(x) and math.isfinite(y):
        return rounded_product_or_quotient(a, b, z)
    return 0x7ff8000000000000 if math.isnan(z) else double_bits(z)


def divide(a,b):
    x,y = double(a),double(b)
    if math.isnan(x) or math.isnan(y) or (x == 0 and y == 0) or (math.isinf(x) and math.isinf(y)):
        return 0x7ff8000000000000
    if y == 0:
        return ((a ^ b) & (1 << 63)) | 0x7ff0000000000000
    if math.isfinite(x) and math.isfinite(y):
        return rounded_product_or_quotient(a, b, x/y, quotient=True)
    return double_bits(x/y)


def check_rounding_reference():
    # Hand-derived expectations in nearest, downward, upward and toward-zero
    # order. Cover both signs at the normal, subnormal and overflow boundaries
    sign = 1 << 63
    one = 0x3ff0000000000000
    minimum_normal = 1 << 52
    maximum = 0x7fefffffffffffff
    infinity = 0x7ff0000000000000
    cases = [
        (1 + Fraction(1, 1 << 53), (one, one, one + 1, one)),
        (1 + Fraction(3, 1 << 53), (one + 2, one + 1, one + 2, one + 1)),
        (Fraction(1, 1 << 1075), (0, 0, 1, 0)),
        (Fraction((1 << 53) - 1, 1 << 1075),
         (minimum_normal, minimum_normal - 1, minimum_normal, minimum_normal - 1)),
        (Fraction((1 << 1024) - (1 << 970)),
         (infinity, maximum, infinity, maximum)),
        (Fraction(1 << 1024), (infinity, maximum, infinity, maximum)),
    ]
    modes = (NEAREST, DOWNWARD, UPWARD, TOWARDZERO)
    for value, (nearest, down, up, zero) in cases:
        assert tuple(round_fraction(value, mode) for mode in modes) == (nearest, down, up, zero)
        assert tuple(round_fraction(-value, mode) for mode in modes) == tuple(
            sign | bits for bits in (nearest, up, down, zero))
    for mode in modes:
        assert add_finite(one, sign | one, mode) == (sign if mode == DOWNWARD else 0)
        assert add_finite(sign, sign, mode) == sign


def vectors():
    check_rounding_reference()
    edge = [0, 1, 2, 0x000fffffffffffff, 0x0010000000000000,
            0x3ff0000000000000, 0x7fefffffffffffff, 0x7ff0000000000000,
            0x7ff0000000000001, 0x7ff8000000000000, 0x7fffffffffffffff,
            0x8000000000000000, 0x8000000000000001, 0x8010000000000000,
            0xbff0000000000000, 0xffefffffffffffff, 0xfff0000000000000,
            0xfff0000000000001, 0xfff8000000001234]
    pairs = [(a,b) for a in edge for b in edge]
    pairs += [(rng.getrandbits(64),rng.getrandbits(64)) for _ in range(400)]
    pairs += [(a,a) for a in (rng.getrandbits(64) for _ in range(100))]
    multiplication = pairs[:]
    for _ in range(320):
        ea = rng.randrange(1,2047)
        eb = max(1,min(2046,2046-ea+rng.randrange(-40,41)))
        a = (rng.getrandbits(1)<<63) | (ea<<52) | rng.getrandbits(52)
        b = (rng.getrandbits(1)<<63) | (eb<<52) | rng.getrandbits(52)
        multiplication.append((a,b))
    for _ in range(100):
        # Products straddling the subnormal/zero boundary
        ea = rng.randrange(2,1022)
        eb = max(1,1023-ea+rng.randrange(-55,4))
        a = (rng.getrandbits(1)<<63) | (ea<<52) | rng.getrandbits(52)
        b = (rng.getrandbits(1)<<63) | (eb<<52) | rng.getrandbits(52)
        multiplication.append((a,b))
    division = pairs[:]
    for _ in range(270):
        ea = rng.randrange(1,2047)
        eb = max(1,min(2046,ea+rng.randrange(-40,41)))
        division.append(((rng.getrandbits(1)<<63) | (ea<<52) | rng.getrandbits(52),
                         (rng.getrandbits(1)<<63) | (eb<<52) | rng.getrandbits(52)))
    for n in range(1,51):
        division.append((n | (rng.getrandbits(1)<<63),0x4000000000000000))
    for _ in range(100):
        ea = rng.randrange(1,1020)
        eb = min(2046,ea+1023+rng.randrange(-4,55))
        division.append(((rng.getrandbits(1)<<63) | (ea<<52) | rng.getrandbits(52),
                         (rng.getrandbits(1)<<63) | (eb<<52) | rng.getrandbits(52)))
    # Every subnormal leading-bit position on both sides of each operation
    # Use a normal operand that keeps multiplication finite and division
    # defined, including the smallest representable binary64 input
    multiplication_subnormal=[]
    division_subnormal=[]
    for bit in range(52):
        subnormal=1<<bit
        multiplication_subnormal.extend(((subnormal,0x7fe0000000000000),
                                        (0x7fe0000000000000,subnormal)))
        division_subnormal.extend(((subnormal,0x3ff0000000000000),
                                  (0x3ff0000000000000,subnormal)))
    arithmetic = pairs[:]
    # Close exponents and near-equal magnitudes force alignment, cancellation,
    # carry propagation and rounding rather than merely returning the larger
    for _ in range(300):
        a = rng.randrange(0x0010000000000000,0x7fd0000000000000)
        b = (a + rng.randrange(-10000,10001)) & 0x7fffffffffffffff
        arithmetic.append((a ^ (rng.getrandbits(1)<<63),b ^ (rng.getrandbits(1)<<63)))
    for _ in range(120):
        exponent = rng.randrange(54,2046)
        a = (exponent << 52) | rng.getrandbits(52)
        half_ulp = (exponent-53) << 52
        arithmetic.append((a ^ (rng.getrandbits(1)<<63),
                           half_ulp ^ (rng.getrandbits(1)<<63)))
    def cmp(a,b):
        x,y = double(a),double(b)
        return 2 if math.isnan(x) or math.isnan(y) else (x > y) - (x < y)
    inputs = edge + [rng.getrandbits(64) for _ in range(500)]
    fedge = [0,1,2,0x007fffff,0x00800000,0x3f800000,0x7f7fffff,
             0x7f800000,0x7f800001,0x7fc00000,0x7fffffff,0x80000000,
             0x80000001,0x80800000,0xbf800000,0xff7fffff,0xff800000,
             0xff800001,0xffc12345]
    # Powers of two and neighbouring subnormals exercise every normalization
    # distance, and random bit patterns cover signs/exponents/payloads
    fedge += [v for n in range(23) for v in (1<<n, (1<<n)+1, (1<<n)-1)]
    fedge += [rng.getrandbits(32) for _ in range(700)]
    integers = [0,1,2,3,0xffff,0x10000,0x7fffffff,0x80000000,0xffffffff]
    integers += [v & 0xffffffff for n in range(32) for v in (1<<n,(1<<n)-1,(1<<n)+1)]
    integers += [rng.getrandbits(32) for _ in range(600)]
    wide = [0,1,2,3,(1<<53)-1,1<<53,(1<<53)+1,
            (1<<63)-1,1<<63,(1<<64)-1]
    wide += [v & MASK for n in range(64) for v in (1<<n,(1<<n)-1,(1<<n)+1)]
    wide += [rng.getrandbits(64) for _ in range(600)]
    # Explicitly cover both sides of halfway and even/odd ties for each
    # integer-to-binary64 rounding distance
    for shift in range(1,12):
        base = (1 << 63) | (rng.getrandbits(52) << shift & ((1<<63)-1))
        half = 1 << (shift-1)
        wide += [(base+v) & MASK for v in (half-1,half,half+1)]
    small = [0.0, -0.0, 0.5, -0.5, 1.0, -1.0, 1.99, -1.99,
             2147483647.0, -2147483648.0, 2147483647.75, -2147483648.75]
    small += [rng.randrange(-2147483648,2147483647) + rng.choice((0.0,0.125,0.5,0.875)) for _ in range(600)]
    unsigned = [0.0, -0.0, -0.5, 1.99, 4294967295.0,4294967295.75]
    unsigned += [rng.randrange(0,4294967296) + rng.choice((0.0,0.125,0.5,0.875)) for _ in range(600)]
    wide_signed = [0.0,-0.0,0.5,-0.5,1.99,-1.99,float(-(1<<63)),
                   math.nextafter(float(1<<63),0),math.nextafter(float(-(1<<63)),0)]
    wide_signed += [float(rng.randrange(-(1<<63),(1<<63)-1024)) for _ in range(600)]
    wide_unsigned = [0.0,-0.0,-0.5,1.99,math.nextafter(float(1<<64),0)]
    wide_unsigned += [float(rng.randrange(0,(1<<64)-2048)) for _ in range(600)]
    narrowing = edge[:]
    # Midpoints and adjacent double values cover ties in both directions,
    # including float subnormal, normal and overflow boundaries
    for f in (0,1,2,0x007ffffe,0x007fffff,0x00800000,0x3f7fffff,
              0x3f800000,0x3f800001,0x7f7ffffe,0x7f7fffff):
        a = struct.unpack('<f',struct.pack('<I',f))[0]
        if f == 0x7f7fffff:
            b = math.ldexp(1.0,128)
        else:
            b = struct.unpack('<f',struct.pack('<I',f+1))[0]
        midpoint = (a+b)/2
        for x in (math.nextafter(midpoint, -math.inf),midpoint,math.nextafter(midpoint, math.inf)):
            narrowing.extend((double_bits(x),double_bits(-x)))
    narrowing += [rng.getrandbits(64) for _ in range(600)]
    for _ in range(100):
        f = rng.randrange(0,0x7f7fffff)
        a = struct.unpack('<f',struct.pack('<I',f))[0]
        b = struct.unpack('<f',struct.pack('<I',f+1))[0]
        midpoint = (a+b)/2
        for x in (math.nextafter(midpoint,-math.inf),midpoint,math.nextafter(midpoint,math.inf)):
            narrowing.append(double_bits(-x if rng.getrandbits(1) else x))
    return {
        'dcmp': [(a,b,cmp(a,b) & MASK) for a,b in pairs],
        'dneg': [(a,0,a ^ (1<<63)) for a in inputs],
        'fext32_64': [(a,0,extend(a)) for a in fedge],
        'sfloat64_32': [(a,0,int_double(a,True)) for a in integers],
        'ufloat64_32': [(a,0,int_double(a,False)) for a in integers],
        'sfloat64_64': [(a,0,double_bits(float(a-(1<<64) if a & (1<<63) else a))) for a in wide],
        'ufloat64_64': [(a,0,double_bits(float(a))) for a in wide],
        'fix64_32': [(double_bits(a),0,int(a) & 0xffffffff) for a in small],
        'ufix64_32': [(double_bits(a),0,int(a) & 0xffffffff) for a in unsigned],
        'fix64_64': [(double_bits(a),0,int(a) & MASK) for a in wide_signed],
        'ufix64_64': [(double_bits(a),0,int(a) & MASK) for a in wide_unsigned],
        'ftrunc64_32': [(a,0,truncate(a)) for a in narrowing],
        'dadd': [(a,b,addsub(a,b,False)) for a,b in arithmetic],
        'dsub': [(a,b,addsub(a,b,True)) for a,b in arithmetic],
        'dmul': [(a,b,multiply(a,b)) for a,b in multiplication],
        'ddiv': [(a,b,divide(a,b)) for a,b in division],
        'dmul_subnormal': [(a,b,multiply(a,b)) for a,b in multiplication_subnormal],
        'ddiv_subnormal': [(a,b,divide(a,b)) for a,b in division_subnormal],
    }


def check_environment():
    source = c.OUT/'environment.c'
    source.write_text(r'''
#include <fenv.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
union Bits { double d; unsigned long long bits; };
volatile union Bits x, y;
union Bits result;
volatile unsigned long long integer;
union FloatBits { float f; unsigned long bits; } narrow;
char text[32];

int main(void) {
    fenv_t saved;
    fexcept_t flags;
    int mode;
    if (fegetround() != FE_TONEAREST || fetestexcept(FE_ALL_EXCEPT)) return 1;
    if (!fesetround(4) || fegetround() != FE_TONEAREST) return 2;
    for (mode = FE_TONEAREST; mode <= FE_TOWARDZERO; ++mode) {
        if (fesetround(mode) || fegetround() != mode) return 3;
        x.bits = 0x3ff0000000000000ULL;
        y.bits = 0x3ca0000000000000ULL;
        feclearexcept(FE_ALL_EXCEPT);
        result.d = x.d + y.d;
        if (result.bits != 0x3ff0000000000000ULL + (mode == FE_UPWARD)) return 4;
        if (fetestexcept(FE_ALL_EXCEPT) != FE_INEXACT) return 5;
        result.d = x.d - x.d;
        if (result.bits != (mode == FE_DOWNWARD ? 0x8000000000000000ULL : 0ULL)) return 6;
        x.bits = 1;
        y.bits = 0x3fe0000000000000ULL;
        feclearexcept(FE_ALL_EXCEPT);
        result.d = x.d * y.d;
        if (result.bits != (mode == FE_UPWARD ? 1ULL : 0ULL)) return 7;
        if (fetestexcept(FE_ALL_EXCEPT) != (FE_INEXACT | FE_UNDERFLOW)) return 8;
        x.bits = 0x7fefffffffffffffULL;
        feclearexcept(FE_ALL_EXCEPT);
        result.d = x.d / y.d;
        if (result.bits != (mode == FE_DOWNWARD || mode == FE_TOWARDZERO
            ? 0x7fefffffffffffffULL : 0x7ff0000000000000ULL)) return 9;
        if (fetestexcept(FE_ALL_EXCEPT) != (FE_INEXACT | FE_OVERFLOW)) return 10;
        integer = 0x20000000000001ULL;
        result.d = (double)integer;
        if (result.bits != 0x4340000000000000ULL + (mode == FE_UPWARD)) return 11;
        x.bits = 0x3ff0000010000000ULL;
        narrow.f = (float)x.d;
        if (narrow.bits != 0x3f800000UL + (mode == FE_UPWARD)) return 12;
        feclearexcept(FE_ALL_EXCEPT);
        narrow.f = (float)16777217LL;
        if (narrow.bits != 0x4b800000UL + (mode == FE_UPWARD) ||
            fetestexcept(FE_ALL_EXCEPT) != FE_INEXACT) return 22;
        feclearexcept(FE_ALL_EXCEPT);
        feraiseexcept(FE_INVALID);
        if (((float)16777217ULL > 16777216.0f) != (mode == FE_UPWARD)) return 23;
        if ((-16777216.0f > (float)-16777217LL) != (mode == FE_DOWNWARD)) return 24;
        if (((float)-16777219LL == -16777220.0f) != (mode == FE_TONEAREST || mode == FE_DOWNWARD)) return 25;
        if (((float)18446744073709551615ULL != 0x1p64f) != (mode == FE_DOWNWARD || mode == FE_TOWARDZERO)) return 26;
        if (fetestexcept(FE_ALL_EXCEPT) != (FE_INVALID | FE_INEXACT)) return 27;
        feclearexcept(FE_ALL_EXCEPT);
        if ((float)18446744073709551615ULL > 0x1p64f ||
            fetestexcept(FE_ALL_EXCEPT) != FE_INEXACT) return 28;
        result.d = strtod("1.00000000000000011102230246251565404236316680908203125", 0);
        if (result.bits != 0x3ff0000000000000ULL + (mode == FE_UPWARD)) return 13;
        result.d = strtod("-0x1.00000000000008p0", 0);
        if (result.bits != 0xbff0000000000000ULL + (mode == FE_DOWNWARD)) return 14;
        x.bits = 0x4000000000000000ULL;
        result.d = sqrt(x.d);
        if (result.bits != 0x3ff6a09e667f3bccULL +
            (mode == FE_TONEAREST || mode == FE_UPWARD)) return 15;
        x.bits = 0xbff4000000000000ULL;
        sprintf(text, "%.1f", x.d);
        if (text[0] != '-' || text[1] != '1' || text[2] != '.' ||
            text[3] != (mode == FE_DOWNWARD ? '3' : '2') || text[4]) return 16;
    }
    fesetenv(FE_DFL_ENV);
    x.bits = 0x3ff0000000000000ULL;
    y.bits = 0;
    result.d = x.d / y.d;
    if (result.bits != 0x7ff0000000000000ULL ||
        fetestexcept(FE_ALL_EXCEPT) != FE_DIVBYZERO) return 17;
    fegetexceptflag(&flags, FE_ALL_EXCEPT);
    feholdexcept(&saved);
    if (fetestexcept(FE_ALL_EXCEPT) || flags != FE_DIVBYZERO) return 18;
    y.bits = 0x7ff8000000000000ULL;
    if (x.d < y.d || fetestexcept(FE_ALL_EXCEPT) != FE_INVALID) return 19;
    feupdateenv(&saved);
    if (fetestexcept(FE_ALL_EXCEPT) != (FE_INVALID | FE_DIVBYZERO)) return 20;
    fesetexceptflag(&flags, FE_ALL_EXCEPT);
    if (fetestexcept(FE_ALL_EXCEPT) != FE_DIVBYZERO) return 21;
    return 0;
}
''')
    for stage in (1, 2, 3, 4):
        raw = c.OUT/f'environment-{stage}.raw'
        c.run([sys.executable, ROOT/'tools/build-rom.py', source,
               '--stage', str(stage), '-o', raw], timeout=120)
        labels = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(
            r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        rom = raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
        c.emulate(rom, labels, 0)



def check_rom_default_rounding():
    source = c.OUT/'default-rounding.c'
    source.write_text('''
extern void abort(void);
int main(void) {
    if ((float)18446744073709551615ULL < 0x1p64f) abort();
    return 0;
}
''')
    foreign = c.OUT/'opaque-rounding.s'
    foreign.write_text('.segment "CODE"\n.export _foreign\n_foreign: rts\n')
    cache = c.OUT/'rounding-compile-cache'

    def build(tag, sources, extra=()):
        raw = c.OUT/f'{tag}.raw'
        c.run([sys.executable, ROOT/'tools/build-rom.py', *sources, *extra,
               '--compile-cache', cache, '-o', raw], timeout=120)
        allocation = json.loads(raw.with_suffix('.allocation.json').read_text())
        stage = Path(allocation['evidence'])/f"stage{allocation['stage']}"
        labels = {n.removeprefix('_'): int(a, 16) for a, n in re.findall(
            r'^al ([0-9A-Fa-f]+) \.(\S+)$', raw.with_suffix('.labels').read_text(), re.M)}
        rom = raw.with_suffix('.sfc')
        c.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
        hits = {Path(path).name for path in allocation['compile_cache_hits']
                if Path(path).parent == Path(stage.name)}
        return rom, labels, stage, hits

    read_mode = 'lda a:.loword(__fp_round_mode)'
    rom, labels, stage, _ = build('rounding-closed', [source])
    assert read_mode not in (stage/'0_default_rounding.s').read_text()
    flags = labels['_fp_exceptions'] & 0x1ffff
    c.emulate(rom, labels, 0, extra_checks=f'''
emu.addMemoryCallback(function()
    require_value(emu.read({flags},emu.memType.snesWorkRam,false)==16 and
                  emu.read({flags + 1},emu.memType.snesWorkRam,false)==0,'sticky FE_INEXACT')
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
''')

    cached_rom, _, _, hits = build('rounding-closed-cached', [source])
    assert cached_rom.read_bytes() == rom.read_bytes()
    assert {'0_default_rounding.s', '0_default_rounding.rounding.s'} <= hits

    rom, labels, stage, hits = build('rounding-opaque', [source], ['--assembly', foreign])
    assert '0_default_rounding.s' in hits
    assert read_mode in (stage/'0_default_rounding.s').read_text()
    c.emulate(rom, labels, 0)

    driver = c.OUT/'rounding-driver.c'
    driver.write_text('''
extern int set_mode(int);
extern int rounded_below(void);
extern int feclearexcept(int), feraiseexcept(int), fetestexcept(int);
int main(void) {
    for (int mode = 0; mode < 4; ++mode) {
        if (set_mode(mode) || feclearexcept(31) || feraiseexcept(1)) return 1;
        if (rounded_below() != (mode & 1) || fetestexcept(31) != 17) return 2;
    }
    return 0;
}
''')
    kernel = c.OUT/'rounding-kernel.c'
    kernel.write_text('''
extern int fesetround(int);
int set_mode(int mode) { return fesetround(mode); }
int rounded_below(void) {
    if ((float)18446744073709551615ULL < 0x1p64f) return 1;
    return 0;
}
''')
    rom, labels, stage, _ = build('rounding-runtime', [driver, kernel])
    assert read_mode in (stage/'1_rounding_kernel.s').read_text()
    c.emulate(rom, labels, 0)


def main():
    rows_by_name = vectors()
    workspace = c.OUT/'workspace.s'
    workspace.write_text('.exportzp __arith_lhs,__arith_rhs\n.segment "DP_SCRATCH": zeropage\n'
                         '__arith_lhs: .res 4\n__arith_rhs: .res 28\n')
    c.run([c.CC65/'ca65.exe', '-o', c.OUT/'workspace.o', workspace])
    objects = []
    for name in ('environment-state','environment','cmp','neg','extend','truncate','fromint32','toint32','fromint64','toint64','addsub','mul','div'):
        obj = c.OUT/(name+'.o')
        c.run([c.CC65/'ca65.exe', '--cpu','65816','-g','-o',obj,ROOT/'runtime/ieee64'/(name+'.s')])
        objects.append(obj)
    archive = c.OUT/'ieee64.a'
    archive.unlink(missing_ok=True)
    c.run([c.CC65/'ar65.exe','a',archive,*objects])
    _, baseline, _ = c.compile_case('baseline','int main(void){return 0;}')
    _, with_archive, labels = c.compile_case('baseline-archive','int main(void){return 0;}',extra_objects=[archive])
    assert baseline.read_bytes() == with_archive.read_bytes()
    assert not any('_'+n in labels for n in rows_by_name)
    assert '_fp_round_mode' not in labels and 'fegetround' not in labels
    _, flag_only, labels = c.compile_case(
        'flag-only', 'int main(void){return (float)16777217ULL > 16777216.0f;}',
        extra_objects=[archive])
    assert '_fp_raise' in labels and '_fp_round_mode' in labels
    assert 'fegetround' not in labels and '_fp_round_increment' not in labels
    c.emulate(flag_only, labels, 0)
    check_environment()
    check_rom_default_rounding()
    batched = ('dmul', 'ddiv')
    cases = {name: (name, rows) for name, rows in rows_by_name.items() if name not in batched}
    # Keep both corpora while leaving room for the helpers and startup code
    # in each single-bank LoROM fixture
    for operation in batched:
        rows = rows_by_name[operation]
        for first in range(0, len(rows), 1024):
            cases[f'{operation}-{first//1024+1}'] = (operation, rows[first:first+1024])
    for name, (operation, rows) in cases.items():
        helper_name=operation.removesuffix('_subnormal')
        assert len(rows)*24 < 32768
        lines = ['.setcpu "65816"','.a16','.i16','.importzp __arith_lhs',
                 '.import __'+helper_name,'.export _ieee64_probe, _ieee64_after','.segment "CODE"',
                 '_ieee64_probe:','    phy','    ldx #0','ieee64_loop:']
        for offset in range(0,16,2):
            lines += [f'    lda f:table+{offset},x',f'    sta z:__arith_lhs+{offset}']
        # All three helpers promise to preserve X and Y. Keep a saved index
        # independently in unused scratch and assert both registers afterwards
        lines += ['    stx z:__arith_lhs+30','    ldy #$5aa5']
        if name in ('dadd','dsub'):
            lines += ['    phx']
        lines += ['    jsr .loword(__'+helper_name+')','_ieee64_after:']
        if name in ('dadd','dsub'):
            lines += ['    plx']
        lines += ['    pha',
                  '    cpx z:__arith_lhs+30','    bne @bad_pushed',
                  '    cpy #$5aa5','    bne @bad_pushed','    pla']
        if name == 'dcmp':
            lines += ['    cmp f:table+16,x','    bne @bad']
        else:
            for offset in range(0,4 if name in ('fix64_32','ufix64_32','ftrunc64_32') else 8,2):
                lines += [f'    lda z:__arith_lhs+{offset}',f'    cmp f:table+{16+offset},x','    bne @bad']
        lines += ['    txa','    clc','    adc #24','    tax',f'    cpx #{len(rows)*24}',
                  '    bne ieee64_loop','    lda #0','    ply','    rts',
                  '@bad_pushed:','    pla','@bad:','    lda #1','    ply','    rts',
                  '.segment "RODATA"','table:']
        for a,b,v in rows:
            lines.append('    .word '+words(a)+','+words(b)+','+words(v))
        source = c.OUT/(name+'-driver.s')
        source.write_text('\n'.join(lines)+'\n')
        obj = source.with_suffix('.o')
        c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',obj,source])
        _,rom,labels = c.compile_case(name,'int ieee64_probe(void); int main(void){return ieee64_probe();}',
                                      extra_objects=[obj,c.OUT/'workspace.o',archive])
        group = ({'dadd','dsub'} if name in ('dadd','dsub') else
                 {'sfloat64_64','ufloat64_64'} if name in ('sfloat64_64','ufloat64_64') else
                 {'fix64_64','ufix64_64'} if name in ('fix64_64','ufix64_64') else
                 {'sfloat64_32','ufloat64_32'} if name in ('sfloat64_32','ufloat64_32') else
                 {'fix64_32','ufix64_32'} if name in ('fix64_32','ufix64_32') else {helper_name})
        assert {n for n in rows_by_name if not n.endswith('_subnormal') and '_'+n in labels} == group
        addr = labels['_'+helper_name]
        checks = f'''
local helper_calls=0
local began,subnormal_cycles,subnormal_calls=0,0,0
local reported=false
emu.addMemoryCallback(function() helper_calls=helper_calls+1; began=emu.getState()['cpu.cycleCount'] end,emu.callbackType.exec,{addr},{addr})
emu.addMemoryCallback(function() if helper_calls>{0 if name.endswith('_subnormal') else len(rows)} then subnormal_cycles=subnormal_cycles+emu.getState()['cpu.cycleCount']-began;subnormal_calls=subnormal_calls+1 end end,emu.callbackType.exec,{labels['ieee64_after']},{labels['ieee64_after']})
emu.addMemoryCallback(function() if reported then return end; reported=true; require_value(helper_calls=={len(rows)},'helper call count'); if subnormal_calls>0 then print('SUBNORMAL_CYCLES '..subnormal_cycles..' CALLS '..subnormal_calls) end end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
        c.emulate(rom,labels,0,extra_checks=checks)
        print(f'PASS {name}: {len(rows)} vectors',flush=True)

    # The banked builder changes runtime calls to long calls. Check both a
    # rounding helper and addition's internal helper calls in long-call stages
    caller = c.OUT/'banked.c'
    caller.write_text('int ieee64_probe(void); int main(void){return ieee64_probe();}')
    banked = {'ftrunc64_32','dadd','sfloat64_64','fix64_64','dmul','ddiv','dmul_subnormal','ddiv_subnormal'}
    for name, (operation, rows) in cases.items():
        if operation not in banked:
            continue
        helper_name=operation.removesuffix('_subnormal')
        original = (c.OUT/(name+'-driver.s')).read_text()
        for stage in (3,4):
            driver = c.OUT/f'banked-{name}-{stage}.s'
            text = original.replace('jsr .loword(__'+helper_name+')','jsl __'+helper_name)
            if stage == 4:
                text = text.replace('    rts\n','    rtl\n')
            driver.write_text(text)
            raw = c.OUT/f'banked-{name}-{stage}.raw'
            c.run([sys.executable,ROOT/'tools/build-rom.py',caller,'--assembly',driver,
                   '--stage',str(stage),'-o',raw],timeout=120)
            labels = {n.removeprefix('_'):int(a,16) for a,n in re.findall(
                r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
            rom = raw.with_suffix('.sfc')
            c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
            addr = labels['_'+helper_name]
            count = len(rows)
            checks = f'''
local helper_calls=0
emu.addMemoryCallback(function() helper_calls=helper_calls+1 end,emu.callbackType.exec,{addr},{addr})
emu.addMemoryCallback(function() require_value(helper_calls=={count},'banked helper calls') end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
            c.emulate(rom,labels,0,extra_checks=checks)
            print(f'PASS banked stage {stage}: {count} {name} vectors',flush=True)


if __name__ == '__main__':
    main()
