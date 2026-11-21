"""Call 64-bit string conversions from C and check that the linker pulls in the routines on demand."""
import os
import importlib.util
from pathlib import Path
import random
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'int64-strto-check';OUT.mkdir(parents=True,exist_ok=True);c.OUT=OUT
MASK=(1<<64)-1
# text, base, unsigned, expected, consumed characters, errno
CASES=[
 ('0',0,False,0,1,0),('  -123tail',10,False,-123,6,0),
 ('9223372036854775807!',10,False,(1<<63)-1,19,0),
 ('-9223372036854775808!',10,False,-(1<<63),20,0),
 ('9223372036854775808!',10,False,(1<<63)-1,19,34),
 ('-9223372036854775809!',10,False,-(1<<63),20,34),
 ('18446744073709551615!',10,True,MASK,20,0),
 ('18446744073709551616!',10,True,MASK,20,34),
 ('-1!',0,True,MASK,2,0),('  +0xabcdefZ',0,True,0xabcdef,11,0),
 ('0778',0,False,63,3,0),('0x',0,False,0,1,0),
 ('  -x',10,False,0,0,0),('Zz!',36,True,1295,2,0),
 ('101101?',2,True,45,6,0),('12',1,False,0,0,0),
 ('0xffffffffffffffff!',16,True,MASK,18,0),
 ('0x8000000000000000!',16,False,(1<<63)-1,18,34),
 ('-0x8000000000000000!',16,False,-(1<<63),19,0),
]

def digits(value,base):
    alphabet='0123456789abcdefghijklmnopqrstuvwxyz'
    out=''
    while value:
        value,r=divmod(value,base);out=alphabet[r]+out
    return out or '0'

rng=random.Random(0x64c0ffee)
for i in range(24):
    base=(2,3,8,10,16,36)[i%6]
    unsigned=i%2==0
    value=rng.getrandbits(64 if unsigned else 63)
    neg=(i%4>=2)
    spelling=('-' if neg else '')+digits(value,base)
    result=(-value if neg else value)&MASK
    CASES.append((spelling+'!',base,unsigned,result,len(spelling),0))

def main():
    _,plain,_=c.compile_case('unused-plain','int main(void){return 0;}')
    _,archived,labels=c.compile_case('unused-archive','int main(void){return 0;}',extra_objects=[ROOT/'build/libc.a'])
    assert plain.read_bytes()==archived.read_bytes(),'unused strto64 archive changed the ROM'
    assert 'strtoll' not in labels and 'strtoull' not in labels
    source='#include <stdlib.h>\n#include <errno.h>\n'
    for i,(s,*_) in enumerate(CASES):source+=f'char input{i}[]="{s}";\n'
    source+=f'volatile unsigned long long results[{len(CASES)}]; volatile unsigned ends[{len(CASES)}],errors[{len(CASES)}];\nchar * __far end;\nint main(void){{\n'
    for i,(_,base,unsigned,_,offset,_) in enumerate(CASES):
        fn='strtoull' if unsigned else 'strtoll'
        source+=f'errno=0;results[{i}]={fn}(input{i},&end,{base});ends[{i}]=(end==input{i}+{offset});errors[{i}]=errno;\n'
    source+='return 0;}\n'
    path=OUT/'strto64.c';path.write_text(source)
    for stage in (1,3,4):
        raw=OUT/f'strto64-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',path,'--stage',str(stage),'-o',raw],timeout=120)
        sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        assert 'strtoll' in sy and 'strtoull' in sy
        rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        checks=['local once=false','emu.addMemoryCallback(function()',' if once then return end',' once=true']
        for i,(_,_,_,value,_,error) in enumerate(CASES):
            for j in range(8):
                checks.append(f" require_value(emu.read({(sy['results']&0x1ffff)+8*i+j},emu.memType.snesWorkRam,false)=={((value&MASK)>>(8*j))&255},'result {i} byte {j}')")
            for name,expected in (('ends',1),('errors',error)):
                checks.append(f" require_value(emu.read16({(sy[name]&0x1ffff)+2*i},emu.memType.snesWorkRam,false)=={expected},'{name} {i}')")
        checks.append(f"end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})")
        c.emulate(rom,sy,0,extra_checks='\n'.join(checks))
    print(f'PASS: {len(CASES)} signed/unsigned strto64 cases, LoROM and banked stages 3/4')

if __name__=='__main__':main()
