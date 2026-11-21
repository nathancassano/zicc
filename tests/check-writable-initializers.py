"""One linked DATA image, copied before console/main, including odd/empty spans."""
import os
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'writable-initializer-check'
spec = importlib.util.spec_from_file_location('data_support',ROOT/'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)

DEFINITIONS = '''struct Item {char tag;short count;unsigned long price;};
union Value {short number;char bytes[5];};
short zero_words[19];
char zero_bytes[3];
char first=17;
short negative=-2;
struct Item item={7,3,0x12345678UL};
union Value value={0x1234};
short words[4]={1,2};
float real=1.5f;
static short private_value=9;
short private_get(void){return private_value;}
void private_set(void){private_value=27;}
'''
MAIN = '''struct Item {char tag;short count;unsigned long price;};
union Value {short number;char bytes[5];};
extern short zero_words[19];extern char zero_bytes[3];
extern char first;extern short negative;extern struct Item item;
extern union Value value;extern short words[4];extern float real;
short private_get(void);void private_set(void);
char last=33;
const short rom_word=123;
int main(void){int i;
 if(first!=17||negative!=-2||item.tag!=7||item.count!=3||item.price!=0x12345678UL)return 1;
 if(value.number!=0x1234||value.bytes[4]!=0||words[0]!=1||words[1]!=2||words[3]!=0)return 2;
 if(real!=1.5f||last!=33||private_get()!=9||rom_word!=123)return 3;
 for(i=0;i<19;++i)if(zero_words[i])return 4;
 for(i=0;i<3;++i)if(zero_bytes[i])return 5;
 first=18;negative=-7;item.count+=5;item.price=99;value.bytes[0]=0x56;
 for(i=0;i<4;++i)words[i]=i+10;
 real=2.5f;last=44;private_set();
 if(first!=18||negative!=-7||item.count!=8||item.price!=99UL||value.number!=0x1256)return 6;
 if(words[3]!=13||real!=2.5f||last!=44||private_get()!=27||rom_word!=123)return 7;
 return 0;
}
'''


def image_at(rom, address, size):
    # All fixtures use the single-bank LoROM config
    return rom[address & 0x7fff:(address & 0x7fff)+size]


def verify(name, source, images, extra_objects=(), console=False, expected_size=None):
    _, rom, labels = support.compile_case(name,source,console=console,extra_objects=extra_objects)
    data = rom.read_bytes()
    load, run, size = (labels['_DATA_'+kind+'__'] for kind in ('LOAD','RUN','SIZE'))
    assert run >= 0x7e0500 and run+size <= 0x7f0000
    assert load >= 0x808000 and (load & 0xffff)+size <= 0x10000
    if expected_size is not None:
        assert size == expected_size,(name,size)
    # The linked image contains objects from every contributing translation unit
    for symbol, image in images.items():
        offset = labels[symbol]-run
        assert 0 <= offset <= size-len(image),(symbol,offset,size)
        assert image_at(data,load+offset,len(image)) == image,symbol
    # Exactly one channel-0 DMA trigger in the startup copy region, irrespective of object count
    copy = image_at(data,labels['data_copy'],labels['data_copied']-labels['data_copy'])
    assert copy.count(bytes.fromhex('a9018d0b42')) == 1,copy.hex()
    # Check the complete RAM image, including linker/interior padding, before any
    # application code runs. Seeded WRAM additionally verifies the preceding clear
    image = image_at(data,load,size)
    values = ','.join(str(b) for b in image)
    checkpoints = [labels['main']]
    if console:
        checkpoints.insert(0,labels['console_init'])
    original_run = support.run
    def instrument(command, *args, **kwargs):
        if '--testRunner' in command:
            lua = Path(command[-1]);script = 'for i=0,0x1ffff do emu.write(((i)&0x1ffff),0xa5,emu.memType.snesWorkRam) end\n'+lua.read_text()
            script += '\nlocal expected_data={'+values+'}\n'
            for address in checkpoints:
                script += f'''emu.addMemoryCallback(function()
 local s=emu.getState()
 if s['cpu.dbr']~=0x7e or s['cpu.d']~=0 or (s['cpu.ps'] & 0x30)~=0 then error('DATA copy ABI') end
 for i,v in ipairs(expected_data) do
  if emu.read((({run}+i-1)&0x1ffff),emu.memType.snesWorkRam,false)~=v then error('DATA copy byte '..i) end
 end
 print('DATA_IMAGE_OK {address}')
end,emu.callbackType.exec,{address},{address})
'''
            lua.write_text(script)
        return original_run(command,*args,**kwargs)
    support.run = instrument
    try:
        log = support.emulate(rom,labels,0)
    finally:
        support.run = original_run
    for address in checkpoints:
        assert f'DATA_IMAGE_OK {address}' in log,log
    return dict(load=load,run=run,size=size,image_sha256=hashlib.sha256(image).hexdigest(),
                rom_sha256=hashlib.sha256(data).hexdigest(),runtime=log)


def main():
    OUT.mkdir(parents=True,exist_ok=True);support.OUT=OUT
    extra = [ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o']
    report = {}
    report['empty'] = verify('empty','short zero;int main(void){return zero;}',{},expected_size=0)
    report['one'] = verify('one','char x=91;int main(void){if(x!=91)return 1;x=7;return x!=7;}',{'x':bytes([91])},expected_size=1)
    report['odd'] = verify('odd','char x[3]={1,2,3};int main(void){if(x[2]!=3)return 1;x[1]=9;return x[1]!=9;}',{'x':bytes([1,2,3])},expected_size=3)
    blob = bytes((i*37+1)&255 for i in range(1025))
    source = 'char blob[1025]={'+','.join(map(str,blob))+'''};
short guard[9];
int main(void){int i;for(i=0;i<1025;++i)if(blob[i]!=(char)(i*37+1))return 1;
 for(i=0;i<9;++i)if(guard[i])return 2;
 blob[0]=77;blob[1024]=88;return blob[0]!=77||blob[1024]!=88;}
'''
    report['large_odd'] = verify('large_odd',source,{'blob':blob},extra_objects=extra,expected_size=1025)
    path=OUT/'definitions.c';path.write_text(DEFINITIONS)
    support.run([ROOT/'build/zicc.exe',path,'-o',OUT/'definitions.s'])
    support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',OUT/'definitions.o',OUT/'definitions.s'])
    images = {'first':bytes([17]),'negative':struct.pack('<h',-2),
              'item':struct.pack('<BxhI',7,3,0x12345678),'value':bytes.fromhex('341200000000'),
              'words':struct.pack('<4h',1,2,0,0),'real':struct.pack('<f',1.5),'last':bytes([33])}
    for console in (False,True):
        name='multiple_console' if console else 'multiple'
        report[name]=verify(name,MAIN,images,extra_objects=[OUT/'definitions.o',*extra],console=console)
    # MSVC checks the same separate-TU initialization/write semantics. Layout
    # bytes and target widths are verified above rather than assumed identical
    host=OUT/'host.exe';main=OUT/'multiple.c'
    support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(OUT)+'/',
                 '/Fe'+str(host),main,path])
    support.run([host])
    (OUT/'results.json').write_text(json.dumps(dict(cases=report,
        compiler_sha256=hashlib.sha256((ROOT/'build/zicc.exe').read_bytes()).hexdigest(),
        startup_sha256=hashlib.sha256((ROOT/'runtime/startup.s').read_bytes()).hexdigest()),indent=2)+'\n')
    print('PASS: empty/one/odd/1025-byte DATA; separate-TU scalar/aggregate images, writes, seeded RAM; pre-console/main copy and ABI; MSVC reference')


if __name__=='__main__':
    main()
