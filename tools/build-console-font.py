"""Pack the visible console glyphs as one 8-bit mask per row."""
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / 'assets/console'
source = (ASSETS / 'ascii8x8.2bpp').read_bytes()
assert len(source) == 128 * 16
assert source[::2] == source[1::2]
assert not any(source[:ord('!') * 16] + source[(ord('~') + 1) * 16:])
(ASSETS / 'ascii8x8.1bpp').write_bytes(source[ord('!') * 16:(ord('~') + 1) * 16:2])
