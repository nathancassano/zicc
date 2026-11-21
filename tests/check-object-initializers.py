"""Execute Dragon's S1/S2 prerequisites without depending on Dragon sources."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'object-initializers-check'
spec = importlib.util.spec_from_file_location('support', ROOT/'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

SOURCE = r'''
unsigned extern merged[];
unsigned merged[3];
extern unsigned merged[];
unsigned rows[][2]={{11,12},{21,22}};
extern unsigned rows[][2];
unsigned *cursor=&merged[1];
unsigned *null_pointer=0;
unsigned *computed_null=(2>1?0:1);
unsigned *conditional_address=1 ? &merged[2] : &merged[0];
char * __far port=(char * __far)0x002100UL;
char * __far computed_port=(char * __far)(1 ? 0x002100UL : 0UL)+2;
unsigned * __far far_ram=&merged[2];
unsigned ((*row_pointer))[2]=&rows[1];
unsigned (* (row_pointers[2]))[2]={&rows[0],&rows[1]};
const char text[]="ab" "cd";
const char * __far message=1+text;
const char * __far literal="xy"+1;
char exact[2]="hi";
char padded[5]={"hi"};
char embedded[]="a\0b";
struct Entry {char tag;unsigned *ram;const char * __far rom;unsigned tail;};
const struct Entry table[2]={{3,&merged[0],text,9},{4,&rows[0][1],"uv",10}};
const struct Entry flat_table[]={5,&merged[1],text,11,6,&rows[0][1],"wx"};
const unsigned flat_rows[][2]={1,2,{3},4,};
struct Cell {char name[3];unsigned words[2];};
struct Block {struct Cell cells[2];unsigned last;};
const struct Block flat_block={"ab",21,22,"c",23,24,25};
struct Record {char tag;unsigned words[3];char name[4];unsigned last;};
__loram const unsigned low=0x2345;
const unsigned *low_pointer=&low;
volatile __dpage unsigned dp;
volatile unsigned * __far dp_pointer=&dp;
unsigned calls;
volatile unsigned input=7;
__noinline unsigned next(void){calls++;return input+calls;}
__noinline unsigned pair(unsigned a,unsigned b){return a*10+b;}
__noinline unsigned lifetime(unsigned n){
    static unsigned value=4;
    const unsigned static masks[3]={1,4,16};
    static unsigned zero;
    unsigned value_before=value;
    value+=n;zero++;
    if(masks[zero-1]!=(zero==1?1:4))return 999;
    return value_before;
}
__forceinline unsigned shared(void){static unsigned count;return ++count;}
__forceinline unsigned *same(void){static unsigned n=17;static unsigned *ref=&n;return ref;}
__noinline unsigned shadow(void){
    static unsigned x=1;unsigned a=++x;
    {static unsigned x=20;a+=++x;}
    return a;
}
__noinline unsigned recursive(unsigned n){
    static unsigned visits;
    visits++;
    if(n)return recursive(n-1);
    return visits;
}
static unsigned linked_local=12;
__noinline unsigned block_linkage(void){
    unsigned merged=8;
    {extern unsigned merged[];extern unsigned linked_local;extern unsigned later;
     extern unsigned later;merged[0]=13;linked_local+=later;}
    return merged;
}
unsigned later=4;
__noinline unsigned call_block_function(unsigned value){
    unsigned add_later(unsigned);
    extern unsigned add_later(unsigned);
    return add_later(value);
}
unsigned add_later(unsigned value){return value+later;}
__noinline int implicit_after_block(int value){
    {int block_target(int);}
    return block_target(value);
}
int block_target(int value){return value+1;}
__noinline unsigned jumps(unsigned n,unsigned value,unsigned step){
    unsigned again=0,sum=again;
    goto start;
    return 99;
again:
    sum+=step;
start:
    if(n--)goto again;
    goto inside;
    while(0){
inside:
        sum+=value;
    }
    if(0){
finish:
        return sum;
    }
    goto finish;
}
__noinline unsigned local(unsigned n){
    unsigned auto a[]={next(),n,9};
    unsigned b[4]={n};
    unsigned grid[2][2]={{n},{next(),3}};
    struct Record r={2,{n,6},"hey"};
    struct Record copy=r;
    union Choice {unsigned word;char bytes[2];};
    union Choice choice={0x1234};
    const char * __far names[]={"first",text};
    char countdown[]="Auto-load in 5 secs";
    char small[2]="ok";
    const unsigned immutable[2]={n,4};
    if(sizeof(a)!=3*sizeof(unsigned)||a[0]!=8||a[1]!=n||a[2]!=9)return 1;
    if(b[0]!=n||b[1]||b[2]||b[3]||grid[0][0]!=n||grid[0][1]||grid[1][0]!=9)return 2;
    if(r.tag!=2||r.words[0]!=n||r.words[1]!=6||r.words[2]||r.name[3]||r.last)return 3;
    if(copy.words[0]!=n||copy.name[1]!='e'||choice.bytes[0]!=0x34||choice.bytes[1]!=0x12)return 4;
    if(names[0][2]!='r'||names[1][3]!='d'||countdown[13]!='5'||small[1]!='k'||immutable[0]!=n)return 5;
    countdown[0]='X';return countdown[0]!='X';
}
__noinline unsigned elided_local(unsigned n){
    static const unsigned grid[][2]={31,32,33,};
    unsigned rows[][2]={next(),n,{next()},n+1,};
    struct Cell cell={"de",n,41};
    struct Block flat={"f",n,42,"gh",43,44,45};
    struct Block copied={cell,"i",46,47,48};
    union First {struct Cell cell;unsigned other;};
    struct Choice {union First first;unsigned last;};
    struct Choice choice={"jk",49,50,51};
    if(sizeof(grid)!=4*sizeof(unsigned)||grid[1][0]!=33||grid[1][1])return 1;
    if(sizeof(rows)!=6*sizeof(unsigned)||rows[0][0]!=8||rows[0][1]!=n||
       rows[1][0]!=9||rows[1][1]||rows[2][0]!=n+1||rows[2][1])return 2;
    if(flat.cells[0].name[1]||flat.cells[0].words[0]!=n||
       flat.cells[1].name[1]!='h'||flat.cells[1].words[1]!=44||flat.last!=45)return 3;
    if(copied.cells[0].name[1]!='e'||copied.cells[0].words[1]!=41||
       copied.cells[1].name[0]!='i'||copied.cells[1].words[1]!=47||copied.last!=48)return 4;
    if(choice.first.cell.name[1]!='k'||choice.first.cell.words[1]!=50||choice.last!=51)return 5;
    return 0;
}
struct RomSlice { unsigned index; char text[4]; };
const struct RomSlice rom_slice={1,"x"}, rom_other={0,"y"};
const struct RomSlice * __far const rom_pointer=&rom_slice;
const struct RomSlice * __far rom_mutable=&rom_slice;
volatile unsigned rom_visits;
__noinline unsigned rom_fixed(void){
    if(rom_pointer->text[rom_pointer->index])++rom_visits;
    return rom_pointer->index;
}
__noinline unsigned rom_indirect(void){return rom_mutable->text[rom_mutable->index];}
struct FixedPart { unsigned first, second; };
__noinline struct FixedPart init_fixed_slice(unsigned n){
    struct FixedPart values[24]={{0x4567,0x6789}};
    values[23].second=n;
    return values[23];
}
__noinline unsigned read_slice(struct FixedPart *values,unsigned n){return values[n].first;}
__noinline unsigned init_escaped_slice(unsigned n){
    struct FixedPart values[3]={{0x4567,2},{5,next()}};
    return read_slice(values,n)+values[1].second;
}
struct CommaValue { unsigned words[2]; };
static const struct CommaValue comma_rom={{9,10}};
static volatile struct CommaValue comma_volatile={{11,12}};
__noinline struct CommaValue comma_return(unsigned n){
    struct CommaValue value={{n,n+1}};
    return (++n,value);
}
__noinline unsigned comma_argument(struct CommaValue value){return value.words[1];}
static unsigned aggregate_comma(void){
    struct CommaValue a={{1,2}}, b={{3,4}}, c;
    unsigned n=0, v;
    c=(++n,b);
    v=(a=b,7);
    if(n!=1||v!=7||a.words[0]!=3||c.words[1]!=4)return 1;
    (void)(++n,(void)comma_volatile);
    (n++,comma_volatile);
    c=(n++,comma_rom);
    if(n!=4||c.words[0]!=9||c.words[1]!=10)return 2;
    if(comma_argument((++n,comma_return(5)))!=6||n!=5)return 3;
    if((++n,b).words[0]!=3||n!=6)return 4;
    if((++n,comma_rom).words[1]!=10||n!=7)return 5;
    return 0;
}
int (main)(void){
    unsigned a=0,b=0,i,sum=0;unsigned *p;
    if(sizeof(merged)!=3*sizeof(unsigned)||sizeof(rows)!=4*sizeof(unsigned)||cursor!=&merged[1]||row_pointer!=&rows[1])return 1;
    if(null_pointer||(unsigned long)port!=0x2100UL)return 20;
    if(computed_null||conditional_address!=&merged[2]||(unsigned long)computed_port!=0x2102UL)return 30;
    *cursor=17;*far_ram=19;(*row_pointer)[0]=31;
    if(merged[1]!=17||merged[2]!=19||rows[1][0]!=31)return 2;
    if((*row_pointers[0])[0]!=11||(*row_pointers[1])[0]!=31)return 26;
    if(message[0]!='b'||message[2]!='d'||literal[0]!='y'||literal[1])return 3;
    if(sizeof(text)!=5||sizeof(exact)!=2||padded[2]||padded[4]||sizeof(embedded)!=4||embedded[2]!='b')return 4;
    if(table[0].tag!=3||table[0].ram!=merged||table[0].rom[2]!='c'||table[1].ram!=&rows[0][1]||table[1].rom[1]!='v')return 5;
    if(*low_pointer!=0x2345)return 6;
    *dp_pointer=123;if(dp!=123)return 7;
    if(local(input)||calls!=2)return 8;
    calls=0;if(local(input)||calls!=2)return 9;
    if(lifetime(3)!=4||lifetime(2)!=7)return 10;
    if(shared()!=1||shared()!=2)return 11;
    p=same();if(p!=same()||*p!=17)return 21;
    if(shadow()!=23||shadow()!=25||recursive(3)!=4)return 12;
    for(i=0;i<4;i++,a+=2,b++){
        if(i==1)continue;
        sum+=i;
    }
    if(a!=8||b!=4||sum!=5)return 13;
    a=0;if((a=3,a+4)!=7||a!=3)return 14;
    if(pair((a=2,a+1),4)!=34||a!=2)return 15;
    p=(a=5,&merged[1]);if(p!=cursor||a!=5)return 16;
    if((a=0,a?11:(a=9,13))!=13||a!=9)return 17;
    if(0&&(a=44,a))return 18;
    if(a!=9||sizeof((a=33,a))!=sizeof(unsigned)||a!=9)return 19;
    if(sizeof(flat_rows)!=6*sizeof(unsigned)||flat_rows[0][1]!=2||
       flat_rows[1][0]!=3||flat_rows[1][1]||flat_rows[2][0]!=4||flat_rows[2][1])return 22;
    if(flat_table[0].ram!=&merged[1]||flat_table[0].tail!=11||
       flat_table[1].ram!=&rows[0][1]||flat_table[1].rom[1]!='x'||flat_table[1].tail)return 23;
    if(flat_block.cells[0].name[1]!='b'||flat_block.cells[0].words[1]!=22||
       flat_block.cells[1].name[1]||flat_block.cells[1].words[0]!=23||flat_block.last!=25)return 24;
    calls=0;if(elided_local(input)||calls!=2)return 25;
    if(block_linkage()!=8||merged[0]!=13||linked_local!=16)return 27;
    if(call_block_function(input)!=11)return 28;
    if(implicit_after_block(input)!=8)return 31;
    if(jumps(3,input,2)!=13)return 29;
    if(aggregate_comma())return 32;
    if(rom_fixed()!=1||rom_visits||rom_indirect())return 35;
    rom_mutable=&rom_other;if(rom_indirect()!='y')return 36;
    {struct FixedPart last=init_fixed_slice(input);if(last.first||last.second!=input)return 33;}
    calls=0;if(init_escaped_slice(input-7)!=0x4567+8||calls!=1)return 34;
    return 0;
}
'''

BAD = {
    'array_conflict': ('extern unsigned a[];unsigned a[2];extern unsigned a[3];','conflicting declaration'),
    'row_conflict': ('extern unsigned a[][2];unsigned a[3][4];','conflicting declaration'),
    'element_conflict': ('extern unsigned a[];long a[2];','conflicting declaration'),
    'incomplete_tentative': ('struct S a;','requires a complete object type'),
    'incomplete_initialized': ('extern struct S a={1};','requires a complete object type'),
    'incomplete_static': ('static int a[];','requires a complete object type'),
    'tentative_sizeof': ('int a[];int f(void){return sizeof a;}','sizeof requires a complete'),
    'typedef_incomplete_sizeof': ('typedef int Values[];int f(void){return sizeof(Values);}','sizeof requires a complete'),
    'tentative_oversized_row': ('char a[][32768][3];','object size exceeds'),
    'short_string': ('char a[1]="ab";','too long'),
    'excess_local': ('void f(void){unsigned a[1]={1,2};}','excess array'),
    'excess_struct': ('void f(void){struct S {int n;};struct S s={1,2};}','excess struct'),
    'excess_elided_array': ('int a[1][2]={1,2,3};','excess array'),
    'excess_braced_row': ('int a[2][2]={{1,2,3},4};','excess array'),
    'excess_elided_struct': ('void f(void){struct S {int a[2];int b;} s={1,2,3,4};}','excess struct'),
    'unbraced_outer_array': ('int a[2][2]=1;','expected'),
    'auto_static': ('void f(void){auto static int x;}','conflicting storage classes'),
    'auto_file_scope': ('auto int x;','expected a supported type declaration'),
    'extern_escape': ('int f(void){{extern int x;}return x;}','undeclared identifier'),
    'extern_initializer': ('void f(void){extern int x=1;}','cannot have an initializer'),
    'block_static_function': ('void f(void){static int g(void);}','invalid storage class'),
    'block_function_conflict': ('int g(int);void f(void){int g(long);}','conflicting parameter type'),
    'block_function_arguments': ('void f(void){int g(int);g();}','wrong argument count'),
    'extern_extent_escape': ('extern int a[];int f(void){{extern int a[3];}return sizeof(a);}','sizeof requires a complete'),
    'undefined_label': ('void f(void){goto gone;}','undefined label'),
    'duplicate_label': ('void f(void){same:;{same:;}}','duplicate label'),
    'static_dynamic': ('unsigned n;void f(void){static unsigned x=n;}','constant expression'),
    'static_auto_address': ('void f(void){unsigned n;static unsigned *p=&n;}','constant address'),
    'rom_narrow': ('const unsigned a[2]={1,2};const unsigned *p=a;','incompatible pointer'),
    'rom_cast_narrow': ('const unsigned a=1;const unsigned *p=(const unsigned *)&a;','not representable'),
    'nested_rom_cast_narrow': ('const int a[2]={1,2};const int *p=(const int *)(a+1);','not representable'),
    'pointer_offset_overflow': ('char *p=(char *)0xffff+1;','offset overflows'),
    'pointer_load': ('unsigned *a;unsigned *b=a;','constant address'),
    'const_discard': ('const unsigned a=1;unsigned * __far p=&a;','incompatible pointer'),
    'pointer_type': ('unsigned a;char *p=&a;','incompatible pointer'),
    'static_duplicate': ('void f(void){static unsigned n;static unsigned n;}','duplicate local'),
    'static_escape': ('void f(void){{static unsigned n;}n=1;}','undeclared identifier'),
    'const_local': ('void f(void){const unsigned a[2]={1,2};a[0]=3;}','writable'),
    'comma_lvalue': ('void f(void){unsigned a,b;(a,b)=2;}','writable'),
    'comma_constant': ('unsigned a=(1,2);','constant expression'),
    'static_oversized': ('void f(void){static char a[256][256];}','object size'),
    'aggregate_comma_lvalue': ('void f(void){struct S {int n;} a,b;(a,b).n=1;}','writable'),
    'floating_offset': ('unsigned a[2];unsigned *p=a+1.0;','invalid operands to pointer arithmetic'),
}


def main():
    OUT.mkdir(parents=True,exist_ok=True);support.OUT=OUT
    report={}
    objects=[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables')]
    for name,flags in [('optimized',()),('fallback',('--no-inline','--no-body-optimizations','--no-known-values','--no-strength-reduction'))]:
        _,rom,labels=support.compile_case(name,SOURCE,extra_objects=objects,flags=flags)
        report[name]=dict(execution=support.emulate(rom,labels,0),rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest())
        assembly=(OUT/(name+'.s')).read_text()
        fixed_slice=assembly.split('_init_fixed_slice:\n',1)[1].split('__size_init_fixed_slice',1)[0]
        assert ('#$4567' in fixed_slice)==bool(flags),fixed_slice
        rom_fixed=assembly.split('_rom_fixed:\n',1)[1].split('__size_rom_fixed',1)[0]
        assert ('_rom_pointer' in rom_fixed)==bool(flags),rom_fixed
        image=rom.read_bytes()
        def initial_bytes(symbol,size):
            address=labels['_DATA_LOAD__']+labels[symbol]-labels['_DATA_RUN__']
            return image[address&0x7fff:(address&0x7fff)+size]
        assert initial_bytes('cursor',2)==struct.pack('<H',(labels['merged']+2)&0xffff)
        assert initial_bytes('far_ram',4)==struct.pack('<I',labels['merged']+4)
        assert initial_bytes('message',4)==struct.pack('<I',labels['text']+1)
        assert initial_bytes('null_pointer',2)==bytes(2)
        assert initial_bytes('port',4)==bytes.fromhex('00210000')
    host_source=OUT/'reference.c'
    portable=SOURCE
    for word in ('__dpage','__loram','__far','__noinline','__forceinline'):
        portable=re.sub(r'\b'+word+r'\b','',portable)
    host_source.write_text(portable)
    host=OUT/'reference.exe'
    support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(OUT/'reference.obj'),'/Fe'+str(host),host_source])
    support.run([host]);report['host_reference']='PASS'
    _,rom,labels=support.compile_case('tentative', '''
        int single[], sized[];
        int row[][3];
        typedef int Values[];
        Values values={8,9};
        Values *values_ptr;
        extern int single[];
        int sized[2]={3,4};
        static int local[2];
        static int local[];
        struct Record record;
        struct Record { int value; };
        struct Record initialized;
        struct Record initialized={7};
        int main(void){
            if(single[0]||row[0][2]||record.value||local[1]||initialized.value!=7||sized[1]!=4)return 1;
            single[0]=5;
            record.value=6;
            values_ptr=&values;
            return single[0]+record.value!=11||(*values_ptr)[1]!=9||sizeof values!=4;
        }
    ''')
    report['tentative']=support.emulate(rom,labels,0)
    assert labels['_zicc_object_size_single']==2
    assert labels['_zicc_object_size_row']==6
    # Crossing the old 512 boundary exercises expansion suppression at high IDs
    macros=''.join(f'#define M{i} {i}\n' for i in range(1100))
    macros+='#define AGAIN AGAIN\n#define ADD(x) ((x)+M1099)\n#undef M800\n#define M800 17\n'
    macros+='int main(void){int AGAIN=3;return ADD(M800)!=1116||AGAIN!=3||M700!=700;}\n'
    _,rom,labels=support.compile_case('macros',macros)
    report['macros']=support.emulate(rom,labels,0)
    boundary=OUT/'macro-boundary.c'
    boundary.write_text(''.join(f'#define B{i} {i}\n' for i in range(4092))+'int main(void){return B4091!=4091;}\n')
    support.run([ROOT/'build/zicc.exe',boundary,'-o',boundary.with_suffix('.s')])
    overflow=boundary.read_text()+'#define TOO_MANY 1\n'
    BAD['macro_limit']=(overflow,'too many macros')
    for name,(text,message) in BAD.items():
        path=OUT/('bad_'+name+'.c');path.write_text(text)
        r=subprocess.run([str(ROOT/'build/zicc.exe'),str(path),'-o',str(path.with_suffix('.s'))],capture_output=True,text=True)
        assert r.returncode and message in r.stderr and re.search(r':\d+:\d+: error:',r.stderr),(name,r.stderr)
    # Separate object definitions, near/far relocations, and private-symbol LTO remapping
    defs=OUT/'definitions.c';driver=OUT/'driver.c'
    defs.write_text('unsigned data[3]={7,8,9};static const char text[]="xyz";'
                    'const char * __far message=text+1;unsigned *cursor=&data[2];'
                    'unsigned count(void){static unsigned n;return ++n;}')
    driver.write_text('extern unsigned data[];extern unsigned *cursor;extern const char * __far message;'
                      'unsigned count(void);int main(void){return *cursor!=9||message[0]!=\'y\'||count()!=1||count()!=2;}')
    for lto,stage in ((False,1),(True,1),(False,3),(True,3)):
        name=('linked-lto' if lto else 'linked')+str(stage)
        raw=OUT/(name+'.raw')
        support.run([sys.executable,ROOT/'tools/build-rom.py',driver,defs,'-o',raw,'--stage',str(stage),*(['--lto'] if lto else [])],timeout=120)
        labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        rom=raw.with_suffix('.sfc');support.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        report[name]=support.emulate(rom,labels,0)
    report['rejected']=list(BAD)
    report['compiler_sha256']=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest()
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS: object initialization/lifetime/comma semantics, 1100 macros, separate-TU/LTO relocations; {len(BAD)} diagnostics')


if __name__=='__main__':main()
