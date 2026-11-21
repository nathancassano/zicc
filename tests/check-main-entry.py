"""SNES startup accepts int/void main while preserving its entry-only ABI."""
import importlib.util
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('entry_support', ROOT/'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
OUT = support.OUT


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in [('fallthrough', 'finished=123;'),
                       ('explicit', 'int local=121; finished=local+2; return;')]:
        _, rom, labels = support.compile_case('void_main_'+name,
            'volatile int finished; void main(void){'+body+'}')
        checks = f"""
emu.addMemoryCallback(function()
    require_value(entered,'exit before void main')
    require_value(emu.read16({labels['finished']},emu.memType.snesMemory,false)==123,'void main side effect')
    require_value(emu.getState()['cpu.sp']==0x04ff,'void main stack balance')
    require_value(emu.getState()['cpu.dbr']==0x7e,'void main DBR')
    done=true
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
"""
        support.emulate(rom, labels, extra_checks=checks, embedded=True)
    invalid = [
        'long main(void){return 0L;}',
        'char main(void){return 0;}',
        'float main(void){return 0.0f;}',
        'int *main(void){return 0;}',
        'void main(int argc){}',
        'int main(int argc){return argc;}',
    ]
    for i, source in enumerate(invalid):
        path=OUT/f'invalid_main_{i}.c'
        path.write_text(source)
        result=subprocess.run([str(ROOT/'build/zicc.exe'), str(path), '-o',
                               str(path.with_suffix('.s'))], capture_output=True, text=True)
        assert result.returncode and 'main must be int main(void) or void main(void)' in result.stderr, result.stderr
    path=OUT/'call_void_main.c'
    path.write_text('void main(void){} void call(void){main();}')
    result=subprocess.run([str(ROOT/'build/zicc.exe'), str(path), '-o',
                           str(path.with_suffix('.s'))], capture_output=True, text=True)
    assert result.returncode and 'startup-only entry ABI' in result.stderr, result.stderr
    print('PASS void main fallthrough/return execution, stack/DBR and invalid entry declarations')


if __name__ == '__main__':
    main()
