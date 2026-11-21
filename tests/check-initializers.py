"""Const ROM images: exact bytes, target execution and initializer diagnostics."""
import os
import importlib.util,json,re,struct,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'initializer-check'
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
SOURCE='''struct Row {char tag;short count;unsigned long price;};
struct Table {char head;struct Row rows[2];short tail;};
const char odd[3]={1,2,3};
const struct Table table={7,{{9,-2,100+25},{10,3,200UL}},};
const long negative=-2;
const unsigned short words[4]={65535U+1U,3*7,(short)-1,};
const float real=-.15e1f;
const float arithmetic=(-0.0f ? 1.0f/0.0f : (5+1.5f)*2)/4;
const int truncated=(int)(-3.75f+1);
const int ordered=2.0f<3 && !-0.0f;
const short lazy[3]={0&&(1/0),1?17:(1/0),1||(1/0)};
extern const short external;
const short external={42,};
static const unsigned long wrap=0xffffffffUL+1UL;
int main(void){int i;const struct Row * __far p=table.rows;
 if(table.head!=7||p[0].tag!=9||p[0].count!=-2||p[0].price!=125UL)return 1;
 if(p[1].price!=200UL||table.tail!=0||negative!=-2L)return 2;
 for(i=0;i<4;++i)if(words[i]!=(i==1?21:i==2?65535U:0))return 3;
 if(real!=-1.5f||lazy[0]!=0||lazy[1]!=17||lazy[2]!=1||external!=42||wrap!=0UL)return 4;
 if(arithmetic!=3.25f||truncated!=-2||ordered!=1)return 5;
 return 0;}
'''
BAD={
 'void_cast':('const int x=(void)1;','numeric constant expression'),
 'writable_pointer':('int *source;int *value=source;','constant address'),
 'writable_dpage':('__dpage int value=3;','cannot use __dpage'),
 'writable_runtime':('int f(void);int value=f();','numeric constant expression'),
 'runtime':('int f(void);const int value=f();','numeric constant expression'),
 'excess_array':('const int a[1]={1,2};','excess array initializer'),
 'excess_struct':('struct S {int a;};const struct S s={1,2};','excess struct initializer'),
 'designator':('struct S {int a;};const struct S s={.a=1};','designated initializers'),
 'pointer':('int *source;struct S {int *p;};const struct S s={source};','constant address'),
 'dpage_redecl':('__dpage extern const int x;const int x=1;','cannot use __dpage'),
 'dpage':('__dpage const int x=1;','cannot use __dpage'),
 'duplicate':('const int x=1;const int x=2;','duplicate initializer'),
 'divide':('const int x=1/0;','division by zero'),
 'floating_divide':('const float x=1.0f/0.0f;','division by zero'),
 'floating_range':('const int x=32768.0f;','conversion is out of range'),
 'shift':('const int x=1<<16;','invalid shift count'),
 'overflow':('const int x=32767+1;','signed constant expression overflows'),
 'empty':('const int x[1]={};','empty initializer'),
 'missing_braces':('struct S {int x;};const struct S s=1;','aggregate initializer'),
 'scalar_excess':('const int x={1,2};','excess scalar initializer'),
 'object_read':('const int x=1;const int y=x;','numeric constant expression'),
}

def main():
 OUT.mkdir(parents=True, exist_ok=True);support.OUT=OUT;report={}
 extra=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o']
 for name,source in [('catalog',(ROOT/'samples/structures_and_tables.c').read_text()),('images',SOURCE)]:
  _,rom,labels=support.compile_case(name,source,extra_objects=extra)
  report[name]=support.emulate(rom,labels,0)
  data=rom.read_bytes()
  if name=='catalog':
   expected=b''.join(struct.pack('<HhI',*row) for row in [(10,2,125),(20,3,200),(30,1,999)])
   assert labels['catalog']>=0x808000 and labels['catalog']%2==0
   assert data[labels['catalog']&0x7fff:(labels['catalog']&0x7fff)+24]==expected
   assembly=(OUT/'catalog.s').read_text();assert '_catalog: .res' not in assembly
  else:
   expected=bytes([7,0])+struct.pack('<BxhI',9,-2,125)+struct.pack('<BxhI',10,3,200)+bytes(2)
   for label,image in [('table',expected),('negative',struct.pack('<i',-2)),('words',struct.pack('<4H',0,21,65535,0)),('real',struct.pack('<f',-1.5))]:
    pos=labels[label]&0x7fff;assert labels[label]>=0x808000 and labels[label]%2==0
    assert data[pos:pos+len(image)]==image,(label,data[pos:pos+len(image)].hex(),image.hex())
  exe=OUT/(name+'-host.exe');support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/D__far=','/Fo'+str(OUT/(name+'-host.obj')),'/Fe'+str(exe),OUT/(name+'.c')])
  assert subprocess.run([str(exe)]).returncode==0
 for name,(source,message) in BAD.items():
  path=OUT/(name+'.c');path.write_text(source)
  p=subprocess.run([str(ROOT/'build/zicc.exe'),str(path),'-o',str(OUT/(name+'.s'))],capture_output=True,text=True)
  assert p.returncode and message in p.stderr,(name,p.stderr)
  assert re.search(r':\d+:\d+: error:',p.stderr)
 (OUT/'results.json').write_text(json.dumps(dict(runtime=report,diagnostics=len(BAD),compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest()),indent=2)+'\n')
 print(f'PASS: unchanged catalog and nested ROM images, exact bytes/alignment, MSVC/Mesen, {len(BAD)} diagnostics')
if __name__=='__main__':
 main()
 spec=importlib.util.spec_from_file_location('writable',ROOT/'tests/check-writable-initializers.py')
 writable=importlib.util.module_from_spec(spec);spec.loader.exec_module(writable)
 writable.main()
