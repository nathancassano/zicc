"""Enum frontend semantics, target representation, constant diagnostics and unchanged lowering."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'enum-check'
SPEC = importlib.util.spec_from_file_location('support', ROOT/'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT


def compile_only(name, source, succeeds=True):
    path = OUT/(name+'.c'); path.write_text(source)
    result = subprocess.run([str(ROOT/'build/zicc.exe'), str(path), '-o', str(OUT/(name+'.s'))],
                            cwd=ROOT, capture_output=True, text=True, timeout=20)
    if succeeds:
        assert result.returncode == 0, (name, result.stderr)
    else:
        assert result.returncode != 0 and re.search(r':\d+:\d+: error:', result.stderr), (name, result.stderr)
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = (ROOT/'tests/enum_cases.c').read_text()
    path, rom, symbols = support.compile_case('semantics', source,
        extra_objects=[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables')])
    support.emulate(rom, symbols, 0)
    assembly = (OUT/'semantics.s').read_text()
    for name in ('MODE_NEG','LOW','HIGH','MODE_COUNT','CHOICE'):
        assert not re.search(r'^_'+name+r':', assembly, re.M), name
    host = OUT/'reference.exe'
    support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/W4','/O2','/wd4127',
                         '/Fo'+str(OUT/'reference.obj'),'/Fe'+str(host),path])
    support.run([host])
    accepted = {
        'anonymous_typedef': 'typedef enum {Step_1,Step_2,Step_3,Step_4,Step_5} Step; Step x; int main(void){return Step_5-4;}',
        'reset_after_max': 'enum E{ MAX=32767, RESET=-2, NEXT }; enum E; int main(void){return NEXT+1;}',
        'constants': 'enum { X=(2+3)*4, Y=sizeof(int), Z=(int)32768L }; int main(void){return X-20;}',
        'namespaces': 'enum E {E}; struct S{enum {S=3} field;}; int main(void){return E;}',
        'tag_shadow': 'struct E{int x;}; int main(void){{enum E{A};enum E x=A;}return sizeof(struct E)-2;}',
        'typedef_repeat': 'typedef enum {A} E; typedef E E; int main(void){E x=A;return x;}',
        'parameter': 'enum E {A}; int f(enum E x){return x;} int main(void){return f(A);}',
        'local_alias_shadow': 'enum {X=2}; int main(void){{typedef int X; X value=3;}return X-2;}',
    }
    for name, text in accepted.items(): compile_only(name, text)
    rejected = {
        'positive_overflow': 'enum { A=32768 };',
        'negative_overflow': 'enum { A=-32769 };',
        'unsigned_overflow': 'enum { A=65535U };',
        'increment_overflow': 'enum { A=32767,B };',
        'expression_overflow': 'enum { A=32767+1 };',
        'duplicate_constant': 'enum {A,A};',
        'duplicate_other_enum': 'enum {A};enum {A};',
        'object_collision': 'int A; enum {A};',
        'later_object': 'enum {A}; int A;',
        'later_function': 'enum {A}; int A(void);',
        'typedef_collision': 'typedef int A;enum {A};',
        'later_typedef': 'enum {A};typedef int A;',
        'parameter_collision': 'int f(int A){enum {A};return 0;}',
        'unknown_tag': 'enum Missing object;',
        'forward': 'enum Missing;',
        'redefined_tag': 'enum E{A};enum E{B};',
        'enum_as_struct': 'enum E{A};struct E *p;',
        'struct_as_enum': 'struct E{int x;};enum E p;',
        'conflicting_tag_definition': 'struct E{int x;};enum E{A};',
        'empty': 'enum {};',
        'missing_comma': 'enum {A B};',
        'double_comma': 'enum {A,,B};',
        'float': 'enum {A=1.0};',
        'float_condition': 'enum {A=1.0?1:2};',
        'float_not': 'enum {A=!1.0};',
        'float_comparison': 'enum {A=1.0<2.0};',
        'float_arithmetic_cast': 'enum {A=(int)(1.0+2.0)};',
        'variable': 'int x;enum {A=x};',
        'division_zero': 'enum {A=1/0};',
        'invalid_shift': 'enum {A=1<<16};',
        'self_reference': 'enum {A=A};',
        'assignment': 'enum {A};int main(void){A=3;return 0;}',
        'address': 'enum {A};int main(void){int *p=&A;return 0;}',
        'increment': 'enum {A};int main(void){A++;return 0;}',
        'expired_constant': 'int main(void){{enum {LOCAL};}return LOCAL;}',
        'expired_tag': 'int main(void){{enum E{A};}enum E x;return 0;}',
        'expired_typedef': 'int main(void){{typedef enum {A} E;} E x;return 0;}',
        'unsigned_enum': 'unsigned enum E{A} x;',
        'unsigned_alias': 'typedef enum {A} E;unsigned E x;',
    }
    for name, text in rejected.items(): compile_only('bad_'+name, text, False)
    # Both forms must lower through the very same pre-existing integer codegen
    path = OUT/'lowering.c'
    bodies = [('enum', 'enum Mode {LOW=-2,HIGH=3}; enum Mode value; enum Mode f(enum Mode x){return x+HIGH;}'),
              ('int', 'int value; int f(int x){return x+3;}')]
    outputs = []
    for label, body in bodies:
        path.write_text(body+'\nint main(void){value=f(-2);return value-1;}\n')
        support.run([ROOT/'build/zicc.exe',path,'-o',OUT/(label+'.s')])
        text = (OUT/(label+'.s')).read_text()
        outputs.append(re.sub(r'^;[^\n]*\n','',text,flags=re.M))
    assert outputs[0] == outputs[1], 'enum lowering differs from signed int'
    report = dict(target='PASS',host_reference='PASS',accepted=len(accepted),rejected=len(rejected),
                  integer_lowering_identical=True,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
                  compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest())
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: enum target/MSVC semantics, {len(accepted)} acceptance and {len(rejected)} diagnostic cases, identical integer lowering')


if __name__ == '__main__': main()
