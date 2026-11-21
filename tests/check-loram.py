"""Check low-RAM variables across C files, including startup copies and addresses shared with the stack."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'loram-check'
spec = importlib.util.spec_from_file_location('loram_support', ROOT/'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
CC65 = support.CC65

DEFS = '''__loram unsigned char low[0x1afe];
extern __loram const unsigned marker;
const unsigned marker=0x1234;
unsigned touch(unsigned char *p,unsigned n){p[0]=19;p[n-1]=37;return p[0]+p[n-1];}
'''
DRIVER = '''#include <stdlib.h>
extern __loram unsigned char low[0x1afe];
extern __loram const unsigned marker;
unsigned touch(unsigned char *p,unsigned n);
unsigned ordinary;
unsigned initialized=0x5678;
unsigned recurse(unsigned n){unsigned char local[16];local[0]=(unsigned char)n;
 if(n)return recurse(n-1)+local[0];return 0;}
int main(void){unsigned char local[16];unsigned char *p;void *heap;
 if(marker!=0x1234||initialized!=0x5678||ordinary||low[0]||low[0x1afd])return 1;
 if(sizeof(&marker)!=2||sizeof(low)!=0x1afe)return 2;
 if(touch(low,sizeof(low))!=56||low[0]!=19||low[0x1afd]!=37)return 3;
 if(touch(local,sizeof(local))!=56||local[0]!=19||local[15]!=37)return 4;
 p=local;if((unsigned)p<0x100||(unsigned)p>=0x500)return 5;
 if(recurse(6)!=21)return 6;
 heap=malloc(8);if(!heap||(unsigned)heap<0x2000)return 7;
 free(heap);ordinary=91;initialized+=2;
 return ordinary!=91||initialized!=0x567a;
}
'''


def labels(path):
    return {n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',path.read_text(),re.M)}


def check_stack_layout(sy, size):
    assert sy['_STACK_SIZE__']==size and sy['_STACK_BOTTOM__']==0x100
    assert sy['_STACK_TOP__']==0xff+size
    assert sy['_NEAR_START__']==0x7e0100+size and sy['_NEAR_SIZE__']==0xff00-size


def compile_unit(name, text):
    source=OUT/(name+'.c');source.write_text(text)
    asm=source.with_suffix('.s');obj=source.with_suffix('.o')
    support.run([ROOT/'build/zicc.exe',source,'-o',asm,'-I',ROOT/'include'])
    support.run([CC65/'ca65.exe','--cpu','65816','-g','-o',obj,asm])
    return source,obj


def reject(name, definitions, use='', diagnostic='__loram'):
    source,obj=compile_unit(name,definitions+'\nint main(void){'+use+'return 0;}\n')
    result=subprocess.run([str(CC65/'ld65.exe'),'-C',str(ROOT/'linker/lorom32.cfg'),
        '-o',str(source.with_suffix('.raw')),str(ROOT/'build/startup.o'),str(obj),
        str(ROOT/'build/nmi.o'),str(ROOT/'build/vectors.o'),str(ROOT/'build/rom_header.o')],
        capture_output=True,text=True)
    assert result.returncode and diagnostic in result.stderr,result.stderr


def main():
    OUT.mkdir(parents=True, exist_ok=True);support.OUT=OUT
    resume=sys.argv[1:]==['--resume']
    if sys.argv[1:] and not resume:raise SystemExit('usage: check-loram.py [--resume]')
    checkpoint = OUT / 'resume.json'
    identity = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (ROOT / 'build/zicc.exe', Path(__file__))}
    saved = dict(inputs=identity, cases={})
    if resume and checkpoint.is_file():
        previous = json.loads(checkpoint.read_text(encoding='utf-8'))
        if previous['inputs'] == identity:
            saved = previous

    def artifact_hashes(raw):
        return {suffix: hashlib.sha256(raw.with_suffix(suffix).read_bytes()).hexdigest()
                for suffix in ('.sfc', '.labels')}

    def completed_case(name, raw):
        case = saved['cases'].get(name)
        if case and all(raw.with_suffix(suffix).is_file() for suffix in ('.sfc', '.labels')):
            if case['artifacts'] == artifact_hashes(raw):
                return case['output']
        return None

    def checkpoint_case(name, raw, output):
        saved['cases'][name] = dict(artifacts=artifact_hashes(raw), output=output)
        temporary = checkpoint.with_suffix('.tmp')
        temporary.write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
        temporary.replace(checkpoint)
        return output

    defs,defs_obj=compile_unit('lowdefs',DEFS)
    driver,driver_obj=compile_unit('lowdriver',DRIVER)
    source,probe_obj=compile_unit('stack-probe','''__loram volatile unsigned pinned;
int main(void){pinned=123;return pinned!=123;}
''')
    unpinned=OUT/'stack-unpinned.c'
    unpinned.write_text(source.read_text().replace('__loram ', ''))
    report={}
    for stage in (1,2,3,4):
        raw=OUT/f'stage{stage}.raw'
        name = f'stage{stage}'
        prior_output = completed_case(name, raw)
        if prior_output is not None:
            report[name] = prior_output
            continue
        support.run([sys.executable,ROOT/'tools/build-rom.py',defs,driver,'-o',raw,'--stage',str(stage)],timeout=120)
        sy=labels(raw.with_suffix('.labels'))
        assert sy['low']==0x7e0500 and sy['marker']==0x7e1ffe
        assert sy['ordinary']>=0x7e2000 and sy['initialized']>=0x7e2000
        check_stack_layout(sy,1024)
        rom=raw.with_suffix('.sfc')
        support.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        extra=f'''local tracking=false
emu.addMemoryCallback(function() tracking=true end,emu.callbackType.exec,{sy['main']},{sy['main']})
emu.addMemoryCallback(function()
 if tracking then require_value(emu.getState()['cpu.sp']>=0x100,'stack entered direct page') end
end,emu.callbackType.exec,0,0xffffff)
'''
        report[name] = checkpoint_case(name, raw, support.emulate(rom,sy,0,seed=True,extra_checks=extra))
    # The same object constraints and initialization work in every manual layout
    manual_base=[CC65/'ld65.exe','-C',ROOT/'linker/lorom32.cfg',
                 ROOT/'build/startup.o',probe_obj,ROOT/'build/nmi.o',
                 ROOT/'build/vectors.o',ROOT/'build/rom_header.o']
    for cfg in sorted((ROOT/'linker').glob('*.cfg')):
        raw=OUT/(cfg.stem+'.raw');vector=ROOT/'build/vectors.o'
        flags=[]
        if cfg.stem.startswith('hirom'):
            vector=OUT/'hirom-vectors.o'
            if not vector.exists():
                support.run([CC65/'ca65.exe','--cpu','65816','-D','HIROM=1','-o',vector,ROOT/'runtime/vectors.s'])
            flags=['-D','__NEAR_ROM_SIZE__=16']
        if not resume or not raw.with_suffix('.labels').exists() or cfg.stem=='lorom32':
            support.run([CC65/'ld65.exe','-C',cfg,*flags,'-o',raw,'-Ln',raw.with_suffix('.labels'),
                         '--dbgfile',raw.with_suffix('.dbg'),
                         ROOT/'build/startup.o',defs_obj,driver_obj,ROOT/'build/malloc.o',ROOT/'build/free.o',
                         ROOT/'build/arithmetic.o',ROOT/'build/ieee_engine.o',
                         ROOT/'build/nmi.o',vector,ROOT/'build/rom_header.o'])
        sy=labels(raw.with_suffix('.labels'))
        assert sy['low']==0x7e0500 and sy['marker']==0x7e1ffe and sy['ordinary']>=0x7e2000
        check_stack_layout(sy,1024)
        if cfg.stem=='lorom32':
            rom=raw.with_suffix('.sfc')
            support.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
            name = 'manual-lorom32'
            prior_output = completed_case(name, raw)
            report[name] = prior_output if prior_output is not None else checkpoint_case(
                name, raw, support.emulate(rom,sy,0,seed=True))
        override=OUT/'manual-stack.raw'
        support.run([CC65/'ld65.exe','-C',cfg,*flags,'-D','__STACK_SIZE__=1536',
                     '-o',override,'-Ln',override.with_suffix('.labels'),
                     ROOT/'build/startup.o',probe_obj,ROOT/'build/nmi.o',vector,ROOT/'build/rom_header.o'])
        sy=labels(override.with_suffix('.labels'))
        check_stack_layout(sy,1536)
        assert sy['pinned']==0x7e0700
    for size in (256,1536,7936):
        raw=OUT/f'stack-{size}.raw'
        support.run([sys.executable,ROOT/'tools/build-rom.py',unpinned if size==7936 else source,
                     '-o',raw,'--stack-size',str(size)],timeout=120)
        sy=labels(raw.with_suffix('.labels'))
        check_stack_layout(sy,size)
        assert sy['pinned']==sy['_NEAR_START__']
        rom=raw.with_suffix('.sfc')
        support.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        report[f'stack-{size}']=support.emulate(rom,sy,0,seed=True)
    for size in (255,7937):
        for command in ([sys.executable,ROOT/'tools/build-rom.py',source,'--stack-size',str(size)],
                        [*manual_base,'-D',f'__STACK_SIZE__={size}']):
            result=subprocess.run([*map(str,command),'-o',str(OUT/'invalid-stack.raw')],
                                  capture_output=True,text=True)
            assert result.returncode and 'must be between 256 and 7936 bytes' in result.stderr,result.stderr
    result=subprocess.run([*map(str,manual_base),'-D','__STACK_SIZE__=7936','-o',str(OUT/'pinned-stack.raw')],
                          capture_output=True,text=True)
    assert result.returncode and '__loram' in result.stderr,result.stderr
    # Empty DATA, small low prefix, static linkage, aggregates, pointer-object
    # placement and ordinary near allocation using the remaining low space
    small='''struct Row {char tag;unsigned value;};
__loram char *cursor;
static __loram const struct Row row={7,0x1234};
__loram unsigned char bytes[3];
unsigned ordinary;
int main(void){cursor=(char *)bytes;cursor[2]=9;
 return sizeof(&row)!=2||row.tag!=7||row.value!=0x1234||bytes[2]!=9||ordinary;}
'''
    _,rom,sy=support.compile_case('small',small)
    assert sy['ordinary']<0x7e2000
    report['small']=support.emulate(rom,sy,0)
    # Skip an oversized handler group without starving a later complete group
    # Cross-unit DATA still needs copying, while address-only operands do not
    # make their target an interrupt placement candidate
    irq_defs=OUT/'irqdefs.c'
    irq_defs.write_text('''__loram char pinned[0x1af4];
char large[0x200], ordinary_large[32], ordinary_small;
volatile unsigned hot_init=0x1234;
''')
    irq_driver=OUT/'irqdriver.c'
    irq_driver.write_text('''extern char large[], ordinary_large[];
extern volatile unsigned hot_init;
volatile unsigned hot_bss;
volatile __dpage unsigned address_sink;
__interrupt(nmi) void oversized(void){large[0]=1;hot_bss++;}
__interrupt(irq) void fits(void){hot_bss=hot_init;address_sink=(unsigned)ordinary_large;}
int main(void){return hot_init!=0x1234||hot_bss!=0;}
''')
    raw=OUT/'interrupt-placement.raw'
    support.run([sys.executable,ROOT/'tools/build-rom.py',irq_defs,irq_driver,'-o',raw],timeout=120)
    sy=labels(raw.with_suffix('.labels'))
    assert sy['pinned']==0x7e0500
    assert {sy['hot_bss'],sy['hot_init']}=={0x7e1ff4,0x7e1ff6}
    assert 0x7e1ff8<=sy['ordinary_large']<sy['ordinary_small']<sy['large']
    rom=raw.with_suffix('.sfc')
    support.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
    report['interrupt-placement']=support.emulate(rom,sy,0,seed=True)
    reject('bss-overflow','__loram char a[0x1000];__loram char b[0xb01];')
    reject('data-overflow','__loram char a[0x1b00];__loram char b=1;')
    reject('padding-overflow','struct S {unsigned x;};__loram char a[0x1aff];__loram struct S s;')
    # A used extern constraint checks the defining object's actual complete
    # size even when the declaration is an incomplete array in another TU
    foreign,foreign_obj=compile_unit('foreign','char foreign[0x1b01];')
    constraint,constraint_obj=compile_unit('constraint','extern __loram char foreign[];int main(void){return foreign[0];}')
    result=subprocess.run([str(CC65/'ld65.exe'),'-C',str(ROOT/'linker/lorom32.cfg'),'-o',str(OUT/'foreign.raw'),
        str(ROOT/'build/startup.o'),str(foreign_obj),str(constraint_obj),str(ROOT/'build/nmi.o'),
        str(ROOT/'build/vectors.o'),str(ROOT/'build/rom_header.o')],capture_output=True,text=True)
    assert result.returncode and '__loram object foreign' in result.stderr,result.stderr
    invalid=[
        '__loram int f(void);', '__loram typedef int T;', '__loram __dpage int x;',
        '__dpage extern int x;extern __loram int x;',
        'extern __loram int x;__dpage int x;',
        'int main(void){__loram int x;return 0;}',
        'int f(__loram int x);',
        'int x;extern __loram int x;',
        'extern const int x;int f(void){return x;}extern __loram const int x;',
    ]
    for i,text in enumerate(invalid):
        path=OUT/f'invalid{i}.c';path.write_text(text)
        result=subprocess.run([str(ROOT/'build/zicc.exe'),str(path),'-o',str(path.with_suffix('.s'))],capture_output=True,text=True)
        assert result.returncode and 'error:' in result.stderr,result.stderr
    # An empty DATA span may have its end-marker in bank $7F when ordinary
    # BSS fills near WRAM. Startup must skip the copy and leave bank $7F alone
    full='char near_buffer[0xfb00];int main(void){near_buffer[0]=11;near_buffer[0xfaff]=22;return near_buffer[0]!=11||near_buffer[0xfaff]!=22;}'
    _,rom,sy=support.compile_case('full-near',full)
    assert sy['near_buffer']==0x7e0500 and sy['_DATA_SIZE__']==0 and sy['_DATA_RUN__']==0x7f0000
    report['full-near']=support.emulate(rom,sy,0)
    reject('near-overflow','char near_buffer[0xfb01];',diagnostic='overflow')
    report['manual_layouts']=len(list((ROOT/'linker').glob('*.cfg')))
    report['compiler_sha256']=identity['zicc.exe']
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: __loram cross-unit size/bounds, all layouts, four runtime stages, initialization, near heap and stack aliases')


if __name__=='__main__':main()
