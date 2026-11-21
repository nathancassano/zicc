# Third-party sources and notices

The [project license](../LICENSE) covers zicc. The imports below retain their
own credits and notices.

## Console font

The SNES console uses converted glyphs from libnds. The source bytes and the
libnds notice accompany the converted assets. See the
[font provenance and conversion details](../assets/console/readme.md).

## Dhrystone

The Dhrystone samples and their runner were archived. The
[original C 2.1 archive at Netlib](https://netlib.org/benchmark/dhry-c)
includes Reinhold P. Weicker's benchmark rules and source. Those materials
give no explicit redistribution terms, which the
[SiFive port's notice](https://raw.githubusercontent.com/sifive/benchmark-dhrystone/master/LICENSE)
also records. The archived 1.1 SNES port carries an MIT notice. The terms
for its underlying translation remained unverified after consulting
[Rick Richardson's 1986 source posting](https://groups.google.com/g/net.arch/c/MAJQXdd0A2g).
Historical reports continue to credit the benchmark and identify their inputs.

## Whetstone

The Whetstone import and its local console version were archived with the
SNES port's MIT notice and pinned file hashes. The eight-test workload matches
the C/C++ benchmark credited to
Roy Longbottom in the [Emscripten benchmark source](https://raw.githubusercontent.com/emscripten-core/emscripten/main/test/third_party/whets.c).
The redistribution terms for that earlier implementation remain unverified.
