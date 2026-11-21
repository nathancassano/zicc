"""Compute the expected binary64 result for each C rounding mode using exact fractions.

This module does not use the host floating environment. It is shared by
directed-rounding runtime tests; inputs and outputs are binary64 bit patterns.
"""
from fractions import Fraction

NEAREST = 0
DOWNWARD = 1
UPWARD = 2
TOWARDZERO = 3
SIGN = 1 << 63
INF = 0x7ff0000000000000
MAX_FINITE = 0x7fefffffffffffff
FRACTION = (1 << 52) - 1


def finite_fraction(bits):
    """Return the exact finite value represented by a binary64 bit pattern."""
    exponent = (bits >> 52) & 0x7ff
    significand = bits & FRACTION
    if exponent == 0x7ff:
        raise ValueError('nonfinite binary64')
    if exponent:
        significand |= 1 << 52
        shift = exponent - 1023 - 52
    else:
        shift = -1074
    value = (Fraction(significand << shift) if shift >= 0
             else Fraction(significand, 1 << -shift))
    return -value if bits & SIGN else value


def _floor_log2(numerator, denominator):
    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        if numerator < denominator << exponent:
            exponent -= 1
    elif numerator << -exponent < denominator:
        exponent -= 1
    return exponent


def _rounded_integer(numerator, denominator, mode, negative):
    whole, remainder = divmod(numerator, denominator)
    if not remainder:
        return whole
    if mode == NEAREST:
        twice = remainder * 2
        increment = twice > denominator or (twice == denominator and whole & 1)
    elif mode == DOWNWARD:
        increment = negative
    elif mode == UPWARD:
        increment = not negative
    elif mode == TOWARDZERO:
        increment = False
    else:
        raise ValueError('invalid rounding mode')
    return whole + int(increment)


def _overflow(mode, negative):
    infinite = (mode == NEAREST or
                (mode == UPWARD and not negative) or
                (mode == DOWNWARD and negative))
    return (SIGN if negative else 0) | (INF if infinite else MAX_FINITE)


def round_fraction(value, mode, zero_negative=False):
    """Round a finite Fraction to binary64 under the selected direction."""
    if mode not in (NEAREST, DOWNWARD, UPWARD, TOWARDZERO):
        raise ValueError('invalid rounding mode')
    if not value:
        return SIGN if zero_negative else 0
    negative = value < 0
    magnitude = -value if negative else value
    numerator, denominator = magnitude.numerator, magnitude.denominator
    exponent = _floor_log2(numerator, denominator)
    if exponent > 1023:
        return _overflow(mode, negative)
    sign = SIGN if negative else 0
    if exponent < -1022:
        significand = _rounded_integer(numerator << 1074, denominator,
                                       mode, negative)
        # Rounding can produce the least normal value
        return sign | significand
    shift = 52 - exponent
    if shift >= 0:
        numerator <<= shift
    else:
        denominator <<= -shift
    significand = _rounded_integer(numerator, denominator, mode, negative)
    if significand == 1 << 53:
        significand >>= 1
        exponent += 1
        if exponent > 1023:
            return _overflow(mode, negative)
    return sign | ((exponent + 1023) << 52) | (significand & FRACTION)


def add_finite(left, right, mode, subtract=False):
    """Round finite addition/subtraction, including IEEE signed-zero rules."""
    if subtract:
        right ^= SIGN
    result = finite_fraction(left) + finite_fraction(right)
    if result:
        return round_fraction(result, mode)
    left_zero = (left & ~SIGN) == 0
    right_zero = (right & ~SIGN) == 0
    if left_zero and right_zero and not ((left ^ right) & SIGN):
        negative = bool(left & SIGN)
    else:
        negative = mode == DOWNWARD
    return round_fraction(result, mode, zero_negative=negative)
