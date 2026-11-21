# Full verification before the byte-shuffle milestone

The full run passed 26 of 27 suites. One test expected the interrupt handler to save a temporary value it no longer wrote. The corrected test passed on its own and still checked the old instruction sequence with the optimization disabled.

The isolated homebrew-samples checkout was verified after the imported demos,
main-entry/signed-char compatibility fixes, direct indexed operands, X/Y index
retention and known-value selection. The original checkout was not changed.

`make check` used the default 20 hardware-thread workers and emulator cache.
Evidence: `build/check/20261108T103615.710225Z/summary.json` and adjacent logs.
The full run took 417.90 seconds: 26/27 suites passed, with 324 cached and 1,028
emulated runs. Arithmetic coverage retained all 200,873 cases and assertions.
The compiler was unchanged throughout the run and the follow-up.

The sole failure was an exact scratch-save expectation in `interrupt-scratch`.
Direct indexed addition now emits `ADC table,X`, avoiding the former RHS
workspace write. `software_break` therefore correctly saves only $E0, rather than
$E0 and $E4. Its 32-bit shift still writes $E0. The assertion was updated to the
observed minimal set; a new `--no-indexed-operands` control retains explicit
coverage of the original sparse $E0/$E4 save/restore contract.

`python tests/check-compiler.py --part interrupt-scratch` then passed, including
independent helper-write auditing and NTSC/PAL preservation in all four interrupt
width modes. Evidence: `build/interrupt-scratch-check/results.json` and retained
assembly, ROMs and logs in that directory. No compiler behavior was changed to
resolve the stale expectation. Unaffected full-run passes were retained; no
coverage remains outstanding from that verification run.

The BouncingSprites state/pixel checks and repeated 600-logical-update timing
results are in [known-values.md](known-values.md). Subsequent optimization work
starts from this verified state and requires its own validation.
