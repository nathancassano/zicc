"""Linked debugger exports contain only objects/entries with source spelling."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import debug_symbols

OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'debug-symbols-check'


def run(*args):
    subprocess.run(list(map(str, args)), cwd=ROOT, check=True,
                   capture_output=True, text=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = OUT/'names.c'
    source.write_text('''volatile int value;
volatile int _value;
static volatile int hidden;
static int _helper(int x) { hidden=x; return hidden; }
__noinline int _function(int x) { return _helper(x)+_value; }
int main(void) { value=_function(3); value=value*_value; return value; }
''')
    native = OUT/'entries.s'
    native.write_text('''.setcpu "65816"
.segment "ZEROPAGE": zeropage
native_workspace: .res 4
native_ram_entry = native_workspace+1
.segment "CODE"
.import __function
.export native_entry, native_alias, metadata, entry_alias
metadata = $c00000
entry_alias := native_entry
native_entry:
native_alias:
    jsr private_call
    jsr native_ram_entry
    jsr .loword(__function)
    rtl
private_call:
    rts
.proc private_proc
    rts
.endproc
private_branch:
    rtl
''')
    for lto in (False, True):
        output = OUT/('lto.raw' if lto else 'normal.raw')
        run(sys.executable, ROOT/'tools/build-rom.py', source, '-o', output,
            '--assembly', native,
            *(['--lto'] if lto else ['--no-inline']))
        labels = output.with_suffix('.labels')
        symbols = debug_symbols.collect(labels)
        assert {'main', 'value', '_value'} <= symbols.keys(), symbols
        assert {'reset_vector', 'nmi_vector', 'irq_vector', 'brk_vector', 'cop_vector'} <= symbols.keys(), symbols
        assert {'private_call', 'private_proc', 'native_ram_entry', '__initialize_extra_ram', '__mul16'} <= symbols.keys(), symbols
        assert 'mul16' not in symbols, symbols
        assert '_function' in symbols and '__function' not in symbols, symbols
        assert any(name.endswith('names__hidden') for name in symbols), symbols
        assert symbols['native_entry'] == symbols['native_alias'], symbols
        assert not {'metadata', 'entry_alias', 'private_branch'} & symbols.keys(), symbols
        if not lto:
            assert '_function' in symbols and 'names___helper' in symbols, symbols
        assert all(not name.startswith(('__lto_', '_inlined_', '_zicc_'))
                   for name in symbols), symbols
        raw = labels.read_text()
        assert '__zicc_object_size_' in raw
        assert not any('object_size' in name or name.startswith(('cg_', 'return_'))
                       for name in symbols), symbols
        debug_symbols.write(labels, output.with_suffix('.sym'))
        run('powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            ROOT/'tools/labels-to-sym.ps1', '-InputPath', labels,
            '-OutputPath', output.with_suffix('.ps.sym'))
        assert output.with_suffix('.sym').read_bytes() == output.with_suffix('.ps.sym').read_bytes()
        assert ':_value' in output.with_suffix('.mlb').read_text()
        assert ':native_entry' in output.with_suffix('.mlb').read_text()
        assert ':native_alias' in output.with_suffix('.mlb').read_text()
        assert 'SnesPrgRom:00ffa4:nmi_vector' in output.with_suffix('.mlb').read_text()
    print('PASS debugger symbols: linked normal/LTO, source underscores, private objects, metadata exclusion, SYM/MLB')


if __name__ == '__main__':
    main()
