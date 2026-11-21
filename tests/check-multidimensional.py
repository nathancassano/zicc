"""Check arrays with several dimensions, including row pointers and arrays passed to functions."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'multidimensional-check'
SPEC = importlib.util.spec_from_file_location('support', ROOT/'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = (ROOT/'tests/multidimensional_cases.c').read_text()
    path, rom, labels = support.compile_case('semantics', source,
        extra_objects=[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables')])
    support.emulate(rom, labels, 0)
    assembly=(OUT/'semantics.s').read_text()
    loops=[]
    for name in ('across_row','down_column','nested_rows','nested_columns'):
        match=re.search(r'^_'+name+r':\n.*?^__size_'+name+r' = .*?$',assembly,re.M|re.S)
        assert match, name
        loops.append('## '+name+'\n\n```asm\n'+match.group(0)+'\n```\n')
    (OUT/'loop-assembly.md').write_text(
        '# How the compiler fills rows and columns\n\n'
        'Each example writes values into a two-dimensional array. The store instructions show how far apart the cells are in memory.\n\n'
        +'\n'.join(loops))
    host = OUT/'reference.exe'
    support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/W4','/O2',
                          '/Fo'+str(OUT/'reference.obj'),'/Fe'+str(host),path])
    support.run([host])
    rejected = {
        'const_parameter': 'int f(const int a[][3]){a[0][0]=1;return 0;}',
        'const_discard': 'const int a[2][3]={{1},{2}};int (*p)[3];int main(void){p=a;return 0;}',
        'const_typedef': 'typedef int M[2][3];const M a;int main(void){a[0][0]=1;return 0;}',
        'shape_assignment': 'int a[2][3];int (*p)[4];int main(void){p=a;return 0;}',
        'float_index': 'int a[2][3];int main(void){return a[1.0][0];}',
        'wrapped_product': 'char a[16384][16384][16];',
        'array_return': 'int f(void)[2][3];',
        'zero': 'int a[2][0];',
        'negative': 'int a[2][-1];',
        'overflow': 'int a[256][256];',
        'variable': 'int n; int a[2][n];',
        'inner_omitted': 'int f(int a[2][]);',
        'static_object_omitted': 'static int a[][3];',
        'void': 'void a[2][3];',
        'row_assignment': 'int a[2][3]; int main(void){a[0]=a[1];return 0;}',
        'shape_argument': 'int f(int a[][4]);int a[2][3];int main(void){return f(a);}',
        'double_pointer': 'int f(int **a);int a[2][3];int main(void){return f(a);}',
        'prototype': 'int f(int a[][3]);int f(int a[][4]);',
        'initializer': 'const int a[2][2]={{1,2,3},{4}};',
    }
    for name, text in rejected.items():
        cfile=OUT/('bad_'+name+'.c');cfile.write_text(text)
        result=subprocess.run([str(ROOT/'build/zicc.exe'),str(cfile),'-o',str(cfile.with_suffix('.s'))],
                              cwd=ROOT,capture_output=True,text=True,timeout=20)
        assert result.returncode and re.search(r':\d+:\d+: error:',result.stderr), (name,result.stderr)
    report=dict(target='PASS',host_reference='PASS',rejected=len(rejected),
                rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),
                compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest())
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: multidimensional target/MSVC semantics and '+str(len(rejected))+' diagnostics')


if __name__ == '__main__': main()
