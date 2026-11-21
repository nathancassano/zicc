"""C23 binary inclusion syntax, expansion, probing and diagnostics."""
import os
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'embed-check'
spec=importlib.util.spec_from_file_location('pp', ROOT/'tests/check-preprocessor.py')
pp=importlib.util.module_from_spec(spec);spec.loader.exec_module(pp)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    driver=pp.build_driver(OUT)
    (OUT/'bytes.bin').write_bytes(bytes([0,1,127,128,255,13,10,26]))
    (OUT/'empty.bin').write_bytes(b'')
    (OUT/'nested').mkdir(exist_ok=True)
    (OUT/'nested/resource.bin').write_bytes(b'Q')
    (OUT/'nested/fixture.h').write_text('#embed "resource.bin"\n')
    cases={
        'bytes':('#embed "bytes.bin"\n','0,1,127,128,255,13,10,26'),
        'angle':('#embed <bytes.bin> limit(2)\n','0,1'),
        'literal_name':('#define bytes ignored\n#embed <bytes.bin> limit(1)\n','0'),
        'macros':('#define FILE "bytes.bin"\n#define N (1+2)\n#define P 41,\n#embed FILE __limit__(N) __prefix__(P) __suffix__(,42)\n','41,0,1,127,42'),
        'empty':('#embed "empty.bin" prefix(1,) suffix(,2) if_empty(3,4)\n','3,4'),
        'zero':('#embed "bytes.bin" limit(0) if_empty(99)\n','99'),
        'long_limit':('#embed "bytes.bin" limit(18446744073709551615ULL)\n','0,1,127,128,255,13,10,26'),
        'no_tokens':('before\n#embed "empty.bin"\nafter\n','before after'),
        'balanced':('#embed "bytes.bin" limit(1) prefix(f({1,2},[3]),)\n','f({1,2},[3]),0'),
        'relative_header':('#include "nested/fixture.h"\n','81'),
        'inactive':('#if 0\n#embed "missing.bin"\n#endif\nright\n','right'),
        'probe':('''#ifdef __has_embed
#if defined(__has_embed) && __has_embed("bytes.bin") == __STDC_EMBED_FOUND__ && __has_embed("empty.bin") == __STDC_EMBED_EMPTY__ && __has_embed("bytes.bin" limit(0)) == 2 && __has_embed("missing.bin") == __STDC_EMBED_NOT_FOUND__ && !__has_embed("bytes.bin" vendor::thing({1,[2]}))
right
#endif
#endif
''','right'),
        'self_probe':('#if __has_embed(__FILE__ limit(1)) == 1 && __LINE__ == 1\nright\n#endif\n#if 0\nwrong\n#elifdef __has_embed\nalso\n#endif\n','right also'),
        'probe_macros':('#define F "bytes.bin"\n#define N 0\n#if __has_embed(F limit(N)) == 2\nright\n#elif __has_embed("missing.bin")\nwrong\n#endif\n','right'),
    }
    report={}
    def invoke(name,source):
        file=OUT/(name+'.c');file.write_text(source)
        result=subprocess.run([driver,file,OUT],capture_output=True,text=True,timeout=15)
        return result
    for name,(source,expected) in cases.items():
        result=invoke(name,source)
        assert result.returncode==0,(name,result.stderr)
        assert pp.body(result.stdout)==pp.body(expected),(name,result.stdout)
        report[name]='PASS'
    failures={
        'missing':('#embed "missing.bin" if_empty(0)\n','cannot open'),
        'unsupported':('#embed "bytes.bin" vendor::thing(1)\n','unsupported embed'),
        'negative':('#embed "bytes.bin" limit(-1)\n','negative embed'),
        'duplicate':('#embed "bytes.bin" limit(1) __limit__(2)\n','duplicate'),
        'defined':('#embed "bytes.bin" limit(defined(X))\n','defined is forbidden'),
        'defined_macro':('#define D defined\n#embed "bytes.bin" limit(D(X))\n','defined is forbidden'),
        'delimiter':('#embed "bytes.bin" prefix([)])\n','mismatched'),
        'unclosed':('#embed "bytes.bin" suffix(1\n','unterminated'),
        'no_clause':('#embed "bytes.bin" limit\n',"expected '('"),
        'empty_limit':('#embed "bytes.bin" limit()\n','expected operand'),
        'float_limit':('#embed "bytes.bin" limit(1.5)\n','invalid integer'),
        'zero_divisor':('#embed "bytes.bin" limit(1/0)\n','division by zero'),
        'extra_limit':('#embed "bytes.bin" limit(1 2)\n','unexpected token'),
        'outside_probe':('int x=__has_embed("bytes.bin");\n','only allowed'),
        'too_deep':('#embed \"bytes.bin\" prefix('+('('*66)+'1'+(')'*66)+')\n','nesting exceeds'),
        'bad_probe':('#if __has_embed("bytes.bin" limit(-1))\n#endif\n','negative embed'),
    }
    for name,(source,error) in failures.items():
        result=invoke(name,source)
        assert result.returncode!=0 and error in result.stderr,(name,result.stderr)
        report[name]='rejected'
    # Inferred arrays use the normal numeric initializer and preserve NUL/high bytes
    file=OUT/'compiled.c';file.write_text('const unsigned char data[]={\n#embed "bytes.bin"\n};\nconst int ordinary[]={2,3,4};\nint main(void){return sizeof(data)+sizeof(ordinary);}\n')
    with file.open('a') as stream:
        stream.write('const unsigned char nested[]={\n#include "nested/fixture.h"\n};\n'
                     '#if __has_embed("missing.bin")\n#error unexpected resource\n#endif\n')
    deps = OUT/'compiled.deps'
    result=subprocess.run([ROOT/'build/zicc.exe',file,'-o',OUT/'compiled.s',
                           '-I',OUT,'--dependencies',deps],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert {(line[0], Path(line[2:]).relative_to(OUT).as_posix()) for line in deps.read_text().splitlines()} == {
        ('+', 'bytes.bin'), ('+', 'nested/fixture.h'), ('+', 'nested/resource.bin'), ('-', 'missing.bin'),
    }
    asm=(OUT/'compiled.s').read_text()
    assert '.segment "EMBED"' in asm and '$00,$01,$7F,$80,$FF,$0D,$0A,$1A' in asm
    assert '.segment "RODATA"' in asm and '$02,$00,$03,$00,$04,$00' in asm
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: {len(cases)} embed expansions/probes; {len(failures)} diagnostics; inferred arrays')


if __name__=='__main__':main()
