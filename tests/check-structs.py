"""Check structure layout, sizeof, storage alignment and unsupported uses."""
import os
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'struct-check'
spec = importlib.util.spec_from_file_location('support', Path(__file__).with_name('check-compiler.py'))
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

LAYOUT = '''struct Forward;
typedef struct Forward Forward;
struct Bytes { char a, b, c; };
struct Mixed { char lead; long wide; char tail; };
struct Item { unsigned short id; short quantity; unsigned long unit_price; };
struct Forward { char mark; struct Forward *next; };
struct Nested { char first; struct Bytes bytes; struct Item items[3]; char last; };
struct Six { char first; unsigned long value; };
struct Types { char a; int *pointer; float real; short words[3]; };
'''

RUNTIME = LAYOUT + '''
unsigned char before;
struct Mixed global;
unsigned char between;
struct Six globals[3];
unsigned char after;
__dpage unsigned char dp_before;
__dpage struct Six dp_array[2];
__dpage unsigned char dp_after;
int calls;
int side(void){++calls;return 0;}
int probe(int depth,int salt){
    unsigned char head=55;
    struct Six a[3];
    struct Mixed b;
    unsigned char tail=99;
    unsigned char *pa=(unsigned char *)a;
    unsigned char *pb=(unsigned char *)&b;
    int i;
    if(((unsigned int)a&1)||((unsigned int)&b&1))return 1;
    if(sizeof(a)!=18||sizeof(b)!=8||sizeof(a[side()])!=6||calls)return 2;
    for(i=0;i<18;++i)pa[i]=(unsigned char)(i+salt);
    for(i=0;i<8;++i)pb[i]=(unsigned char)(100+i);
    if(head!=55||tail!=99)return 3;
    if(depth&&probe(depth-1,salt+1))return 4;
    for(i=0;i<18;++i)if(pa[i]!=(unsigned char)(i+salt))return 5;
    for(i=0;i<8;++i)if(pb[i]!=(unsigned char)(100+i))return 6;
    return 0;
}
int main(void){
    struct Forward object;
    struct Forward *p=&object;
    struct Six *q=globals;
    int i=2;
    int unused=0;
    if(sizeof(struct Bytes)!=4||sizeof(struct Mixed)!=8||sizeof(struct Item)!=8)return 1;
    if(sizeof(struct Nested)!=32||sizeof(Forward)!=4||sizeof(struct Types)!=14)return 2;
    if(sizeof(struct Six[3])!=18||sizeof(struct Forward *)!=2||sizeof(*p)!=4)return 3;
    if(sizeof(struct Item *)!=2||sizeof(struct Six)!=6||sizeof(struct Six[2])!=12)return 4;
    if(((unsigned int)&global&1)||((unsigned int)globals&1)||((unsigned int)&object&1))return 5;
    if(((unsigned int)dp_array&1)||sizeof(dp_array)!=12)return 16;
    dp_before=44;dp_after=55;
    ((unsigned char *)dp_array)[0]=77;
    ((unsigned char *)dp_array)[11]=88;
    if(dp_before!=44||dp_after!=55)return 17;
    before=11;between=22;after=33;
    if((unsigned int)(q+i)-(unsigned int)q!=12)return 6;
    ++q;if((unsigned int)q-(unsigned int)globals!=6)return 7;
    if(before!=11||between!=22||after!=33)return 8;
    if(sizeof(struct Item[3])!=24||sizeof(struct Forward)!=4)return 9;
    {struct Item { char c; };if(sizeof(struct Item)!=2)return 10;}
    if(sizeof(struct Item)!=8)return 11;
    {struct Item;struct Item *opaque;if(sizeof(opaque)!=2)return 12;}
    if(sizeof(struct Item)!=8)return 13;
    if(sizeof(unused++)!=2||unused)return 14;
    if(probe(3,7))return 15;
    return 0;
}
'''

INVALID = {
    'duplicate': ('struct S { int a; char a; };', "duplicate member 'a'"),
    'redefined': ('struct S {int a;};struct S {int b;};', "redefinition of struct 'S'"),
    'recursive': ('struct S {struct S value;};', 'requires a complete object type'),
    'incomplete_member': ('struct S {struct Other value;};', 'requires a complete object type'),
    'incomplete_array': ('struct S {struct Other values[2];};', 'requires a complete object type'),
    'void_member': ('struct S {void value;};', 'requires a complete object type'),
    'empty': ('struct S {};', 'empty structs'),
    'incomplete_sizeof': ('int main(void){return sizeof(struct S);}', 'sizeof requires a complete object type'),
    'incomplete_local': ('int main(void){struct S x;return 0;}', 'local requires a complete type'),
    'incomplete_global': ('struct S x;', "global 'x' requires a complete object type"),
    'incomplete_index': ('struct S *p;int main(void){return sizeof(p[1]);}', 'pointer arithmetic requires a complete struct type'),
    'incomplete_step': ('struct S *p;int main(void){++p;return 0;}', 'pointer arithmetic requires a complete struct type'),
    'incomplete_add': ('struct S *p;int main(void){p=p+1;return 0;}', 'pointer arithmetic requires a complete struct type'),
    'incomplete_post': ('struct S *p;int main(void){p++;return 0;}', 'pointer arithmetic requires a complete struct type'),
    'compound_copy': ('struct S {int a;};int main(void){struct S a,b;a+=b;return 0;}', 'struct values are not implemented'),
    'initializer': ('struct S {int a;};struct T {int a;};int main(void){struct T a;struct S b=a;return 0;}', 'incompatible aggregate initializer'),
    'arithmetic': ('struct S {int a;};int main(void){struct S a;return a+1;}', 'struct values are not implemented'),
    'comparison': ('struct S {int a;};int main(void){struct S a;return a==a;}', 'struct values are not implemented'),
    'bitfield_width': ('struct S {int a:17;};', 'invalid bit-field width'),
    'missing_semicolon': ('struct S {int a};', "';' after struct member"),
    'missing_brace': ('struct S {int a;', "expected '}' in struct definition"),
    'large_sizeof': ('struct S {int x;};int main(void){return sizeof(struct S {long a[16383];}[2]);}', 'sizeof operand exceeds 130560 bytes'),
    'large': ('struct S {long a[32641];};', 'struct layout exceeds 130560 bytes'),
    'shadow_incomplete': ('struct S {int a;};int main(void){struct S;return sizeof(struct S);}', 'sizeof requires a complete object type'),
    'escaped_tag': ('int f(void){struct S {int a;};return 0;}int main(void){return sizeof(struct S);}', 'sizeof requires a complete object type'),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    support.OUT = OUT
    # Inspect recorded offsets independently of generated member-access code
    inspector = OUT / 'inspect.c'
    inspector.write_text('#define main compiler_entry\n#include "' + (ROOT/'src/main.c').as_posix() + '''"
#undef main
int main(int argc,char **argv){
    Parser *p=allocate(sizeof *p);unsigned i;Member *m;
    if(argc!=2)return 1;
    p->path=intern_path(p,argv[1]);p->line=p->column=1;
    p->function_tail=&p->functions;p->string_tail=&p->strings;
    p->source=preprocess(argv[1],"include");lex(p);translation_unit(p);
    for(i=0;i<p->tag_count;++i){
        printf("%s %u",p->tags[i].name,p->tags[i].size);
        for(m=p->tags[i].members;m;m=m->next)printf(" %s:%u",m->name,m->offset);
        puts("");
    }
    return 0;
}
''')
    exe = OUT/'inspect.exe'
    support.run([ROOT/'tools/msvc.cmd', '/nologo', '/std:c17', '/W4', '/WX', '/O2',
                 '/D_CRT_SECURE_NO_WARNINGS', '/Fo'+str(OUT)+'/', '/Fe'+str(exe),
                 inspector, ROOT/'src/preprocess.c', ROOT/'src/relax.c'])
    definitions = OUT/'definitions.c'
    definitions.write_text(LAYOUT)
    actual = support.run([exe, definitions]).stdout.splitlines()
    expected = ['Forward 4 mark:0 next:2', 'Bytes 4 a:0 b:1 c:2',
                'Mixed 8 lead:0 wide:2 tail:6', 'Item 8 id:0 quantity:2 unit_price:4',
                'Nested 32 first:0 bytes:2 items:6 last:30',
                'Six 6 first:0 value:2', 'Types 14 a:0 pointer:2 real:4 words:8']
    assert actual == expected, actual
    _, rom, labels = support.compile_case('runtime', RUNTIME, extra_objects=[
        ROOT/'build/arithmetic.o', ROOT/'build/integers.o', ROOT/'build/ieee_engine.o'])
    assert labels['global'] % 2 == labels['globals'] % 2 == labels['dp_array'] % 2 == 0
    log = support.emulate(rom, labels, 0)
    for name, (source, message) in INVALID.items():
        cfile = OUT/(name+'.c')
        cfile.write_text(source)
        result = subprocess.run([str(ROOT/'build/zicc.exe'), str(cfile), '-o', str(OUT/(name+'.s'))], capture_output=True, text=True)
        assert result.returncode != 0 and message in result.stderr, (name, result.stderr)
        assert re.search(r':\d+:\d+: error:', result.stderr), result.stderr
    (OUT/'results.json').write_text(json.dumps(dict(layout=actual, runtime=log, rejected=list(INVALID), compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest(), rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest()), indent=2)+'\n')
    print(f'PASS: seven recorded layouts; sizeof/alignment/stride/recursive storage on Mesen; {len(INVALID)} diagnostics')


if __name__ == '__main__':
    main()
    spec = importlib.util.spec_from_file_location('unions', ROOT/'tests/check-unions.py')
    unions = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unions)
    unions.main()
