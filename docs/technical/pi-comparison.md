# Supplied PI ROM and standard C comparison

The four ROMs run the same digit calculation. Each passed two fresh runs on an emulated NTSC SNES. Each repeated clock interval, output stream, work-array hash and update count agrees. The original ROM is used byte-for-byte from the ZIP. New builds use identical driver/kernel/console source bytes, separate compilation and no LTO. Stock VBCC is vbcc65816_r2 with `-O3 -msfp4`.

## Completion time

Display completion is measured from cold ROM startup to the first completed frame containing the stable final screen, after checking final VRAM. Calculation/output time starts at calculate_pi entry and ends on its return; it includes per-digit console calls but excludes setup and final fflush. Seconds use nominal NTSC 21,477,272 master clocks/s.

| ROM | Calculation/output master clocks | Calculation/output seconds | Boot to completed display frame, clocks | Display seconds | Clock wraps observed |
| --- | ---: | ---: | ---: | ---: | ---: |
| original | 16,931,028,338 | 788.323039 | 16,933,380,080 | 788.432538 | 3 |
| zicc-fast | 14,767,631,596 | 687.593452 | 14,773,817,340 | 687.881466 | 3 |
| zicc-slow | 17,076,605,654 | 795.101243 | 17,082,759,068 | 795.387751 | 3 |
| vbcc-slow | 16,412,404,774 | 764.175486 | 16,415,199,380 | 764.305605 | 3 |

The emulator exposes a wrapping clock counter. The harness extends it at every frame and each measured checkpoint, well before another wrap can occur. Earlier raw-counter measurements are retained as superseded evidence and are not used here. Final-screen capture hashes establish the earliest final frame within the settling window; later frames must remain identical. VBCC needs more than the initial three-frame capture window.

The original emits 897 characters: a leading zero plus 896 further digit characters. Its last character is stored on row 29, below the normal 28-row picture. Its reported display endpoint therefore means the final visible screen plus verified final VRAM, not simultaneous visibility of all 897 characters. zicc displays 64 columns; stock VBCC displays 32 columns and scrolls once. All streams and final arrays match exactly.

## Code size

| ROM | Application code bytes | All linked code bytes | ROM container bytes |
| --- | ---: | ---: | ---: |
| original | 1,169 | not available | 262,144 |
| zicc-fast | 661 | 5,836 | 65,536 |
| zicc-slow | 661 | 5,836 | 65,536 |
| vbcc-slow | 1,155 | 3,579 | 163,840 |

Code excludes assets, data and padding. The original application total comes from its four function-section sizes in main.obj, checked against matching linked instructions while allowing relocation bytes. No complete original linker map/runtime object set is supplied, so an original all-linked-code number is not inferred from ROM padding or symbol gaps. Current sizes use allocation manifests/linker maps. zicc has smaller application code but links more runtime code than stock VBCC.

## Arithmetic preservation and verification

The original quotient is read from the low byte of TCC temporary $18 after `%`. Portable divmodu expresses the same remainder and low-byte quotient using standard C `%` and `/`. It keeps the original 8-bit A/aux/nines and 16-bit intermediate arithmetic. Only display setup/palette calls and print_digit are replaced. The loop bound is passed unchanged as 896 by a separately compiled driver. No target computes pre-generated digits.

The supplied algorithm is numerically limited: only its first 42 digits after the leading zero match mathematical pi; the 43rd differs. An independent Decimal/Chudnovsky value confirms this. The benchmark preserves that behavior instead of repairing the calculation. A separately compiled MSVC host execution also matches all 897 output characters.

Every run requires 2,411,135 writes to A: 2,687 initialization bytes plus 896*(2,687+1) updates. Initialization values, opaque kernel argument, every emitted character, final 2,687-byte array, VRAM and stable final screenshots are checked. The original also requires 2,408,448 actual divmodu calls. zicc assembly shows inline divmodu substitutions and shared quotient/remainder production; VBCC retains separate remainder and quotient helper calls, with legal loop unrolling. Missing ABI calls are not used as evidence of removed calculations.

ROM speeds are asserted live: the supplied ROM is FastROM LoROM (MEMSEL=1, execution bank $80), zicc is HiROM (bank $C0, MEMSEL=1/0), and stock VBCC is SlowROM LoROM (bank $00). zicc speed variants differ only in the startup MEMSEL immediate, header speed bit and checksum. Pointer ABIs, near/far array access, register/frame conventions and console/runtime implementations differ. These are full-program comparisons; the calculation/output interval still includes each console implementation.

## Historical evidence

Historical run. Clock-counter and short capture-window attempts remain in raw-counter-run directories; final run1/run2 result.json files identify the accepted runs. Compiler sources were not changed for this sample, so verification compares all eight runs with the expected results from the host.

Evidence: `C:\snesdev\compiler\build\pi\comparison`. Full source, compiler, runtime, ROM, DLL and tool hashes, commands, assembly, allocation manifests, linker maps, Lua assertions, logs and screenshots are retained.
