"""Compare C and assembly rounding, including write order when addresses overlap and the effect of interrupts."""
import os
import argparse,hashlib,importlib.util,itertools,json,random,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'assembly-rounded-check';CASES=[]
def add(data,keep,scale=0,n=None,alias=0):
    CASES.append(dict(data=bytes(data),n=len(data) if n is None else n,keep=keep,scale=scale,alias=alias))
for data,keep in itertools.product(itertools.product(range(10),repeat=3),(0,1,2)):add(data,keep)
for b,keep in itertools.product(range(256),(0,1)):add((b,),keep)
for n in (1,2,6,17,199,200):
    for keep in (-1,0,1,n-1,n,n+3):add([9]*n,keep,scale=n)
for next_digit,sticky_at,parity in itertools.product((4,5,6),(None,0,98),(8,9)):
    data=[0]*200;data[199]=parity;data[99]=next_digit
    if sticky_at is not None:data[sticky_at]=1
    add(data,100,scale=150)
for data,keep,alias in itertools.product(((0,5,2),(1,5,9),(9,9,9),(0,0,0)),(-1,0,1,2,4),range(1,6)):
    if alias==3 and keep>2:continue # Character writes stay within the exponent word
    add(data,keep,alias=alias)
for n,keep,scale in ((0,-32767,32767),(0,0,32767),(-32767,0,0),(-1,6,0),(200,-32567,0),(1,0,-32766),(200,199,-32567)):
    add([9]*max(n,0),keep,scale,n=n)
rng=random.Random(65816)
for _ in range(128):
    n=rng.randrange(1,201);add([rng.randrange(10) for i in range(n)],rng.randrange(-1,n+4),rng.randrange(-150,151))
IRQ_START=len(CASES)
add([1]*200,32767);add([],16000,n=-1)

SOURCE=f'''
void decimal__rounded(int,char *,int *,int *);
void loop_interrupt_enable(void);void loop_interrupt_disable(void);
unsigned case_id,nmis,irqs,irq_status;unsigned long interrupt_mix;
int keep,*length_ptr,*exp_ptr;char *out;
__interrupt(nmi) void rounded_nmi(void){{++nmis;interrupt_mix=(interrupt_mix<<(nmis&7))+0x10001UL;}}
__interrupt(irq) void rounded_irq(void){{unsigned before=nmis;irq_status=*(unsigned char * __far)0x4211UL;
 ++irqs;interrupt_mix=(interrupt_mix<<(irqs&7))+0x10001UL;
 while(nmis==before){{}}*(unsigned char * __far)0x4200UL=0;}}
__noinline void case_ready(void){{}}
int main(void){{for(case_id=0;case_id<{len(CASES)};++case_id){{case_ready();
 if(case_id>={IRQ_START})loop_interrupt_enable();
 decimal__rounded(keep,out,length_ptr,exp_ptr);
 if(case_id>={IRQ_START})loop_interrupt_disable();
 }}if(irqs!={len(CASES)-IRQ_START}||!nmis)return 1;return 0;}}
'''

def model(v,base,naddr,scaleaddr,optimized):
    p,length,exp=0x4000,0x3500,0x3502
    if v['alias']==1:p=(base+1)&65535
    elif v['alias']==2:exp=length
    elif v['alias']==3:p=exp
    elif v['alias']==4:length=naddr&65535
    elif v['alias']==5:exp=scaleaddr&65535
    count=max(1,v['keep']);memory={a:0xa5 for a in range(p-1,p+count+1)}
    def initial_word(a,x):memory[a]=x&255;memory[a+1]=(x>>8)&255
    initial_word(length,0xa55a);initial_word(exp,0x5aa5)
    memory.update({base+i:b for i,b in enumerate(v['data']+bytes(200-len(v['data'])))})
    initial_word(naddr,v['n']);initial_word(scaleaddr,v['scale'])
    initial=dict(memory);reads=[];writes=[]
    def read(a,word_byte=False):
        if base<=a<base+200:reads.append(a)
        if not optimized and not word_byte and base<=a+1<base+200:reads.append(a+1)
        return memory[a]
    def write(a,b):memory[a]=b&255;writes.append((a,b&255))
    def word(a):return read(a,True)|(read(a+1,True)<<8)
    def putword(a,x):write(a,x);write(a+1,x>>8)
    n,keep,scale=(v[k] for k in ('n','keep','scale'))
    # Reject undefined C intermediate arithmetic in the test vectors themselves
    assert all(-32768<=x<=32767 for x in (n-keep,n-keep-1,n-scale,n-scale-1)),v
    putword(exp,n-scale-1);rounding=False
    if keep<0:write(p,48);putword(length,1)
    else:
        index=n-keep-1
        if keep<n:
            next_digit=read(base+index) if index>=0 else 0;sticky=0
            if not optimized or next_digit==5:
                for i in range(index):
                    sticky |= read(base+i)
                    if optimized and sticky:break
            rounding=next_digit>5 or next_digit==5 and (sticky or keep>0 and read(base+n-keep)&1)
        if keep==0:
            write(p,49 if rounding else 48);putword(length,1)
        else:
            putword(length,keep)
            for i in range(keep):write(p+i,48+read(base+n-1-i) if i<n else 48)
            if rounding:
                i=keep-1
                while i>=0:
                    digit=read(p+i)
                    if digit!=57:break
                    write(p+i,48);i-=1
                if i>=0:write(p+i,digit+1 if optimized else read(p+i)+1)
                else:write(p,49)
                rounding=i<0
        if rounding:
            value=word(exp);value=value if value<32768 else value-65536
            assert value<32767,v
            if optimized:putword(exp,value+1)
            else:
                # The C selector now uses native INC word. 65816 RMW stores
                # high then low; the hand-written routine retains STA order
                # Assert this exact bus trace, not an unordered write set
                write(exp+1,(value+1)>>8);write(exp,value+1)
    return dict(p=p,length=length,exp=exp,initial=initial,reads=reads,writes=writes,
                output=bytes(memory[a] for a in range(p-1,p+count+1)),
                raw=bytes(memory[base+i] for i in range(200)),n=word(naddr),scale=word(scaleaddr),
                length_value=word(length),exp_value=word(exp))

def lua_bytes(b):
    return '..'.join(f'string.rep(string.char({x[0]}),{len(x)})' if len(x)>50 else '"'+''.join('\\'+format(y,'03d') for y in x)+'"' for x in (bytes(g) for _,g in itertools.groupby(b))) if b else '""'

def build():
    OUT.mkdir(parents=True,exist_ok=True);ref=OUT/'reference';ref.mkdir(exist_ok=True)
    source=ref/'decimal.c';source.write_text('#define ZICC_ALL_C_REFERENCE 1\n' + (ROOT / 'runtime/ieee32/decimal.c').read_text())
    c.run([ROOT/'build/zicc.exe',source,'-o',source.with_suffix('.s'),'-I',ROOT/'include','--runtime-objects','dec_digits,dec_n,dec_scale,dec_output'])
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',source.with_suffix('.o'),source.with_suffix('.s')])
    assert '_decimal__rounded:' in source.with_suffix('.s').read_text()
    # Arm from scanline zero so IRQ100 cannot occur in the caller's setup
    # Retain both required live interrupts, including the NMI nested in IRQ
    enable_source=OUT/'enable.s'
    enable_text=(ROOT/'tests/far_loop_interrupts.s').read_text()
    enable_text=enable_text.replace('    lda #100', '''@vblank:
    lda f:$004212
    bpl @vblank
@active:
    lda f:$004212
    bmi @active
    lda #100''',1)
    enable_source.write_text(enable_text)
    enable=enable_source.with_suffix('.o');c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',enable,enable_source])
    report={}
    for mode in ('reference','assembly'):
        c.OUT=OUT/mode;c.OUT.mkdir(parents=True, exist_ok=True)
        implementation=[source.with_suffix('.o')] if mode=='reference' else [ROOT/'build/decimal.o']
        c.compile_case('driver',SOURCE,extra_objects=[enable,*[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables','io')],*implementation])
        for region in ('ntsc','pal'):
            report[mode+'-'+region]=c.run([sys.executable,__file__,'--mode',mode,'--region',region],timeout=240).stdout
            print(report[mode+'-'+region].strip(),flush=True)
    report['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'runtime/ieee32/decimal.c',ROOT/'runtime/ieee32/rounded.s',ROOT/'build/decimal.o',ROOT/'build/zicc.exe')}
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')

def worker(mode,region):
    directory=OUT/mode;home=directory/region;home.mkdir(exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(directory/'driver.labels').read_text(),re.M)}
    base,naddr,scaleaddr=[sy['decimal__'+name]&0x1ffff for name in ('dec_digits','dec_n','dec_scale')]
    vectors=[]
    for v in CASES:
        m=model(v,base,naddr,scaleaddr,mode=='assembly')
        # Memory callbacks use CPU addresses; explicit reads/writes use WRAM offsets
        vectors.append('{keep='+str(v['keep']&65535)+',p='+str(m['p'])+',length='+str(m['length'])+',exp='+str(m['exp'])+
            ',seed={'+','.join('{'+str(a)+','+str(b)+'}' for a,b in m['initial'].items())+'}'+
            ',reads={'+','.join(str(0x7e0000|a) for a in m['reads'])+'},writes={'+','.join('{'+str(0x7e0000|a)+','+str(b)+'}' for a,b in m['writes'])+'}'+
            ',output='+lua_bytes(m['output'])+',raw='+lua_bytes(m['raw'])+',n='+str(m['n'])+',scale='+str(m['scale'])+
            ',length_value='+str(m['length_value'])+',exp_value='+str(m['exp_value'])+'}')
    script='local function assert(ok,message)if not ok then emu.breakExecution();error(message or "assertion")end end\nlocal vectors={'+','.join(vectors)+'}\n'
    script+=f'''
local record=nil;local registered=false;local timings={{}};local calls,returns=0,0
local depth,entries,interrupt_returns,nested=0,0,0,0;local live={{}}
local function word(a)return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false)end
local function setword(a,v)emu.write16(a&0x1ffff,v&65535,emu.memType.snesWorkRam)end
emu.addMemoryCallback(function()
 assert(not record,'previous call');local v=vectors[word({sy['case_id']})+1]
 for _,x in ipairs(v.seed)do emu.write(x[1],x[2],emu.memType.snesWorkRam)end
 setword({sy['keep']},v.keep);setword({sy['out']},v.p);setword({sy['length_ptr']},v.length);setword({sy['exp_ptr']},v.exp)
end,emu.callbackType.exec,{sy['case_ready']},{sy['case_ready']})
emu.addMemoryCallback(function()
 assert(not record,'rounded reentered');local s=emu.getState();local id=word({sy['case_id']})+1;local v=vectors[id]
 assert(s['cpu.x']==v.keep and s['cpu.a']==v.p,'register arguments')
 assert(word(s['cpu.sp']+3)==v.length and word(s['cpu.sp']+5)==v.exp,'stack arguments')
 record={{state=s,id=id,reads=0,writes=0}};calls=calls+1
 if not registered then registered=true;local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
  emu.addMemoryCallback(function()
   local r=record;if not r then return end;local s=r.state;local t=emu.getState();local v=vectors[r.id]
   assert(t['cpu.sp']==s['cpu.sp']+2,'return stack')
   for _,k in ipairs({{'y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'ABI '..k)end
   assert((t['cpu.ps']&0x3c)==(s['cpu.ps']&0x3c),'width/decimal/IRQ')
   assert(word(t['cpu.sp']+1)==v.length and word(t['cpu.sp']+3)==v.exp,'argument homes')
   assert(r.reads==#v.reads and r.writes==#v.writes,'memory work case '..r.id..' reads '..r.reads..'/'..#v.reads)
   for i=1,#v.output do assert(emu.read(v.p+i-2,emu.memType.snesWorkRam,false)==string.byte(v.output,i),'output/guard case '..r.id)end
   for i=1,200 do assert(emu.read({base}+i-1,emu.memType.snesWorkRam,false)==string.byte(v.raw,i),'decimal state')end
   assert(word({naddr})==v.n and word({scaleaddr})==v.scale and word(v.length)==v.length_value and word(v.exp)==v.exp_value,'result fields')
   timings[#timings+1]=r.id..':'..(t.masterClock-s.masterClock)..':'..(t['cpu.cycleCount']-s['cpu.cycleCount'])
   returns=returns+1;record=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{sy['decimal__rounded']},{sy['decimal__rounded']})
emu.addMemoryCallback(function(a)
 if record and depth==0 then local r=record;r.reads=r.reads+1
  assert(vectors[r.id].reads[r.reads]==a,'digit read case '..r.id..' #'..r.reads..' got '..a..' expected '..tostring(vectors[r.id].reads[r.reads]))
 end
end,emu.callbackType.read,{0x7e0000|base},{0x7e0000|(base+199)})
emu.addMemoryCallback(function(a,b)
 if record and depth==0 then local r=record;r.writes=r.writes+1;local x=vectors[r.id].writes[r.writes]
  assert(x and x[1]==a and x[2]==b,'write order case '..r.id..' #'..r.writes)
 end
end,emu.callbackType.write,0x7e0500,0x7effff)
'''
    for name in ('rounded_irq','rounded_nmi'):
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
    script+=f'''emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0 and s['cpu.sp']==1279,'driver result/stack')
 assert(calls=={len(CASES)} and returns==calls and not record,'call coverage')
 assert(entries==interrupt_returns and depth==0 and nested>={len(CASES)-IRQ_START},'interrupt coverage')
 for i={IRQ_START+1},{len(CASES)} do assert((live[i] or 0)>=2,'live interrupt case '..i..' entries '..(live[i] or 0))end
 emu.log('TIMINGS '..table.concat(timings,','))
 emu.log('PASS {mode} {region} cases='..calls..' interrupts='..entries..' nested='..nested);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    (home/'check.lua').write_text(script);core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1
        config.DisableFrameSkipping=True;config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(directory/'driver.sfc',home/'check.lua',script);core.start();log=core.wait_for('PASS',210)
        rows=[dict(case=int(i),master_clocks=int(master),cpu_cycles=int(cpu)) for i,master,cpu in re.findall(r'(\d+):(\d+):(\d+)',log)]
        assert len(rows)==len(CASES);(home/'timings.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(next(line for line in log.splitlines() if line.startswith('PASS ')))
    finally:core.close_with_log(home/'check.log')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('reference','assembly'));p.add_argument('--region',choices=('ntsc','pal'));a=p.parse_args()
    if a.mode:worker(a.mode,a.region)
    else:build()
