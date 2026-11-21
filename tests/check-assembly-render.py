"""Compare the render modes, count memory accesses, and check that calls and interrupts preserve the expected state."""
import os
import argparse,hashlib,importlib.util,itertools,json,random,re,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'assembly-render-check'
CASES=[]
def add(digits,n,e,spec,precision,alt,kind=0,p=0x4000,irq=False):
    CASES.append(dict(digits=digits,n=n,e=e,spec=ord(spec) if isinstance(spec,str) else spec,
                      precision=precision,alt=alt,kind=kind,p=p,irq=irq))
for digits,spec,e,precision,alt in itertools.product((b'0',b'123400',b'999999',b'120030'),'gGfFeE',(-6,-4,-1,0,1,5,6,38),(0,1,6,8),(0,1)):
    add(digits,len(digits),e,spec,precision,alt)
for spec,n,precision,alt in itertools.product(('g','G','f','e','?',-1,0x100),(-2,0,1),(-1,0,2),(0,0x8000)):
    add(b'12300',n,-1,spec,precision,alt)
for b in range(256):add(bytes((b,)),1,0,'f',0,0)
for kind,p,spec in itertools.product((0,1,2,3),(0x40ff,0xfff0),'gGeEfF'):
    add(b'120030',6,-1,spec,2,0,kind,p)
for n in (17,255,256,511):
    add(b'1'*n,n,0,'f',n-1,0)
for e in (-32767,-999,-100,-99,99,100,999,32767):
    add(b'12',2,e,'E',0,0)
add(b'123400',-32768,-32768,'f',1,0)
add(b'123400',0,-32768,'f',-1,0)
add(b'123400',6,32766,'f',0,0)
add(b'123400',6,32767,'E',32767,0)
IRQ_START=len(CASES)
add(b'0'*32767,32767,0,'g',6,0,irq=True)
add(b'123400',6,16000,'f',0,0,irq=True)
add(b'123400',6,0,'f',16000,0,irq=True)
add(b'123400',6,0,'E',16000,1,irq=True)
FLOAT_BITS=[0,0x80000000,1,0x80000001,0x7fffff,0x800000,0x7f7fffff,0xff7fffff,
            0x3f800000,0x4b800000,0x7f800000,0xff800000,0x7fc00000,0xffc00000]
rng=random.Random(65816);FLOAT_BITS += [rng.getrandbits(32) for _ in range(256)]
def float_text(bits):
    if bits&0x7f800000==0x7f800000:
        return ('-' if bits>>31 else '')+('nan' if bits&0x7fffff else 'inf')
    return format(struct.unpack('<f',struct.pack('<I',bits))[0],'.6g')

SOURCE=f'''
char *decimal__render(char *,const char * __far,int,int,int,int,int);
char * __far dec_format(unsigned long);
void render_interrupt_enable(void);void loop_interrupt_disable(void);
unsigned case_id,nmis,irqs,irq_status;unsigned long interrupt_mix;
unsigned phase,format_case;unsigned long value_bits;char * __far actual_text;
char *out,*expected_end;const char * __far digits;int count,exp,spec,precision,alt;
__interrupt(nmi) void render_nmi(void){{++nmis;interrupt_mix=(interrupt_mix<<(nmis&7))+0x10001UL;}}
__interrupt(irq) void render_irq(void){{unsigned before=nmis;irq_status=*(unsigned char * __far)0x4211UL;
 ++irqs;interrupt_mix=(interrupt_mix<<(irqs&7))+0x10001UL;
 while(nmis==before){{}}*(unsigned char * __far)0x4200UL=0;}}
__noinline void case_ready(void){{}}
__noinline void format_ready(void){{}}
int main(void){{for(case_id=0;case_id<{len(CASES)};++case_id){{case_ready();
 if(case_id>={IRQ_START})render_interrupt_enable();
 if(decimal__render(out,digits,count,exp,spec,precision,alt)!=expected_end)return 1;
 if(case_id>={IRQ_START})loop_interrupt_disable();
 }}if(irqs!={len(CASES)-IRQ_START}||!nmis)return 2;
 phase=1;for(format_case=0;format_case<{len(FLOAT_BITS)};++format_case){{format_ready();actual_text=dec_format(value_bits);}}
 return 0;}}
'''

def model(v,source):
    memory={(source+i)&0xffffff:b for i,b in enumerate(v['digits'])};reads=[];writes=[];p=v['p']
    def read(i):
        a=(source+i)&0xffffff;reads.append(a);return memory[a]
    def put(b):
        nonlocal p
        writes.append(b);memory[0x7e0000|p]=b;p=(p+1)&65535
    n,e,spec,precision,alt=(v[k] for k in ('n','e','spec','precision','alt'))
    upper=65<=spec<=90;spec=spec+32 if upper else spec
    if spec==ord('g'):
        if not alt:
            while n>1 and read(n-1)==48:n-=1
        if e< -4 or e>=precision:spec=ord('e');precision=(precision if alt else n)-1
        else:spec=ord('f');precision=max(0,(precision if alt else n)-e-1)
    if spec==ord('e'):
        put(read(0))
        if precision or alt:put(46)
        for i in range(precision):put(read(i+1) if i+1<n else 48)
        for b in (('E' if upper else 'e')+('-' if e<0 else '+')+str(abs(e)).zfill(2)).encode():put(b)
    else:
        if e<0:put(48)
        else:
            for i in range(e+1):put(read(i) if i<n else 48)
        if precision or alt:put(46)
        for i in range(1,precision+1):
            k=e+i;put(read(k) if 0<=k<n else 48)
    return bytes(writes),reads,p

def build():
    OUT.mkdir(parents=True,exist_ok=True);ref=OUT/'reference';ref.mkdir(exist_ok=True)
    source=ref/'decimal.c'
    source.write_text('#define ZICC_ALL_C_REFERENCE 1\n' + (ROOT / 'runtime/ieee32/decimal.c').read_text())
    c.run([ROOT/'build/zicc.exe',source,'-o',source.with_suffix('.s'),'-I',ROOT/'include','--runtime-objects','dec_digits,dec_n,dec_scale,dec_output'])
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',source.with_suffix('.o'),source.with_suffix('.s')])
    assert '_decimal__render:' in source.with_suffix('.s').read_text()
    fixture=OUT/'rom.s'
    fixture.write_text('''.setcpu "65816"
.a16
.i16
.export _render_digits, _render_interrupt_enable
.segment "RODATA"
_render_digits: .res 1024,0
.segment "CODE"
_render_interrupt_enable:
    ; Start the stress call at the frame boundary so the IRQ lands inside it
    sep #$20
.a8
:
    lda f:$004212
    bpl :-
:
    lda f:$004212
    bmi :-
    lda #4
    sta f:$004209
    lda #0
    sta f:$00420A
    lda f:$004211
    lda f:$004210
    lda #$A0
    sta f:$004200
    rep #$20
.a16
    cli
    rts
''')
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',fixture.with_suffix('.o'),fixture])
    enable=OUT/'enable.o';c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',enable,ROOT/'tests/far_loop_interrupts.s'])
    report={}
    for mode in ('reference','assembly'):
        c.OUT=OUT/mode;c.OUT.mkdir(parents=True, exist_ok=True)
        implementation=[source.with_suffix('.o')] if mode=='reference' else [ROOT/'build/decimal.o']
        c.compile_case('driver',SOURCE,extra_objects=[fixture.with_suffix('.o'),enable,*[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables','io')],*implementation])
        for region in ('ntsc','pal'):
            report[mode+'-'+region]=c.run([sys.executable,__file__,'--mode',mode,'--region',region],timeout=210).stdout
            print(report[mode+'-'+region].strip(),flush=True)
    report['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'runtime/ieee32/decimal.c',ROOT/'runtime/ieee32/render.s',ROOT/'build/decimal.o',ROOT/'build/zicc.exe')}
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')

def lua_bytes(b):
    if len(b)>100 and all(x==b[0] for x in b):return f'string.rep(string.char({b[0]}),{len(b)})'
    # Compress long runs in the stress outputs without changing their contents
    return '..'.join(f'string.rep(string.char({x[0]}),{len(x)})' if len(x)>50 else '"'+''.join('\\'+format(y,'03d') for y in x)+'"' for x in (bytes(g) for _,g in itertools.groupby(b))) if b else '""'

def worker(mode,region):
    directory=OUT/mode;home=directory/region;home.mkdir(exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(directory/'driver.labels').read_text(),re.M)}
    vectors=[]
    for v in CASES:
        source=(0x7f8000,sy['render_digits'],0x7effff,0x7e0000|v['p'])[v['kind']]
        output,reads,end=model(v,source)
        fields={**v,'source':source,'end':end};fields.pop('digits')
        fields.pop('irq');fields.pop('kind')
        vectors.append('{'+','.join('["'+k+'"]='+str(x) for k,x in fields.items())+',data='+lua_bytes(v['digits'])+',output='+lua_bytes(output)+',reads={'+','.join(str(a) for a in reads)+'}}')
    script='local function assert(ok,message) if not ok then emu.breakExecution();error(message or "assertion")end end\nlocal vectors={'+','.join(vectors)+'}\n'
    script+=f'''
local record=nil;local registered=false;local timings={{}};local calls,returns=0,0
local format_record=nil;local format_calls,format_returns=0,0
local depth,entries,interrupt_returns,nested=0,0,0,0;local live={{}}
local function word(a)return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false)end
local function setword(a,v)emu.write16(a&0x1ffff,v&65535,emu.memType.snesWorkRam)end
local function seed(p,s)
 for i=1,#s do local a=(p+i-1)&0xffffff;local b=string.byte(s,i)
  if a>=0x7e0000 and a<=0x7fffff then emu.write(a&0x1ffff,b,emu.memType.snesWorkRam)
  else emu.write(a&0x7fff,b,emu.memType.snesPrgRom)end
 end
end
emu.addMemoryCallback(function()
 assert(not record,'previous call');local v=vectors[word({sy['case_id']})+1]
 seed(v.source,v.data)
 setword({sy['out']},v.p);setword({sy['digits']},v.source&65535);setword({sy['digits']+2},v.source>>16)
 setword({sy['count']},v.n);setword({sy['exp']},v.e);setword({sy['spec']},v.spec)
 setword({sy['precision']},v.precision);setword({sy['alt']},v.alt);setword({sy['expected_end']},v['end'])
end,emu.callbackType.exec,{sy['case_ready']},{sy['case_ready']})
emu.addMemoryCallback(function()
 if word({sy['phase']})~=0 then assert(format_record,'format entry');format_record.renders=format_record.renders+1;return end
 assert(not record,'render reentered');local s=emu.getState();local id=word({sy['case_id']})+1;local v=vectors[id]
 assert(s['cpu.x']==v.p,'p argument')
 local expected={{v.source&65535,v.source>>16,v.n&65535,v.e&65535,v.spec&65535,v.precision&65535,v.alt&65535}}
 for i=1,7 do assert(word(s['cpu.sp']+1+2*i)==expected[i],'stack argument '..i)end
 local before=emu.read((v.p-1)&65535,emu.memType.snesWorkRam,false)
 local after=emu.read(v['end'],emu.memType.snesWorkRam,false)
 record={{state=s,id=id,reads=0,writes=0,args=expected,before=before,after=after}};calls=calls+1
 if not registered then registered=true;local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
  emu.addMemoryCallback(function()
   local r=record;if not r then return end;local t=emu.getState();local s=r.state;local v=vectors[r.id]
   assert(t['cpu.sp']==s['cpu.sp']+2 and t['cpu.a']==v['end'],'return/stack case '..r.id)
   for _,k in ipairs({{'y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'ABI '..k)end
   assert((t['cpu.ps']&0x3c)==(s['cpu.ps']&0x3c),'width/decimal/IRQ')
   if '{mode}'=='assembly' then for i=1,7 do assert(word(t['cpu.sp']+2*i-1)==r.args[i],'argument home')end end
   assert(r.reads==#v.reads and r.writes==#v.output,'memory work case '..r.id)
   for i=1,#v.output do assert(emu.read((v.p+i-1)&65535,emu.memType.snesWorkRam,false)==string.byte(v.output,i),'output case '..r.id)end
   assert(emu.read((v.p-1)&65535,emu.memType.snesWorkRam,false)==r.before and emu.read(v['end'],emu.memType.snesWorkRam,false)==r.after,'output guard')
   timings[#timings+1]=r.id..':'..(t.masterClock-s.masterClock)..':'..(t['cpu.cycleCount']-s['cpu.cycleCount'])
   returns=returns+1;record=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{sy['decimal__render']},{sy['decimal__render']})
local function read(a)
 if record and depth==0 then local r=record;local v=vectors[r.id];r.reads=r.reads+1
  assert(v.reads[r.reads]==a,'digit read case '..r.id..' #'..r.reads..' address '..a)
 end
end
local function write(a,b)
 if record and depth==0 then local r=record;local v=vectors[r.id];r.writes=r.writes+1
  assert(a==(0x7e0000|((v.p+r.writes-1)&65535)) and b==string.byte(v.output,r.writes),'output write case '..r.id)
 end
end
emu.addMemoryCallback(read,emu.callbackType.read,0x7e4000,0x7fffff)
emu.addMemoryCallback(read,emu.callbackType.read,{sy['render_digits']},{sy['render_digits']+1023})
emu.addMemoryCallback(write,emu.callbackType.write,0x7e3fff,0x7effff)
'''
    for name in ('render_irq','render_nmi'):
        script+=f'''emu.addMemoryCallback(function()
 entries=entries+1;depth=depth+1;if depth>1 then nested=nested+1 end
 if record then live[record.id]=(live[record.id] or 0)+1 end
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
    script+='local floats={'+','.join('{bits='+str(bits)+',text='+lua_bytes(float_text(bits).encode()+b'\0')+',finite='+('true' if bits&0x7f800000!=0x7f800000 else 'false')+'}' for bits in FLOAT_BITS)+'}\n'
    script+=f'''emu.addMemoryCallback(function()
 local v=floats[word({sy['format_case']})+1];setword({sy['value_bits']},v.bits&65535);setword({sy['value_bits']+2},v.bits>>16)
end,emu.callbackType.exec,{sy['format_ready']},{sy['format_ready']})
local format_registered=false
emu.addMemoryCallback(function()
 assert(not format_record,'format reentered');local s=emu.getState();local id=word({sy['format_case']})+1
 format_record={{state=s,id=id,renders=0}};format_calls=format_calls+1
 if not format_registered then format_registered=true;local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
  emu.addMemoryCallback(function()
   local r=format_record;if not r then return end;local s=r.state;local t=emu.getState();local v=floats[r.id]
   assert(t['cpu.sp']==s['cpu.sp']+2,'format stack')
   for _,k in ipairs({{'y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'format ABI '..k)end
   assert(r.renders==(v.finite and 1 or 0),'actual formatter work')
   local result=t['cpu.a']|(t['cpu.x']<<16)
   assert(result=={sy['decimal__dec_output']},'far formatter result')
   for i=1,#v.text do assert(emu.read((result+i-1)&0x1ffff,emu.memType.snesWorkRam,false)==string.byte(v.text,i),'binary32 format '..r.id)end
   format_returns=format_returns+1;format_record=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{sy['dec_format']},{sy['dec_format']})
emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0 and s['cpu.sp']==1279,'driver result/stack')
 assert(calls=={len(CASES)} and returns==calls and not record,'call coverage')
 assert(format_calls=={len(FLOAT_BITS)} and format_returns==format_calls and not format_record,'binary32 coverage')
 assert(entries==interrupt_returns and depth==0 and nested>={len(CASES)-IRQ_START},'interrupt coverage')
 for i={IRQ_START+1},{len(CASES)} do assert((live[i] or 0)>=2,'live interrupt case '..i)end
 emu.log('TIMINGS '..table.concat(timings,','))
 emu.log('PASS {mode} {region} cases='..calls..' floats='..format_calls..' interrupts='..entries..' nested='..nested);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    (home/'check.lua').write_text(script)
    core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1
        config.DisableFrameSkipping=True;config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(directory/'driver.sfc',home/'check.lua',script);core.start();log=core.wait_for('PASS',180)
        rows=[dict(case=int(i),master_clocks=int(master),cpu_cycles=int(cpu)) for i,master,cpu in re.findall(r'(\d+):(\d+):(\d+)',log)]
        assert len(rows)==len(CASES)
        (home/'timings.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(next(line for line in log.splitlines() if line.startswith('PASS ')))
    finally:core.close_with_log(home/'check.log')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('reference','assembly'));p.add_argument('--region',choices=('ntsc','pal'));a=p.parse_args()
    if a.mode:worker(a.mode,a.region)
    else:build()
