"""Read and write structure members and check that the compiler respects their qualifiers and evaluation order."""
import os
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'member-check'
spec = importlib.util.spec_from_file_location('support', Path(__file__).with_name('check-compiler.py'))
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

ITEM = '''struct Item {unsigned short id;short quantity;unsigned long unit_price;};'''
CASES = {
'returned_members': '''struct Pair {int a,b;};
#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
struct Pair *volatile published_pair;
struct Packed {signed char low,high;int number;};
volatile int number;
NEVER struct Packed literal_record(void){
    struct Packed result={-128,127,-1234};
    return result;
}
struct Triple {unsigned short first,second,third;};
NEVER struct Triple literal_slice(void){
    struct Triple values[12]={{5,6,7}};
    values[11].third=0xabcd;
    return values[11];
}
NEVER struct Packed dynamic_record(void){
    struct Packed result={-128,127,number};
    return result;
}
NEVER struct Pair rebuild_pair(struct Pair input){
    struct Pair out;
    out.a=input.a;
    out.b=input.b;
    return out;
}
NEVER struct Pair change_pair(struct Pair input){
    struct Pair out;
    out.a=input.a;
    out.b=input.b+3;
    return out;
}
NEVER int private_result(int a){
    struct Pair value={a,a+1};
    value=rebuild_pair(value);
    return value.a*2+value.b;
}
NEVER int addressable_result(int a){
    struct Pair value={a,a+1};
    published_pair=&value;
    value=change_pair(value);
    a=published_pair->b;
    published_pair=0;
    return a;
}
int main(void){
    struct Packed a=literal_record(),b;
    struct Triple slice=literal_slice();
    if(slice.first||slice.second||slice.third!=0xabcd)return 4;
    number=783;
    b=dynamic_record();
    if(a.low!=-128||a.high!=127||a.number!=-1234)return 2;
    if(b.low!=-128||b.high!=127||b.number!=783)return 3;
    return private_result(7)!=22||addressable_result(11)!=15;
}''',
'private_members': '''struct Pair {int used,spare;};
struct Box {struct Pair pair;};
int *volatile published;
int read_published(void){return *published;}
int only_members(int n){
    const struct Box x={{n++,0}};
    return x.pair.used<0?n:x.pair.used;
}
int publish_member(int n){
    struct Box x={{0,n}};
    int value;
    published=&x.pair.spare;
    value=read_published();
    published=0;
    return value;
}
int main(void){
    return only_members(-3)!=-2||only_members(9)!=9||publish_member(81)!=81;
}''',
'member_parameter': '''struct Pair {int position,status;};
#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
int failures;
NEVER void invalid_status(void){++failures;}
NEVER void normalize(struct Pair *p){
    if(p->status==1)p->status=0;
    if(p->position==1)p->position=0;
    switch(p->status){case 0:break;default:invalid_status();}
}
int main(void){
    struct Pair ok={1,1},bad={5,7};
    normalize(&ok);
    normalize(&bad);
    return ok.position||ok.status||bad.position!=5||bad.status!=7||failures!=1;
}''',
'known_backing': '''struct View {unsigned char tag;unsigned char data[1];};
unsigned char packet[8]={1,2,3,4,5,6,7,8};
#ifdef __ZICC__
#define NEVER __noinline
#else
#define NEVER
#endif
int payload(const struct View *p){return p->data[4];}
NEVER int matches_packet(void){if(payload((const struct View *)packet)!=250)return 0;return 1;}
NEVER void set_payload(unsigned char value){((struct View *)packet)->data[4]=value;}
int main(void){if(matches_packet())return 1;
    set_payload(250);
    if(!matches_packet()||packet[4]!=5||packet[5]!=250||packet[6]!=7)return 2;
    return 0;
}''',
'scalars': '''struct Scalars {unsigned char head;signed char byte;unsigned short word;short signed_word;unsigned long wide;long signed_wide;float real;unsigned char tail;};
struct Scalars global;
int main(void){
    struct Scalars local;struct Scalars *p=&local;
    p->head=77;p->tail=99;p->byte=-128;p->word=65535U;p->signed_word=-32767;
    p->wide=0x89abcdefUL;p->signed_wide=-1234567L;p->real=1.5f;
    if(local.head!=77||local.tail!=99||local.byte!=-128||local.word!=65535U||local.signed_word!=-32767)return 1;
    if(local.wide!=0x89abcdefUL||local.signed_wide!=-1234567L||local.real!=1.5f)return 2;
    if(local.byte++!=-128||local.byte!=-127||++p->byte!=-126)return 3;
    if((local.word+=2)!=1||local.word!=1)return 4;
    if(local.wide++!=0x89abcdefUL||++local.wide!=0x89abcdf1UL)return 5;
    if((p->signed_wide-=33)!=-1234600L)return 6;
    p->real+=2.0f;if(p->real!=3.5f)return 7;
    global.head=11;global.tail=22;global.byte=-1;global.wide=local.wide;global.real=p->real;
    if(global.head!=11||global.tail!=22||global.byte!=-1||global.wide!=0x89abcdf1UL||global.real!=3.5f)return 8;
    if(local.head!=77||local.tail!=99||sizeof(local.byte)!=1||sizeof(p->wide)!=4)return 9;
    p->word=511;p->word*=3;p->word/=7;p->word%=100;p->word<<=3;p->word>>=2;
    p->word|=256;p->word&=511;p->word^=32;if(p->word!=262)return 11;
    p->byte/=-2;if(p->byte!=63||p->head!=77)return 12;
    *(&p->signed_word)=-42;if(local.signed_word!=-42)return 10;
    return 0;
}''',
'nested': ITEM + '''
struct Box {char lead;struct Item rows[3];short bins[4];struct Item *current;struct Box *next;char tail;};
struct Box global[2];
short sum(const short *values,int count){short total=0;int i;for(i=0;i<count;++i)total+=values[i];return total;}
int main(void){
    struct Box local[2];struct Box *p=local;int i,j;
    for(i=0;i<2;++i){local[i].lead=11;local[i].tail=22;
        for(j=0;j<3;++j){local[i].rows[j].id=(unsigned short)(i*10+j);local[i].rows[j].quantity=(short)(i-j);local[i].rows[j].unit_price=100UL+(unsigned long)j;}
        for(j=0;j<4;++j)local[i].bins[j]=(short)(i+j);
    }
    p->next=&p[1];p->next->current=&p->rows[2];
    if(p->next->current->quantity!=-2||p->next->current->unit_price!=102UL)return 1;
    if(sum(p->bins,4)!=6||sum(p[1].bins,4)!=10)return 2;
    p->next->current->quantity+=7;if(local[0].rows[2].quantity!=5)return 3;
    if(sizeof(p->rows)!=3*sizeof(struct Item)||sizeof(p->bins)!=4*sizeof(short))return 4;
    if((unsigned char *)&p->rows[1]-(unsigned char *)&p->rows[0]!=sizeof(struct Item))return 5;
    global[1].rows[2].quantity=p->next->current->quantity;
    if(global[1].rows[2].quantity!=5||local[0].lead!=11||local[1].tail!=22)return 6;
    return 0;
}''',
'evaluation': '''struct Box {short value;unsigned long wide;unsigned char byte;struct Box *next;short values[2];};
struct Box objects[3];struct Box *base;int calls,index_calls;
struct Box *next_item(void){++calls;return base;}
int next_index(void){++index_calls;return 1;}
short rhs(void){return (short)(123456UL/37UL);}
short change_base(void){base=&objects[2];return 9;}
unsigned long wide_rhs(void){return 0xfedcba98UL;}
int main(void){
    struct Box *p;short old;
    base=objects;objects[0].value=5;objects[0].wide=0x1234ffffUL;objects[0].byte=254;
    calls=0;next_item()->value+=rhs();if(calls!=1||objects[0].value!=3341)return 1;
    calls=0;old=next_item()->value++;if(calls!=1||old!=3341||objects[0].value!=3342)return 2;
    calls=0;if(++next_item()->value!=3343||calls!=1)return 3;
    calls=0;if(next_item()->wide++!=0x1234ffffUL||calls!=1||objects[0].wide!=0x12350000UL)return 4;
    calls=0;if(++next_item()->byte!=255||calls!=1)return 5;
    calls=0;next_item()->wide+=0xffff0001UL;if(calls!=1||objects[0].wide!=0x12340001UL)return 6;
    calls=0;sizeof(next_item()->wide);if(calls)return 7;
    calls=0;if((next_item()->wide=wide_rhs())!=0xfedcba98UL||calls!=1||objects[0].wide!=0xfedcba98UL)return 12;
    calls=0;if(next_item()->byte++!=255||calls!=1||objects[0].byte!=0)return 13;
    calls=0;if((next_item()->wide+=wide_rhs())!=0xfdb97530UL||calls!=1||objects[0].wide!=0xfdb97530UL)return 14;
    objects[0].values[1]=17;calls=0;index_calls=0;
    next_item()->values[next_index()]+=rhs();
    if(calls!=1||index_calls!=1||objects[0].values[1]!=3353)return 15;
    calls=0;index_calls=0;sizeof(next_item()->values[next_index()]);if(calls||index_calls)return 16;
    index_calls=0;objects[next_index()].value=rhs();if(index_calls!=1||objects[1].value!=3336)return 8;
    p=objects;if((p++)->byte!=0||p!=objects+1)return 9;
    (*p).value=17;if(objects[1].value!=17)return 10;
    base=objects;objects[0].value=1;objects[2].value=2;calls=0;next_item()->value=change_base();
#ifdef __ZICC__
    if(objects[0].value!=9||objects[2].value!=2||calls!=1)return 11;
#else
    if(calls!=1||!((objects[0].value==9&&objects[2].value==2)||(objects[0].value==1&&objects[2].value==9)))return 11;
#endif
    return 0;
}''',
'qualifiers': '''struct Inner {short n;};
struct Holder {short value;struct Inner inner;short values[2];short *pointer;short *pointers[2];};
struct Holder global;
short total(const short *p){return (short)(p[0]+p[1]);}
int main(void){
    short target=1;struct Holder *mutable=&global;const struct Holder *view=&global;
    short *p;int i=0;
    mutable->value=3;mutable->inner.n=4;mutable->values[0]=5;mutable->values[1]=6;
    mutable->pointer=&target;mutable->pointers[0]=&target;
    if(view->value!=3||view->inner.n!=4||total(view->values)!=11)return 1;
    p=view->pointer;*p=7;if(target!=7)return 2;
    *view->pointer=8;if(target!=8)return 3;
    view->pointers[i][0]=9;if(target!=9)return 4;
    (*(&view->pointer))[0]=10;if(target!=10)return 5;
    if(sizeof(view->inner)!=sizeof(struct Inner)||sizeof(view->values)!=2*sizeof(short))return 6;
    return 0;
}''',
'recursion': ITEM + '''
short recurse(short depth,unsigned long seed){
    struct Item a,b;short next=0;
    a.id=(unsigned short)depth;a.quantity=(short)(depth+1);a.unit_price=seed;
    b.id=99;b.quantity=-23;b.unit_price=0xdeadbeefUL;
    if(depth)next=recurse((short)(depth-1),seed+17UL);
    if(next||a.id!=(unsigned short)depth||a.quantity!=(short)(depth+1)||a.unit_price!=seed)return 1;
    if(b.id!=99||b.quantity!=-23||b.unit_price!=0xdeadbeefUL)return 2;
    return 0;
}
int main(void){return recurse(8,0x1234ffffUL);}''',
'addressing': ITEM + '''
struct Item global;
struct Item *destination;
short quantity(struct Item *p){return p->quantity;}
unsigned long price(struct Item *p){return p->unit_price;}
void copy_price(struct Item *p){destination->unit_price=p->unit_price;}
void reset_price(struct Item *p){p->unit_price=0x43210000UL;}
int matches_price(struct Item *p){return p->unit_price==0x43210000UL;}
void set_quantity(struct Item *p){p->quantity=17;}
void set_global(void){global.quantity=-7;}
short *quantity_address(struct Item *p){return &p->quantity;}
int main(void){
    struct Item local;struct Item *p=&local;unsigned char *bytes=(unsigned char *)p;
    p->id=123;p->quantity=-12;p->unit_price=0x87654321UL;
    if(quantity(p)!=-12||price(p)!=0x87654321UL)return 1;
    if((unsigned char *)quantity_address(p)-bytes!=2)return 2;
    if((unsigned char *)&p->unit_price-bytes!=4)return 3;
    set_quantity(p);if(p->quantity!=17||p->id!=123||p->unit_price!=0x87654321UL)return 4;
    set_global();if(global.quantity!=-7)return 5;
    destination=&global;copy_price(p);if(global.unit_price!=0x87654321UL)return 6;
    destination=p;copy_price(p);if(p->unit_price!=0x87654321UL)return 7;
    reset_price(p);if(!matches_price(p))return 8;
    p->unit_price=0x43210001UL;if(matches_price(p))return 9;
    p->unit_price=0x43220000UL;if(matches_price(p))return 10;
    return 0;
}''',
'dpage': ITEM + '''
#ifdef __ZICC__
__dpage struct Item items[2];
#else
struct Item items[2];
#endif
int main(void){struct Item *p=items;int i=1;items[0].id=77;items[1].quantity=-4;
    p[i].unit_price=0x12345678UL;if(items[0].id!=77||items[1].quantity!=-4||p[1].unit_price!=0x12345678UL)return 1;
    return 0;
}''',
}

# Keep the original functions and checks; only replace the unsupported ROM
# initializer with explicit stores into a zero-filled table in this fixture
original = (ROOT/'samples/structures_and_tables.c').read_text()
original = re.sub(r'const struct Item catalog\[3\] = \{.*?\n\};', 'struct Item catalog[3];', original, flags=re.S)
initializers = ''.join(f'catalog[{i}].id={ident};catalog[{i}].quantity={q};catalog[{i}].unit_price={price}UL;'
                       for i,(ident,q,price) in enumerate(((10,2,125),(20,3,200),(30,1,999))))
CASES['inventory'] = original.replace('    struct Item item;', '    struct Item item;\n    '+initializers)

INVALID = {
'dot_scalar': ('int main(void){int x;return x.field;}', "'.' requires a struct object"),
'dot_pointer': (ITEM+'int main(void){struct Item *p;return p.quantity;}', "'.' requires a struct object"),
'dot_array': (ITEM+'struct Item a[2];int main(void){return a.quantity;}', "'.' requires a struct object"),
'arrow_scalar': ('int main(void){int x;return x->field;}', "'->' requires a pointer to a struct"),
'arrow_struct': (ITEM+'int main(void){struct Item x;return x->quantity;}', "'->' requires a pointer to a struct"),
'arrow_double': (ITEM+'int main(void){struct Item **p;return p->quantity;}', "'->' requires a pointer to a struct"),
'arrow_void': ('int main(void){void *p;return p->field;}', "'->' requires a pointer to a struct"),
'incomplete_arrow': ('struct S *p;int main(void){return p->x;}', 'member access requires a complete struct type'),
'incomplete_dot': ('struct S *p;int main(void){return (*p).x;}', 'member access requires a complete struct type'),
'unknown': (ITEM+'int main(void){struct Item x;return x.missing;}', "has no member 'missing'"),
'unknown_arrow': (ITEM+'int main(void){struct Item *p;return p->missing;}', "has no member 'missing'"),
'missing_name': (ITEM+'int main(void){struct Item x;return x.;}', 'expected member name'),
'keyword_name': (ITEM+'int main(void){struct Item x;return x.int;}', 'expected member name'),
'scalar_chain': (ITEM+'int main(void){struct Item x;return x.quantity.member;}', "'.' requires a struct object"),
'const_dot': (ITEM+'const struct Item x;int main(void){x.quantity=1;return 0;}', 'assignment requires a writable scalar'),
'const_arrow': (ITEM+'int main(void){const struct Item *p;p->quantity=1;return 0;}', 'assignment requires a writable scalar'),
'const_pre': (ITEM+'int main(void){const struct Item *p;++p->quantity;return 0;}', 'increment requires a writable scalar'),
'const_post': (ITEM+'int main(void){const struct Item *p;p->quantity++;return 0;}', 'increment requires a writable scalar'),
'const_compound': (ITEM+'int main(void){const struct Item *p;p->quantity+=1;return 0;}', 'assignment requires a writable scalar'),
'const_nested': (ITEM+'struct Box {struct Item item;};int main(void){const struct Box *p;p->item.quantity=1;return 0;}', 'assignment requires a writable scalar'),
'const_array': ('struct S {short a[2];};int main(void){const struct S *p;p->a[1]=2;return 0;}', 'assignment requires a writable scalar'),
'const_pointer': ('struct S {short *p;};int main(void){const struct S *s;s->p=0;return 0;}', 'assignment requires a writable scalar'),
'const_pointer_step': ('struct S {short *p;};int main(void){const struct S *s;s->p++;return 0;}', 'increment requires a writable scalar'),
'const_pointer_array': ('struct S {short *p[2];};int main(void){const struct S *s;s->p[0]=0;return 0;}', 'assignment requires a writable scalar'),
'const_pointer_address': ('struct S {short *p;};int main(void){const struct S *s;*(&s->p)=0;return 0;}', 'assignment requires a writable scalar'),
'declared_const': ('struct S {const short x;};int main(void){struct S s;s.x=1;return 0;}', 'assignment requires a writable scalar'),
'const_alias': ('struct S {short x;};int main(void){const struct S *s;short *p=&s->x;return 0;}', 'conversion discards const qualification'),
'const_pointer_alias': ('struct S {short *p;};int main(void){const struct S *s;short **p=&s->p;return 0;}', 'conversion discards const qualification'),
'const_arithmetic': ('struct S {short x;};int main(void){const struct S *p;(p+1)->x=1;return 0;}', 'assignment requires a writable scalar'),
'const_conditional': ('struct S {short x;};int main(void){struct S *a;const struct S *b;short *p=0?&a->x:&b->x;return 0;}', 'conversion discards const qualification'),
'const_argument': ('struct S {short *p;};void f(short **p);int main(void){const struct S *s;f(&s->p);return 0;}', 'incompatible argument'),
'array_assignment': ('struct S {short a[2];};int main(void){struct S s;s.a=0;return 0;}', 'assignment requires a writable scalar'),
'aggregate_compound': (ITEM+'struct Box {struct Item item;};int main(void){struct Box a,b;a.item+=b.item;return 0;}', 'struct values are not implemented'),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    support.OUT = OUT
    report = {}
    extra = [ROOT/'build/arithmetic.o', ROOT/'build/integers.o', ROOT/'build/ieee_engine.o']
    for name,source in CASES.items():
        cfile,rom,labels = support.compile_case(name,source,extra_objects=extra)
        exe = OUT/(name+'-host.exe')
        support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/W4','/O2','/wd4101','/wd4552','/D__far=',
                     '/Fo'+str(OUT/(name+'-host.obj')),'/Fe'+str(exe),cfile])
        host = subprocess.run([str(exe)],timeout=5)
        assert host.returncode == 0,(name,host.returncode)
        report[name] = dict(runtime=support.emulate(rom,labels,0),rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest())
        print('PASS member '+name,flush=True)
    # Scalar arrow accesses retain a fixed displacement from X. A named object's
    # field uses its fixed address directly. These inspect useful codegen shapes
    assembly = (OUT/'addressing.s').read_text()
    quantity = assembly.split('_quantity:\n',1)[1].split('__size_quantity',1)[0]
    price = assembly.split('_price:\n',1)[1].split('__size_price',1)[0]
    setter = assembly.split('_set_quantity:\n',1)[1].split('__size_set_quantity',1)[0]
    assert 'lda a:$0002,x' in quantity and 'adc #$0002' not in quantity
    assert 'lda a:$0004,x' in price and 'lda a:$0006,x' in price
    assert 'sta a:$0002,x' in setter
    assert 'sta a:.loword(_global+$0002)' in assembly
    copy = assembly.split('_copy_price:\n',1)[1].split('__size_copy_price',1)[0]
    reset = assembly.split('_reset_price:\n',1)[1].split('__size_reset_price',1)[0]
    compare = assembly.split('_matches_price:\n',1)[1].split('__size_matches_price',1)[0]
    assert 'sta a:$0004,x' in copy and 'sta a:$0006,x' in copy and '__arith_lhs' not in copy,copy
    assert 'stz a:$0004,x' in reset and 'sta a:$0006,x' in reset,reset
    assert 'lda a:$0004,x' in compare and 'lda a:$0006,x' in compare and 'pha' not in compare,compare
    known = (OUT/'known_backing.s').read_text()
    branch = known.split('\n_matches_packet:\n',1)[1].split('__size_matches_packet',1)[0]
    assert 'lda a:.loword(_packet+$0005)' in branch and 'pha' not in branch,branch
    setter = known.split('\n_set_payload:\n',1)[1].split('__size_set_payload',1)[0]
    assert 'sta a:.loword(_packet+$0005)' in setter,setter
    members = (OUT/'private_members.s').read_text()
    for name,visible in (('only_members',False),('publish_member',True)):
        entry = members.split('\n_'+name+':\n',1)[0].rsplit('; allocation function ',1)[1]
        assert ('; caller frame address visible' in entry)==visible,entry
    returned = (OUT/'returned_members.s').read_text()
    def body(name):
        return returned.split('\n_'+name+':\n',1)[1].split('__size_'+name,1)[0]
    assert '    pha\n' not in body('rebuild_pair'),body('rebuild_pair')
    assert 'from a call result' not in body('private_result'),body('private_result')
    assert 'from a call result' in body('addressable_result'),body('addressable_result')
    assert '; literal aggregate return' in body('literal_record'),body('literal_record')
    assert 'lda #$7F80' in body('literal_record') and 'lda #$FB2E' in body('literal_record')
    assert '; literal aggregate return' in body('literal_slice') and 'lda #$ABCD' in body('literal_slice')
    assert '; literal aggregate return' not in body('dynamic_record'),body('dynamic_record')
    normalize = (OUT/'member_parameter.s').read_text().split('_normalize:\n',1)[1].split('__size_normalize',1)[0]
    assert '    phx\n' not in normalize and normalize.count(',x')>=4,normalize
    # Alias/evaluation checks also run with optional codegen passes disabled
    original_run = support.run
    def plain(command,*args,**kwargs):
        if Path(command[0]).name == 'zicc.exe':
            command = [*command,'--no-strength-reduction','--no-register-loops','--no-indexed-dpage','--no-divmod-reuse']
        return original_run(command,*args,**kwargs)
    try:
        support.run = plain
        for name in ('evaluation','nested'):
            _,rom,labels = support.compile_case(name+'-plain',CASES[name],extra_objects=extra)
            report[name+'-plain'] = dict(runtime=support.emulate(rom,labels,0),rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest())
    finally:
        support.run = original_run
    diagnostics = {}
    for name,(source,message) in INVALID.items():
        cfile=OUT/(name+'.c');cfile.write_text(source)
        result=subprocess.run([str(ROOT/'build/zicc.exe'),str(cfile),'-o',str(OUT/(name+'.s'))],capture_output=True,text=True)
        assert result.returncode and message in result.stderr,(name,result.stderr)
        assert re.search(r':\d+:\d+: error:',result.stderr),result.stderr
        diagnostics[name]=result.stderr.strip()
    result = dict(compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest(),runtime=report,diagnostics=diagnostics)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'PASS: {len(CASES)} MSVC/Mesen member cases, two plain variants, field-displacement codegen, {len(INVALID)} diagnostics')


if __name__ == '__main__':
    main()
    spec=importlib.util.spec_from_file_location('copies',ROOT/'tests/check-aggregate-copy.py')
    copies=importlib.util.module_from_spec(spec);spec.loader.exec_module(copies)
    copies.main()
