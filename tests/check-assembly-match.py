"""Compare C and assembly results, count the bytes each reads and writes, and test calls during IRQs and NMIs."""
import os
import argparse,hashlib,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'assembly-match-check'

def lower(b):return b+32 if 65<=b<=90 else b
CASES=[]
def add(tag,s,w,sk=0,wk=0):
    n=0
    while w[n]:
        if lower(s[n])!=w[n]:
            CASES.append(dict(tag=tag,s=s,w=w,sk=sk,wk=wk,result=0,iterations=n+1,matched=False));return
        n+=1
    CASES.append(dict(tag=tag,s=s,w=w,sk=sk,wk=wk,result=n,iterations=n,matched=True))
for b in range(256):
    add('byte-'+str(b),bytes((b,0)),bytes((lower(b),0)))
    add('mismatch-'+str(b),bytes((b,0)),bytes(((lower(b)+1)&255,0)))
for tag,s,w,sk,wk in (
    ('nan',b'NaNextra\0',b'nan\0',1,1),
    ('inf',b'INFINITY\0',b'inf\0',1,0),
    ('inity',b'INITY!\0',b'inity\0',0,1),
    ('word-is-not-folded',b'NAN\0',b'NAN\0',1,1),
    ('short-input',b'na\0',b'nan\0',0,0),
    ('empty-null-input',b'',b'\0',2,1),
    ('same-buffer',b'abc\0',b'abc\0',0,2),
    ('overlap',b'abcabc\0',b'abc\0',0,3),
    ('source-crossing',b'AbCdEfGhIjK\0',b'abcdefghijk\0',4,0),
    ('word-crossing',b'AbCdEfGhIjK\0',b'abcdefghijk\0',0,4),
    ('crossing-mismatch',b'AbCdEfGhIjX\0',b'abcdefghijk\0',0,4),
    ('source-24bit-wrap',b'abc\0',b'abc\0',3,0),
    ('word-24bit-wrap',b'ABC\0',b'abc\0',1,5)):
    add(tag,s,w,sk,wk)
for n in (17,255,256,511):add('length-'+str(n),b'A'*n+b'\0',b'a'*n+b'\0')
IRQ_CASE=len(CASES)
add('int-max-live-interrupts',b'A'*32767+b'\0',b'a'*32767+b'\0')

def vector(name,values):return 'const unsigned '+name+'['+str(len(values))+']={'+','.join(str(v) for v in values)+'};\n'
SOURCE=r'''
int decimal__match(const char * __far,const char * __far);
extern const char match_rom_s[128],match_rom_w[128];
void loop_interrupt_enable(void);void loop_interrupt_disable(void);
unsigned case_id,nmis,irqs,irq_status;unsigned long interrupt_mix;
__interrupt(nmi) void match_nmi(void){++nmis;interrupt_mix=(interrupt_mix<<(nmis&7))+0x10001UL;}
__interrupt(irq) void match_irq(void){unsigned before=nmis;irq_status=*(unsigned char * __far)0x4211UL;
 ++irqs;interrupt_mix=(interrupt_mix<<(irqs&7))+0x10001UL;if(irqs==1)while(nmis==before){}
 *(unsigned char * __far)0x4200UL=0;}
const char * __far source(unsigned k){if(k==1)return match_rom_s;if(k==2)return (char * __far)0;
 if(k==3)return (char * __far)0xfffffeUL;if(k==4)return (char * __far)0x7effffUL;return (char * __far)0x7e8000UL;}
const char * __far word(unsigned k){if(k==1)return match_rom_w;if(k==2)return (char * __far)0x7e8000UL;
 if(k==3)return (char * __far)0x7e8003UL;if(k==4)return (char * __far)0x7effffUL;
 if(k==5)return (char * __far)0xfffffeUL;return (char * __far)0x7f8000UL;}
'''+vector('sk',[x['sk'] for x in CASES])+vector('wk',[x['wk'] for x in CASES])+vector('expected',[x['result'] for x in CASES])+f'''
int main(void){{for(case_id=0;case_id<{len(CASES)};++case_id){{
 if(case_id=={IRQ_CASE})loop_interrupt_enable();
 if(decimal__match(source(sk[case_id]),word(wk[case_id]))!=expected[case_id])return 1;
 if(case_id=={IRQ_CASE})loop_interrupt_disable();
 }}if(!irqs||!nmis)return 2;return 0;}}
'''

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    ref=OUT/'reference';ref.mkdir(exist_ok=True)
    source=ref/'decimal.c'
    source.write_text('#define ZICC_ALL_C_REFERENCE 1\n' + (ROOT / 'runtime/ieee32/decimal.c').read_text())
    c.run([ROOT/'build/zicc.exe',source,'-o',source.with_suffix('.s'),'-I',ROOT/'include','--runtime-objects','dec_digits,dec_n,dec_scale,dec_output'])
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',source.with_suffix('.o'),source.with_suffix('.s')])
    assert '_decimal__match:' in source.with_suffix('.s').read_text()
    fixture=OUT/'rom.s';fixture.write_text('.export _match_rom_s,_match_rom_w\n.segment "RODATA"\n_match_rom_s: .res 128,0\n_match_rom_w: .res 128,0\n')
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',fixture.with_suffix('.o'),fixture])
    enable=OUT/'enable.o';c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',enable,ROOT/'tests/far_loop_interrupts.s'])
    report={}
    for mode in ('reference','assembly'):
        c.OUT=OUT/mode;c.OUT.mkdir(parents=True, exist_ok=True)
        implementation=source.with_suffix('.o') if mode=='reference' else ROOT/'build/decimal.o'
        c.compile_case('driver',SOURCE,extra_objects=[fixture.with_suffix('.o'),enable,*[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables','io')],implementation])
        for region in ('ntsc','pal'):
            report[mode+'-'+region]=c.run([sys.executable,__file__,'--mode',mode,'--region',region],timeout=150).stdout
            print(report[mode+'-'+region].strip())
    report['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'runtime/ieee32/decimal.c',ROOT/'runtime/ieee32/match.s',ROOT/'build/decimal.o',ROOT/'build/zicc.exe')}
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')

def lua_bytes(b):
    if len(b)>100 and b[-1]==0 and all(x==b[0] for x in b[:-1]):return f'string.rep(string.char({b[0]}),{len(b)-1})..string.char(0)'
    return '"'+''.join('\\'+format(x,'03d') for x in b)+'"'

def worker(mode,region):
    directory=OUT/mode;home=directory/region;home.mkdir(exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(directory/'driver.labels').read_text(),re.M)}
    vectors='{'+','.join('{s='+lua_bytes(x['s'])+',w='+lua_bytes(x['w'])+',result='+str(x['result'])+',reads='+str((3 if mode=='reference' else 2)*x['iterations']+int(x['matched']))+'}' for x in CASES)+'}'
    script=f'''local vectors={vectors}
local calls,returns,depth,nested,entries,interrupt_returns,live=0,0,0,0,0,0,0
local record=nil;local registered=false;local timings={{}}
local function word(a)return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false)end
local function seed(p,s)
 for i=1,#s do local a=(p+i-1)&0xffffff;local b=string.byte(s,i)
  if a<0x2000 or a>=0x7e0000 and a<=0x7fffff then emu.write(a&0x1ffff,b,emu.memType.snesWorkRam)
  else emu.write(a&0x7fff,b,emu.memType.snesPrgRom)end
 end
end
emu.addMemoryCallback(function()
 assert(not record,'match reentered');local s=emu.getState();local id=word({sy['case_id']})+1;local v=vectors[id];assert(v,'case id')
 local p=word(s['cpu.sp']+3)|(word(s['cpu.sp']+5)<<16);local w=word(s['cpu.sp']+7)|(word(s['cpu.sp']+9)<<16)
 seed(p,v.s);seed(w,v.w);local scratch={{}};for i=4,15 do scratch[i]=word(0x02+2*i)end
 local args={{}};for i=1,4 do args[i]=word(s['cpu.sp']+1+2*i)end
 record={{state=s,id=id,reads=0,scratch=scratch,args=args}};calls=calls+1
 if not registered then registered=true;local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
  emu.addMemoryCallback(function()
   local r=record;if not r then return end;local t=emu.getState();local s=r.state;local v=vectors[r.id]
   assert(t['cpu.sp']==s['cpu.sp']+2 and t['cpu.a']==v.result,'return/stack case '..r.id)
   for _,k in ipairs({{'y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'ABI '..k)end
   assert((t['cpu.ps']&0x3c)==(s['cpu.ps']&0x3c),'width/decimal/IRQ')
   for i=1,4 do assert(word(t['cpu.sp']+2*i-1)==r.args[i],'argument home')end
   for i=4,15 do assert(word(0x02+2*i)==r.scratch[i],'undocumented scratch')end
   assert(r.reads==v.reads,'byte work case '..r.id..' '..r.reads..'/'..v.reads)
   timings[#timings+1]=r.id..':'..(t.masterClock-s.masterClock)..':'..(t['cpu.cycleCount']-s['cpu.cycleCount'])
   returns=returns+1;record=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{sy['decimal__match']},{sy['decimal__match']})
'''
    ranges=((0x7e8000,0x7fffff),(sy['match_rom_s'],sy['match_rom_s']+127),(sy['match_rom_w'],sy['match_rom_w']+127),(0xfffffe,0xffffff),(0,1))
    for low,high in ranges:script+=f'emu.addMemoryCallback(function()if record and depth==0 then record.reads=record.reads+1 end end,emu.callbackType.read,{low},{high})\n'
    for name in ('match_irq','match_nmi'):
        script+=f'''emu.addMemoryCallback(function()
 entries=entries+1;depth=depth+1;if depth>1 then nested=nested+1 end;if record then live=live+1 end
 local s=emu.getState();local sp=s['cpu.sp'];local ps=emu.read(sp+1,emu.memType.snesWorkRam,false)
 local target=(emu.read(sp+4,emu.memType.snesWorkRam,false)<<16)|word(sp+2);local scratch={{}}
 for i=0,15 do scratch[i]=word(0x02+2*i)end;local done=false
 emu.addMemoryCallback(function()
  local t=emu.getState();if done or t['cpu.sp']~=sp+4 then return end;done=true;interrupt_returns=interrupt_returns+1;depth=depth-1
  for _,k in ipairs({{'a','x','y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'interrupt '..k)end
  assert(t['cpu.ps']==ps and t['cpu.k']==(target>>16),'interrupt frame/status')
  for i=0,15 do assert(word(0x02+2*i)==scratch[i],'interrupt scratch')end
 end,emu.callbackType.exec,target,target)
end,emu.callbackType.exec,{sy[name]&65535},{sy[name]&65535})
'''
    script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0 and s['cpu.sp']==1279,'driver result/stack')
 assert(calls=={len(CASES)} and returns==calls and not record,'call coverage')
 assert(entries==interrupt_returns and depth==0 and nested>0 and live>0,'interrupt coverage')
 emu.log('TIMINGS '..table.concat(timings,','))
 emu.log('PASS {mode} {region} cases='..calls..' interrupts='..entries..' live='..live..' nested='..nested);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1
        config.DisableFrameSkipping=True;config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(directory/'driver.sfc',home/'check.lua',script);core.start();log=core.wait_for('PASS',120)
        rows=[dict(case=int(i),master_clocks=int(master),cpu_cycles=int(cpu)) for i,master,cpu in re.findall(r'(\d+):(\d+):(\d+)',log)]
        assert len(rows)==len(CASES)
        (home/'timings.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(next(line for line in log.splitlines() if line.startswith('PASS ')))
    finally:core.close_with_log(home/'check.log')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('reference','assembly'));p.add_argument('--region',choices=('ntsc','pal'));a=p.parse_args()
    if a.mode:worker(a.mode,a.region)
    else:build()
