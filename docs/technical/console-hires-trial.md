# 512x224 console layout and validation

The default console fits 64 characters across and 28 rows down. It draws 8 by 8 pixel letters on a noninterlaced 512 by 224 pixel Mode 5 display. At the same screen width the letters look half as wide and keep their height. Programs use the same `printf` and `fflush` calls.

The trial used the compiler with discarded aggregate-result elision and destination-load scheduling. Its build was saved under `C:/snesdev/compiler/build/console-hires-trial`. The `build/` paths below are relative to that checkout.

## Layout

Mode 5 tilemap entries select 16x8 pairs. BG1 supplies even character columns
using 4bpp glyph/transparent pairs; BG2 supplies odd columns using 2bpp pairs.
BG2 is shifted right eight hires pixels: HOFS is -4 because its horizontal
scroll units correspond to two hires pixels. Both layers appear on both main
and sub screens. The existing font's shapes and colors are preserved.

The trial's font generator derived both layers from `assets/console/ascii8x8.2bpp`.
BG1 font bytes occupy VRAM $0000-$1fff; BG2 occupies $2000-$2fff.
The maps occupy $6000-$67ff and $6800-$6fff. These are byte addresses.
The two WRAM shadow maps are contiguous, even columns first, with glyph tile
indices equal to twice ASCII. The logical cursor/origin use 128 bytes per row.
Scrolling clears both parity maps and presents both scroll registers together.
Each register's two scroll writes remain adjacent because the PPU shares a latch.

## Cost relative to baseline prompt

| Resource | Baseline | Trial | Change |
| --- | ---: | ---: | ---: |
| Visible character cells | 896 | 1,792 | +896 |
| WRAM shadow maps | 2,048 B | 4,096 B | +2,048 B |
| Console BSS excluding maps | 90 B | 94 B | +4 B |
| Font ROM/VRAM data | 2,048 B | 12,288 B | +10,240 B |
| Console CODE | 1,662 B | 1,743 B | +81 B |
| Full-map DMA payload | 2,048 B | 4,096 B | +2,048 B |
| Prompt cartridge size | 65,536 B | 65,536 B | unchanged |

The trial stored the pre-expanded font in ROM. The current implementation
stores 752 bytes of glyph masks and expands them during forced blank. The
VRAM layout above still applies. See the [current font format](../../assets/console/readme.md).
Both backgrounds are occupied by the console. As before, linking the default
console owns its video setup; this does not add a gameplay overlay API.

## Verification and evidence

The unmodified baseline passed `make all smoke` and `python tests/check-prompt.py`
before edits. Its prompt ROM, map, console object, screenshot and NTSC/PAL
presentation reports are retained under `build/hires-evidence/baseline/`.

The trial tests check all rendered pixels of the prompt, scrolling output,
a 193-character sequence with varied adjacent glyphs, a 1,791-character page, and 4,517 characters
that wrap through the entire circular map. They check WRAM, VRAM, both font
layouts, palette, printf results, ABI, VBlank-only DMA, clean/repeated writes,
both scroll registers, busy mutation, and delayed presentation on NTSC/PAL.
Mesen's raw hires screenshots are 512x448: every pair of rows is asserted
identical, then reduced to the native 512x224 artifact without filtering.
The tests also assert Mode 5 with SETINI zero (no interlace or overscan).

The 4 KiB presentation budget requires entry before line 228 NTSC / 278 PAL.
A user NMI deliberately delays presentation to line 227 / 277; both full maps
and the scroll update complete at line 257 / 307, still within VBlank.
Later user NMIs defer the update. Timing reports and raw Lua/logs are under
`build/console-check/{ntsc,pal}/`; native screenshots are under
`build/prompt-check/*-native.png`.

Full verification passed: 27/27 suites, 76 jobs and 200,873 arithmetic cases
in 579.69 seconds. Command: `make check` with the hardware-thread default (20 workers),
logs under `build/check/20261107T101429.372997Z/`. Final outcome is also recorded
in `build/hires-evidence/results.json` after completion.

`make dhrystone` and `python tools/run-dhrystone.py` also passed on NTSC and
PAL, retaining executed-work assertions and checking every final screen pixel
with the updated 64-column verifier. Evidence is under `build/dhrystone-run/`.
The readable demo ROM and pixel-verified screenshots are under
`build/hires-evidence/demo/`, reproduced with
`python build/hires-evidence/render-demo.py`.

Additional banked-ROM and volatile/NMI checks exercise consumers that inspect
the console's shadow maps. Their expected text decoding is updated for the two
parity maps and doubled glyph tile indices.

README.md and the font documentation describe the adopted layout. Validation
here is emulator-based, with no physical-console run.
