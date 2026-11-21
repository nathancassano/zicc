"""Test the decimal assembly routines directly with inputs supplied at run time."""
import os
import argparse,hashlib,importlib.util,json,random,re,struct,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'decimal-assembly/check'
FUNCTIONS=('hexval','dec-copy','exponent','dec-format','dec-format-raw','ieee-decimal','ieee-decimal-compare','hexparse','ieee-parse','dec-format-spec')
BEFORE=None
BATCH=None
BATCH_SIZES={"ieee-parse":16,"hexparse":128,"ieee-decimal-compare":256,"ieee-decimal":128,"hexval":8192}
numspec=importlib.util.spec_from_file_location('numeric',ROOT/'tests/decimal_numeric_fixture.py')
numeric=importlib.util.module_from_spec(numspec);numspec.loader.exec_module(numeric)

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'results.json').unlink(missing_ok=True)
    ref=OUT/'reference';ref.mkdir(exist_ok=True)
    source=ref/'decimal.c';source.write_text('#define ZICC_ALL_C_REFERENCE 1\n'+(ROOT/'runtime/ieee32/decimal.c').read_text())
    c.run([ROOT/'build/zicc.exe',source,'-o',source.with_suffix('.s'),'-I',ROOT/'include','--runtime-objects','dec_digits,dec_n,dec_scale,dec_output'])
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',source.with_suffix('.o'),source.with_suffix('.s')])
    hook=OUT/'hooks.s';hook.write_text('.setcpu "65816"\n.a16\n.i16\n.export _fixture_before,_fixture_after,_fixture_rom,_fixture_dec_format_call\n.import _dec_format\n.importzp __dp_scratch\n.segment "CODE"\n_fixture_before: rts\n_fixture_after: rts\n_fixture_dec_format_call:\n lda 5,s\n pha\n lda 5,s\n pha\n ldx #$A55A\n lda #$5AA5\n jsr .loword(_dec_format)\n sta z:__dp_scratch\n stx z:__dp_scratch+2\n plx\n plx\n lda z:__dp_scratch\n ldx z:__dp_scratch+2\n rts\n.export _fixture_dec_format_raw_call,_fixture_decimal_call\n.import _decimal__dec_format_raw_spec,___ieee_decimal\n_fixture_dec_format_raw_call:\n pea $0006\n pea $0067\n lda 9,s\n pha\n lda 9,s\n pha\n lda #$5AA5\n jsr .loword(_decimal__dec_format_raw_spec)\n plx\n plx\n plx\n plx\n rts\n_fixture_decimal_call:\n pha\n lda 7,s\n pha\n lda 7,s\n pha\n lda 5,s\n ldx #$A55A\n jsr .loword(___ieee_decimal)\n plx\n plx\n plx\n rts\n\n.segment "RODATA"\n_fixture_rom: .res 2048,0\n')
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',hook.with_suffix('.o'),hook])
    if any(name in FUNCTIONS for name in ('hexparse','ieee-parse')):
        c.run(['cmd','/c',ROOT/'tools/msvc.cmd','/nologo','/LD','/O2',ROOT/'tests/decimal_native_fixture.c',
               '/Fe'+str(OUT/'native.dll'),'/Fo'+str(OUT/'native.obj'),'/link','/IMPLIB:'+str(OUT/'native.lib')],timeout=120)
    reports={}
    for mode in ('reference','assembly'):
        c.OUT=OUT/mode;c.OUT.mkdir(parents=True, exist_ok=True)
        implementation=(BEFORE or source.with_suffix('.o')) if mode=='reference' else ROOT/'build/decimal.o'
        c.compile_case('driver',(ROOT/'tests/decimal_assembly_fixture.c').read_text(),extra_objects=[hook.with_suffix('.o'),*[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables','io')],implementation])
    (OUT/'setup.json').write_text(json.dumps(dict(run_id=uuid.uuid4().hex,fixtures=fixture_hashes())))

def fixture_hashes():
    return {str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in OUT.rglob('*') if p.suffix in ('.sfc','.labels','.dll')}

def collect():
    reports={}
    coverage={}
    setup=json.loads((OUT/'setup.json').read_text())
    assert setup['fixtures']==fixture_hashes(), 'fixtures changed after setup'
    for item in worker_plan():
        home=worker_home(**item)
        report=json.loads((home/'report.json').read_text())
        assert report['run_id']==setup['run_id'], 'stale decimal worker'
        assert report['worker']==item, 'wrong decimal worker'
        assert report['result_sha256']==hashlib.sha256((home/'result.json').read_bytes()).hexdigest()
        result=json.loads((home/'result.json').read_text())
        key='/'.join((item['mode'],item['region'],item['name']))
        if item['name']=='hexval':
            count=sum(row['cases'] for row in result.values())
            expected=min(BATCH_SIZES['hexval'],65536-item['batch']*BATCH_SIZES['hexval'])
        else:
            sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(OUT/item['mode']/'driver.labels').read_text(),re.M)}
            cases=(numeric.make_cases(item['name'],sy) if item['name'] in BATCH_SIZES else case_vectors(item['name'],sy))
            size=BATCH_SIZES.get(item['name'],len(cases));start=item['batch']*size
            expected_cases=cases[start:start+size];count=len(result);expected=len(expected_cases)
            assert [r['case'] for r in result]==list(range(1,expected+1)), 'batch case order'
            assert [r['tag'] for r in result]==[v['tag'] for v in expected_cases], 'batch vector mismatch'
        assert count==expected, 'batch case count'
        coverage[key]=coverage.get(key,0)+count
        report['cases']=count
        reports['/'.join(map(str,item.values()))]=report
    for name in ('hexparse','ieee-parse'):
        if name not in FUNCTIONS:continue
        for batch in range(batch_count(name)):
            baseline=json.loads((worker_home('reference','ntsc',name,batch)/'semantics.json').read_text())
            for mode in ('reference','assembly'):
                for region in ('ntsc','pal'):
                    assert json.loads((worker_home(mode,region,name,batch)/'semantics.json').read_text())==baseline, 'endptr/errno/reference mismatch'
    reports['coverage']=coverage
    reports['sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (ROOT/'build/zicc.exe',ROOT/'build/decimal.o',ROOT/'runtime/ieee32/decimal.c',ROOT/'tests/decimal_assembly_fixture.c')}
    reports['sources']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [ROOT/'tests/decimal_numeric_fixture.py',ROOT/'tests/decimal_native_fixture.c',*[ROOT/'runtime/ieee32'/(name+'.s') for name in ('match','render','rounded',*FUNCTIONS)]]}
    if BEFORE:reports['before_library']=dict(path=str(BEFORE),sha256=hashlib.sha256(BEFORE.read_bytes()).hexdigest())
    reports['fixtures']={mode:{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [OUT/mode/('driver'+suffix) for suffix in ('.c','.s','.sfc')]} for mode in ('reference','assembly')}
    (OUT/'results.json').write_text(json.dumps(reports,indent=2)+'\n')

def batch_count(name):
    if name=='hexval':count=65536
    elif name in ('ieee-decimal','ieee-decimal-compare','hexparse','ieee-parse'):
        count=len(numeric.make_cases(name,{'fixture_rom':0x808000}))
    else:return 1
    size=BATCH_SIZES.get(name,count)
    return (count+size-1)//size

def worker_plan():
    return [dict(mode=mode,region=region,name=name,batch=batch)
            for mode in ('reference','assembly') for region in ('ntsc','pal')
            for name in FUNCTIONS for batch in range(batch_count(name))]

def worker_home(mode,region,name,batch=None):
    home=OUT/mode/region/name
    return home/('batch-%03d'%batch) if batch is not None else home

def run_worker(mode,region,name,batch=None):
    global BATCH
    BATCH=batch
    setup=json.loads((OUT/'setup.json').read_text())
    assert setup['fixtures']==fixture_hashes(), 'fixtures changed after setup'
    worker(mode,region,name)
    home=worker_home(mode,region,name,batch)
    (home/'report.json').write_text(json.dumps(dict(run_id=setup['run_id'],
        worker=dict(mode=mode,region=region,name=name,batch=batch),
        result_sha256=hashlib.sha256((home/'result.json').read_bytes()).hexdigest())))


def worker(mode,region,name):
    if name in ('ieee-decimal','ieee-decimal-compare','hexparse','ieee-parse'):return numeric.run_worker(ROOT,OUT,mode,region,name,BATCH,BATCH_SIZES.get(name))
    if name!='hexval':return worker_cases(mode,region,name)
    directory=OUT/mode;home=worker_home(mode,region,name,BATCH);home.mkdir(parents=True,exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(directory/'driver.labels').read_text(),re.M)}
    assert name=='hexval'
    first=0 if BATCH is None else BATCH*BATCH_SIZES[name]
    last=65535 if BATCH is None else min(first+BATCH_SIZES[name],65536)-1
    script=f'''
local function assert(ok,message)if not ok then emu.breakExecution();error(message or 'assertion')end end
local index={first-1};local record=nil;local registered=false;local calls,returns=0,0
local totals={{digit={{0,0,0}},upper={{0,0,0}},lower={{0,0,0}},other={{0,0,0}}}}
local function word(a)return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false)end
local function put(a,v)emu.write16(a&0x1ffff,v,emu.memType.snesWorkRam)end
local function expected(n)
 if n>=48 and n<=57 then return n-48,'digit' end
 if n>=65 and n<=70 then return n-55,'upper' end
 if n>=97 and n<=102 then return n-87,'lower' end
 return 65535,'other'
end
emu.addMemoryCallback(function()
 assert(not record,'unfinished call');index=index+1;assert(index<={last},'case overflow')
 put({sy['operation']},0);put({sy['input_word']},index)
end,emu.callbackType.exec,{sy['fixture_before']},{sy['fixture_before']})
emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.x']==index,'actual input')
 record=s;calls=calls+1
 if not registered then registered=true;local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
  emu.addMemoryCallback(function()
   local t=emu.getState();local s=record;assert(s,'return without call');local value,kind=expected(index)
   assert(t['cpu.a']==value and t['cpu.sp']==s['cpu.sp']+2,'value/stack '..index)
   for _,k in ipairs({{'y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'ABI '..k)end
   assert((t['cpu.ps']&0x3c)==(s['cpu.ps']&0x3c),'CPU modes')
   local row=totals[kind];row[1]=row[1]+1;row[2]=row[2]+t.masterClock-s.masterClock;row[3]=row[3]+t['cpu.cycleCount']-s['cpu.cycleCount']
   returns=returns+1;record=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{sy['decimal__hexval']},{sy['decimal__hexval']})
emu.addMemoryCallback(function()
 assert(word({sy['result_word']})==expected(index),'stored result')
 if index=={last} then put({sy['running']},0)end
end,emu.callbackType.exec,{sy['fixture_after']},{sy['fixture_after']})
emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0 and s['cpu.sp']==1279,'driver result/stack')
 assert(index=={last} and calls=={last-first+1} and returns==calls and not record,'coverage')
 for k,v in pairs(totals)do emu.log('TOTAL '..k..' '..v[1]..' '..v[2]..' '..v[3])end
 emu.log('PASS {mode} {region} hexval cases='..calls);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    (home/'check.lua').write_text(script);core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1;config.DisableFrameSkipping=True
        config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(directory/'driver.sfc',home/'check.lua',script);core.start();log=core.wait_for('PASS',210)
        totals={k:dict(cases=int(n),master_clocks=int(m),cpu_cycles=int(cpu)) for k,n,m,cpu in re.findall(r'TOTAL (\w+) (\d+) (\d+) (\d+)',log)}
        assert sum(x['cases'] for x in totals.values())==last-first+1
        (home/'result.json').write_text(json.dumps(totals,indent=2)+'\n')
        print(next(x for x in log.splitlines() if x.startswith('PASS ')))
    finally:core.close_with_log(home/'check.log')

def lua_bytes(data):return '"'+''.join('\\'+format(x,'03d') for x in data)+'"'

def case_vectors(name,sy):
    cases=[]
    if name=='dec-format-spec':
        bits=[0,0x80000000,1,0x800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,0x7fc00000,0x3fa00000,0x40200000,0x41f00000,0x60ad78ec]
        for value in bits:
            for spec in 'fFeEgG':
                for precision in (0,1,6,8,32):
                    if value&0x7f800000==0x7f800000:text=('-' if value>>31 else '')+('nan' if value&0x7fffff else 'inf')
                    else:text=format(struct.unpack('<f',struct.pack('<I',value))[0],'.'+str(precision)+spec)
                    p=sy['decimal__dec_output']&0x1ffff
                    cases.append(dict(tag=hex(value)+'/'+spec+'/'+str(precision),op=9,word=ord(spec),bits=value,flag=precision,p=p,source=0x7f4000,data=b'',output=text.encode()+b'\0',result=sy['decimal__dec_output'],stack=[value&65535,value>>16,precision],reg_a=ord(spec),guard_before=False))
        return cases
    if name in ('dec-format','dec-format-raw'):
        bits=[0,0x80000000,1,0x80000001,0x7fffff,0x800000,0x7f7fffff,0xff7fffff,0x3f800000,0x4b800000,0x7f800000,0xff800000,0x7fc00000,0xffc00000]
        for value in (0.0001,0.00001,999999,1000000,9.999995,9.999985,1.000005,0.9999995):bits.append(struct.unpack('<I',struct.pack('<f',value))[0])
        rng=random.Random(65816);bits += [rng.getrandbits(32) for _ in range(256)]
        for value in bits:
            if value&0x7f800000==0x7f800000:text=('-' if value>>31 else '')+('nan' if value&0x7fffff else 'inf')
            else:text=format(struct.unpack('<f',struct.pack('<I',value))[0],'.6g')
            p=(sy['decimal__dec_output']&0x1ffff) if name=='dec-format' else 0x4000
            cases.append(dict(tag=hex(value),op=3 if name=='dec-format' else 4,word=0,bits=value,flag=0,p=p,source=0x7f4000,data=b'',output=text.encode()+b'\0',
                result=sy['decimal__dec_output'] if name=='dec-format' else len(text),stack=[value&65535,value>>16]+([103,6] if name=='dec-format-raw' else []),
                reg_a=0x5aa5,reg_x=0xa55a if name=='dec-format' else p,guard_before=name!='dec-format'))
        return cases
    if name=='exponent':
        values=list(range(-200,201))+[-32767,-10000,-9999,-1000,-999,-100,-99,-10,-9,-1,0,1,9,10,99,100,999,1000,9999,10000,32767]
        rng=random.Random(65816);values += [rng.randrange(-32767,32768) for _ in range(256)]
        for e in values:
            for upper in (0,1,65535):
                text=(('E' if upper else 'e')+('-' if e<0 else '+')+str(abs(e)).zfill(2)).encode()
                cases.append(dict(tag=str(e)+'/'+str(upper),op=2,word=e&65535,bits=0,flag=upper,p=0x4000,source=0x7f4000,data=b'',output=text,result=0x4000+len(text),stack=[upper],reg_a=e&65535))
        return cases
    assert name=='dec-copy'
    def add(data,location=0,tag='copy'):
        p=0x4000;src=(0x7f4000,0x7effff,sy['fixture_rom'],0xfffffe,0x7e4000,0x7e4001)[location]
        output=data.split(b'\0')[0]+b'\0'
        cases.append(dict(tag=tag,op=1,word=0,bits=0,flag=0,p=p,source=src,data=data,
                          output=output,result=None,stack=[src&65535,src>>16]))
    for b in range(256):add(bytes((b,0)),tag='byte-'+str(b))
    for n in (0,1,2,3,15,16,17,127,128,255,256,511,512,40000):add(b'A'*n+b'\0',tag='length-'+str(n))
    for location in (0,1,2,4,5):
        for data in (b'\0',b'inf\0',b'nan\0',b'abcXYZ!\0'):add(data,location,tag='location-'+str(location))
    add(b'AZ\0',3,tag='24bit-wrap')
    return cases

def worker_cases(mode,region,name):
    directory=OUT/mode;home=worker_home(mode,region,name,BATCH);home.mkdir(parents=True,exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(directory/'driver.labels').read_text(),re.M)}
    cases=case_vectors(name,sy);function={'dec-copy':'decimal__dec_copy','exponent':'decimal__exponent','dec-format':'dec_format','dec-format-raw':'decimal__dec_format_raw_spec','dec-format-spec':'dec_format_spec'}[name]
    vectors=[]
    for v in cases:
        vectors.append('{op='+str(v['op'])+',word='+str(v['word'])+',bits='+str(v['bits'])+',flag='+str(v['flag'])+
            ',p='+str(v['p'])+',source='+str(v['source'])+',data='+lua_bytes(v['data'])+',output='+lua_bytes(v['output'])+
            ',stack={'+','.join(map(str,v['stack']))+'}'+(',reg_a='+str(v['reg_a']) if v.get('reg_a') is not None else '')+
            (',reg_x='+str(v.get('reg_x',v['p'])) if name!='dec-format-spec' else '')+',guard_before='+('true' if v.get('guard_before',True) else 'false')+
            (',result='+str(v['result']) if v['result'] is not None else '')+'}')
    script='local function assert(ok,message)if not ok then emu.breakExecution();error(message or "assertion")end end\nlocal vectors={'+','.join(vectors)+'}\n'
    script+=f'''
local index=0;local record=nil;local registered=false;local calls,returns=0,0;local timings={{}}
local function word(a)return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false)end
local function put(a,v)emu.write16(a&0x1ffff,v&65535,emu.memType.snesWorkRam)end
local function seed(p,data)
 for i=1,#data do local a=(p+i-1)&0xffffff
  if a<0x2000 or a>=0x7e0000 and a<=0x7fffff then emu.write(a&0x1ffff,string.byte(data,i),emu.memType.snesWorkRam)
  else emu.write(a&0x7fff,string.byte(data,i),emu.memType.snesPrgRom)end
 end
end
emu.addMemoryCallback(function()
 assert(not record,'unfinished call');index=index+1;local v=vectors[index];assert(v,'case overflow')
 put({sy['operation']},v.op);put({sy['input_word']},v.word);put({sy['flag']},v.flag)
 put({sy['input_long']},v.bits&65535);put({sy['input_long']+2},v.bits>>16);put({sy['output']},v.p)
 put({sy['source']},v.source&65535);put({sy['source']+2},v.source>>16)
 if v.guard_before then emu.write(v.p-1,165,emu.memType.snesWorkRam)end
 emu.write(v.p+#v.output,165,emu.memType.snesWorkRam)
 seed(v.source,v.data)
end,emu.callbackType.exec,{sy['fixture_before']},{sy['fixture_before']})
emu.addMemoryCallback(function()
 local s=emu.getState();local v=vectors[index];if v.reg_x~=nil then assert(s['cpu.x']==v.reg_x,'actual register X argument')end
 if v.reg_a~=nil then assert(s['cpu.a']==v.reg_a,'actual register argument')end
 for i,x in ipairs(v.stack)do assert(word(s['cpu.sp']+1+2*i)==x,'actual argument '..i)end
 record={{state=s,before=emu.read(v.p-1,emu.memType.snesWorkRam,false),after=emu.read(v.p+#v.output,emu.memType.snesWorkRam,false)}};calls=calls+1
 if not registered then registered=true;local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
  emu.addMemoryCallback(function()
   local t=emu.getState();local s=record.state;local v=vectors[index]
   assert(t['cpu.sp']==s['cpu.sp']+2,'stack')
   if v.result~=nil then assert(t['cpu.a']==(v.result&65535),'return pointer/count');if v.op==3 or v.op==9 then assert((t['cpu.a']|(t['cpu.x']<<16))==v.result,'far result bank')end end
   for _,k in ipairs({{'y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'ABI '..k)end
   assert((t['cpu.ps']&0x3c)==(s['cpu.ps']&0x3c),'CPU modes')
   for i=1,#v.output do assert(emu.read(v.p+i-1,emu.memType.snesWorkRam,false)==string.byte(v.output,i),'output case '..index)end
   assert((not v.guard_before or emu.read(v.p-1,emu.memType.snesWorkRam,false)==record.before) and emu.read(v.p+#v.output,emu.memType.snesWorkRam,false)==record.after,'output bounds')
   timings[#timings+1]=index..':'..(t.masterClock-s.masterClock)..':'..(t['cpu.cycleCount']-s['cpu.cycleCount'])
   returns=returns+1;record=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{sy[function]},{sy[function]})
emu.addMemoryCallback(function()
 local v=vectors[index];if v.result~=nil then assert(word({sy['result_word']})==(v.result&65535),'stored return');if v.op==3 or v.op==9 then assert((word({sy['result_long']})|(word({sy['result_long']+2})<<16))==v.result,'stored far result')end end
 if index==#vectors then put({sy['running']},0)end
end,emu.callbackType.exec,{sy['fixture_after']},{sy['fixture_after']})
emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0 and s['cpu.sp']==1279,'driver result/stack')
 assert(calls==#vectors and returns==calls and not record,'coverage')
 emu.log('TIMINGS '..table.concat(timings,','));emu.log('PASS {mode} {region} {name} cases='..calls);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    (home/'check.lua').write_text(script);core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1;config.DisableFrameSkipping=True
        config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(directory/'driver.sfc',home/'check.lua',script);core.start();log=core.wait_for('PASS',270)
        rows=[dict(case=int(i),tag=cases[int(i)-1]['tag'],master_clocks=int(m),cpu_cycles=int(cpu)) for i,m,cpu in re.findall(r'(\d+):(\d+):(\d+)',log)]
        assert len(rows)==len(cases);(home/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(next(x for x in log.splitlines() if x.startswith('PASS ')))
    finally:core.close_with_log(home/'check.log')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('reference','assembly'));p.add_argument('--region',choices=('ntsc','pal'));p.add_argument('--function',choices=FUNCTIONS)
    p.add_argument('--output',type=Path);p.add_argument('--before',type=Path);p.add_argument('--batch',type=int)
    for flag in ('setup','list-workers','collect'):p.add_argument('--'+flag,action='store_true')
    a=p.parse_args()
    if a.output:OUT=a.output.resolve()
    if a.before:BEFORE=a.before.resolve()
    if a.function:FUNCTIONS=(a.function,)
    if a.list_workers:print(json.dumps(worker_plan()))
    elif a.setup:build()
    elif a.collect:collect()
    elif a.mode:run_worker(a.mode,a.region,a.function,a.batch)
    else:
        build()
        for item in worker_plan():
            result=c.run([sys.executable,__file__,'--output',OUT,'--mode',item['mode'],'--region',item['region'],
                   '--function',item['name'],'--batch',str(item['batch'])],timeout=1500)
            print(result.stdout.strip(),flush=True)
        collect()
