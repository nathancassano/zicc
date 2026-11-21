"""Union layouts, overlapping access, ROM images and aggregate tag identity."""
import os
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'union-check'
spec = importlib.util.spec_from_file_location('union_support', ROOT/'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

LAYOUT = '''union Forward;
union Forward;
typedef union Forward Forward;
union Payload {
    char bytes[5];
    short word;
    unsigned long wide;
    struct {char flag;short value;} pair;
};
struct Packet {char kind;union Payload data;char end;};
union Forward {char mark;union Forward *next;};
union Small {char c;};
union Matrix {short cells[2][3];char bytes[7];};
typedef struct {short x;union {long wide;char bytes[4];} variant;} Untagged;
'''

RUNTIME = LAYOUT + '''
union Payload objects[3];
__dpage union Payload dp;
const union Payload image={{1,2,3},};
const union {struct {char lead;short count;} first;char bytes[7];} nested={{9,0x1234}};
const union {unsigned long wide;char bytes[4];} bits={0x12345678UL};
const union Small smalls[2]={{7},{8}};
const union {float real;unsigned long bits;} real={1.5f};
const struct {char a;union Payload p;char z;} packet={3,{{4,5}},6};
union Float {unsigned long bits;float real;};
int calls;
union Payload *next(void){++calls;return &objects[1];}
short *word(union Payload *p){return &p->word;}
int main(void){
    union Payload local;
    union Payload *p=&local;
    Forward f;
    Forward *pf=&f;
    Untagged u;
    union Matrix matrix;
    union Float floating;
    unsigned char * __far raw;
    int i,j;
    if(sizeof(union Payload)!=6||sizeof(struct Packet)!=10||sizeof(union Small)!=2)return 1;
    if(sizeof(matrix)!=12||sizeof(objects)!=18||sizeof(Untagged)!=6||sizeof(Forward)!=2)return 2;
    if((unsigned int)&p->word!=(unsigned int)p||
       (unsigned int)&p->pair!=(unsigned int)p||
       (unsigned int)&p->pair.value-(unsigned int)p!=2)return 3;
    if((unsigned int)(objects+2)-(unsigned int)objects!=12)return 4;
    if(((unsigned int)&local&1)||((unsigned int)objects&1)||((unsigned int)&dp&1))return 5;
    p->wide=0x12345678UL;
    if(p->word!=0x5678||p->bytes[0]!=0x78||p->bytes[3]!=0x12)return 6;
    p->pair.value=0x3210;
    if(p->wide!=0x32105678UL)return 7;
    p->word=0x1111;(*word(p))++;
    if(p->word!=0x1112)return 8;
    next()->word=17;next()->word+=3;
    if(calls!=2||objects[1].word!=20)return 9;
    dp.wide=0xabcdef01UL;
    if(dp.bytes[0]!=1||dp.bytes[3]!=0xab)return 10;
    u.x=5;u.variant.wide=23;
    if(u.x!=5||u.variant.bytes[0]!=23)return 11;
    for(i=0;i<2;++i)for(j=0;j<3;++j)matrix.cells[i][j]=i*10+j;
    if(matrix.cells[1][2]!=12||matrix.bytes[6]!=10)return 12;
    floating.bits=0x3fc00000UL;
    if(floating.real!=1.5f)return 13;
    if(image.bytes[0]!=1||image.bytes[2]!=3||image.bytes[4]!=0)return 14;
    if(nested.first.lead!=9||nested.first.count!=0x1234||nested.bytes[6]!=0)return 15;
    if(bits.bytes[0]!=0x78||bits.bytes[3]!=0x12||smalls[1].c!=8||real.bits!=0x3fc00000UL)return 16;
    if(packet.a!=3||packet.p.bytes[1]!=5||packet.z!=6)return 17;
    raw=(unsigned char * __far)&nested;
    if(raw[1]!=0||raw[4]!=0||raw[7]!=0)return 18;
    pf->mark=9;if(pf->mark!=9)return 19;
    {union Payload {long a[3];};if(sizeof(union Payload)!=12)return 20;}
    if(sizeof(union Payload)!=6)return 21;
    {struct Payload {char c;};if(sizeof(struct Payload)!=2)return 22;}
    {union Payload;union Payload *opaque;if(sizeof(opaque)!=2)return 23;}
    {enum Payload {value=7};if(value!=7)return 24;}
    if(sizeof(union Payload)!=6)return 25;
    {union Shared {short x;} a,b;union Shared *pa=&a;union Shared *pb=&b;pa=pb;pa->x=6;if(b.x!=6)return 26;}
    {typedef union {short x;} Alias;Alias a;Alias *pa=&a;pa->x=7;if(a.x!=7)return 27;}
    {struct {short x;} a,b;a.x=3;b.x=a.x;if(b.x!=3)return 28;}
    {struct Other;{union Other;union Other {short x;};union Other a;a.x=8;if(a.x!=8)return 29;}}
    {union Payload *vp;void *generic=&local;vp=generic;generic=vp;vp=generic;if(vp!=&local)return 30;}
    return 0;
}
'''

INVALID = {
    'empty': ('union U {};', 'empty unions'),
    'duplicate': ('union U {int a;char a;};', 'duplicate member'),
    'recursive': ('union U {union U self;};', 'complete object type'),
    'incomplete': ('union U {struct S value;};', 'complete object type'),
    'large': ('union U {long a[32641];};', 'union layout exceeds 130560'),
    'redefined': ('union U {int a;};union U {int a;};', 'redefinition of union'),
    'kind_struct': ('struct U;union U;', 'declared as struct'),
    'kind_union': ('union U;struct U;', 'declared as union'),
    'kind_enum': ('enum U {a};union U;', 'declared as enum'),
    'kind_to_enum': ('union U;enum U {a};', 'conflicting enum tag'),
    'outer_wrong_kind': ('struct U;int main(void){union U *p;return 0;}', 'declared as struct'),
    'incomplete_shadow': ('union U {int x;};int main(void){union U;return sizeof(union U);}', 'complete object type'),
    'escaped': ('int f(void){union U {int x;};return 0;}int main(void){return sizeof(union U);}', 'complete object type'),
    'anonymous_identity': ('typedef union {int x;} A;typedef union {int x;} B;int main(void){A *a;B *b;a=b;return 0;}', 'incompatible'),
    'struct_identity': ('typedef struct {int x;} A;typedef struct {int x;} B;int main(void){A *a;B *b;a=b;return 0;}', 'incompatible'),
    'tag_identity': ('union A {int x;};union B {int x;};int main(void){union A *a;union B *b;a=b;return 0;}', 'incompatible'),
    'argument_identity': ('union A {int x;};union B {int x;};int f(union A *a);int main(void){union B b;return f(&b);}', 'incompatible argument'),
    'missing_member': ('union U {int x;};int main(void){union U u;return u.y;}', "union 'U' has no member"),
    'promotion': ('struct S {union {int x;};};', 'expected declaration name'),
    'nameless': ('union {int x;} ;int main(void){return sizeof(union);}', 'expected union tag or definition'),
    'const_scalar': ('const union U {int x;};const union U u;int main(void){u.x=1;return 0;}', 'const'),
    'const_array': ('union U {int a[2];};const union U u;int main(void){u.a[0]=1;return 0;}', 'const'),
    'const_nested': ('union U {struct {int x;} s;};const union U u;int main(void){u.s.x=1;return 0;}', 'const'),
    'excess_init': ('const union U {int x;long y;} u={1,2};', 'excess union initializer'),
    'excess_nested': ('const union {struct {int x;} s;long y;} u={{1,2}};', 'excess struct initializer'),
    'designator': ('const union U {int x;} u={.x=1};', 'designated initializers'),
    'local_init': ('int main(void){union U {int x;} u={1,2};return 0;}', 'excess union initializer'),
    'compound_copy': ('union U {int x;};int main(void){union U a,b;a+=b;return 0;}', 'struct values'),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    support.OUT = OUT
    # Record parser offsets independently of member codegen and ROM initialization
    inspector = OUT/'inspect.c'
    inspector.write_text('#define main compiler_entry\n#include "' + (ROOT/'src/main.c').as_posix() + '''"
#undef main
int main(int argc,char **argv){
 Parser *p=allocate(sizeof *p);unsigned i;Member *m;
 if(argc!=2)return 1;
 p->path=intern_path(p,argv[1]);p->line=p->column=1;
 p->function_tail=&p->functions;p->string_tail=&p->strings;
 p->source=preprocess(argv[1],"include");lex(p);translation_unit(p);
 for(i=0;i<p->tag_count;++i){
  printf("%s:%s:%u",p->tags[i].is_union?"union":"struct",p->tags[i].name,p->tags[i].size);
  for(m=p->tags[i].members;m;m=m->next)printf(" %s:%u",m->name,m->offset);
  puts("");
 }
 return 0;
}
''')
    exe = OUT/'inspect.exe'
    support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/W4','/WX','/O2',
                 '/D_CRT_SECURE_NO_WARNINGS','/Fo'+str(OUT)+'/', '/Fe'+str(exe),
                 inspector,ROOT/'src/preprocess.c',ROOT/'src/relax.c'])
    definitions = OUT/'definitions.c'
    definitions.write_text(LAYOUT)
    layout = support.run([exe,definitions]).stdout.splitlines()
    assert layout == [
        'union:Forward:2 mark:0 next:0',
        'union:Payload:6 bytes:0 word:0 wide:0 pair:0',
        'struct::4 flag:0 value:2',
        'struct:Packet:10 kind:0 data:2 end:8',
        'union:Small:2 c:0',
        'union:Matrix:12 cells:0 bytes:0',
        'struct::6 x:0 variant:2',
        'union::4 wide:0 bytes:0',
    ], layout
    _, rom, labels = support.compile_case('runtime',RUNTIME,extra_objects=[
        ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
    log = support.emulate(rom,labels,0)
    images = {'image':bytes([1,2,3,0,0,0]), 'nested':bytes([9,0,0x34,0x12,0,0,0,0]),
              'bits':bytes.fromhex('78563412'), 'smalls':bytes([7,0,8,0]),
              'real':bytes.fromhex('0000c03f'), 'packet':bytes([3,0,4,5,0,0,0,0,6,0])}
    data = rom.read_bytes()
    for name, image in images.items():
        pos = labels[name] & 0x7fff
        assert labels[name] >= 0x808000 and labels[name] % 2 == 0
        assert data[pos:pos+len(image)] == image, (name,data[pos:pos+len(image)].hex())
    for name, (source,message) in INVALID.items():
        path = OUT/(name+'.c');path.write_text(source)
        result = subprocess.run([str(ROOT/'build/zicc.exe'),str(path),'-o',str(OUT/(name+'.s'))],capture_output=True,text=True)
        assert result.returncode and message in result.stderr, (name,result.stderr)
        assert re.search(r':\d+:\d+: error:',result.stderr),result.stderr
    (OUT/'results.json').write_text(json.dumps(dict(layout=layout,runtime=log,images={k:v.hex() for k,v in images.items()},
        rejected=list(INVALID),compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest(),
        rom_sha256=hashlib.sha256(data).hexdigest()),indent=2)+'\n')
    print(f'PASS: eight union/untagged layouts; overlapping typed access, six exact ROM images, tag scope; {len(INVALID)} diagnostics')


if __name__ == '__main__':
    main()
