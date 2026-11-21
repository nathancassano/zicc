"""Exact state models and differential parsing fixtures for assembly decimal ports."""
import ctypes,hashlib,json,random,re,struct
from pathlib import Path
from mesen_core import Core,SnesConfig

def decimal_state(m,e):
    if not m:return bytes((0,)),1,0
    if not m&1:
        while e<=-8 and not m&255:m>>=8;e+=8
        while e<0 and not m&1:m>>=1;e+=1
    scale=max(-e,0);value=m*5**(-e) if e<0 else m<<e
    digits=bytes(int(c) for c in str(value)[::-1]);assert len(digits)<=200
    return digits,len(digits),scale

def comparison(text,raw,n,scale,exponent):
    q=n-scale;assert -32768<=q<=32767
    if exponent!=q:return -1 if exponent<q else 1
    chars=text.replace(b'.',b'')
    for i in range(max(len(chars),max(n,0))):
        a=chars[i]-48 if i<len(chars) else 0;b=raw[n-1-i] if i<n else 0
        if a!=b:return -1 if a<b else 1
    return 0

def make_cases(name,sy):
    cases=[]
    if name=='ieee-decimal':
        inputs=[]
        for m in (0,1,2,3,9,10,15,16,255,256,257,65535,65536,65537,0x7fffff,0x800000,0xffffff,0x1000000,0x7fffffff,0x80000000,0xffffffff):
            for e in (-150,-149,-8,-1,0,1,8,104):inputs.append((m,e))
        for m in (1,3,0xffffffff):
            for e in (-272,-250,600,630):
                try:decimal_state(m,e)
                except AssertionError:continue
                inputs.append((m,e))
        inputs += [(0,-32768),(0,32767)]
        rng=random.Random(65816);inputs += [(rng.getrandbits(32),rng.randrange(-150,105)) for _ in range(64)]
        for m,e in inputs:
            raw,n,scale=decimal_state(m,e)
            cases.append(dict(tag=hex(m)+'/'+str(e),op=5,bits=m,word=e&65535,flag=0,source=0x7f4000,data=b'',limit=0x7f4000,endptr=0,
                raw=bytes(),n=7,scale=9,expected_raw=raw+bytes([165])*(200-n),expected_n=n,expected_scale=scale,reg_a=e&65535,reg_x=0xa55a,stack=[m&65535,m>>16],ret16=None))
        return cases
    if name=='ieee-decimal-compare':
        inputs=[]
        for raw in (bytes((0,)),bytes((1,)),bytes((9,)),bytes((0,1)),bytes((5,2)),bytes((9,9,9)),bytes([0])*200,bytes([9])*200):
            n=len(raw)
            for scale in (0,1,149):
                q=n-scale
                for exponent in (q-1,q,q+1,-2147483648,2147483647):
                    for text in (b'',b'0',b'1.23',bytes(48+x for x in raw[::-1]),b'9999',b'...0...'):
                        inputs.append((text,raw,n,scale,exponent))
        for b in range(256):inputs.append((bytes((b,)),bytes((5,)),1,0,1))
        inputs += [(b'000',b'',0,0,0),(b'000',b'',-1,0,-1)]
        for i,(text,raw,n,scale,exponent) in enumerate(inputs):
            source=(0x7f4000,0x7effff,sy['fixture_rom'],0x7f0000)[i%4]
            expected=comparison(text,raw,n,scale,exponent)&65535;limit=(source+len(text))&0xffffff
            cases.append(dict(tag=str(i),op=6,bits=exponent&0xffffffff,word=0,flag=0,source=source,data=text+b'\0',limit=limit,endptr=0,
                raw=raw,n=n,scale=scale,expected_raw=raw+bytes([165])*(200-len(raw)),expected_n=n&65535,expected_scale=scale&65535,
                reg_a=None,reg_x=None,stack=[source&65535,source>>16,limit&65535,limit>>16,exponent&65535,(exponent>>16)&65535],ret16=expected))
        return cases
    if name in ('hexparse','ieee-parse'):
        if name=='hexparse':
            texts=['0x','0x.','0x.p2','0xg','0X1','0x0','0x0000','0x1.','0x.8','0x1p0','0x1p+','0x1p-','0x1pZ','0x1.8p2tail',
                '0xabcdefp-20','0x12345678','0x123456789','0x80000000p-181','0x80000001p-181','0x80000000.1p-181','0x40000000p-181',
                '0x1p-149','0x1p-150','0x1.000001p-150','0x7fffffp-149','0x800000p-149','0xffffffp104','0x1.fffffep127',
                '0x1.ffffffp127','0x1.fffffeffffffffp127','0x1p128','0x1p-1000000','0x1p1000000','0x0p1000000',
                '0x00000000000000.000000001p+0','0x1..0','0x1P-+2','0x00z','0x1_2']
        else:
            texts=['',' ','\t\n\r','+','-','.','+.','-.','e1','NaN','-NaN','+NAN(foo)','nan()','nan(ABC_123)','nan(unclosed','nan(bad!)','NaN_abc',
                'Inf','-INFINITY','+infinitytail','infinite','0','-0','+000','00012','1','16777215','16777216','16777217','99999999','100000000',
                '12.0','0.125','-0.125','0x1.8p2','0x','-0xg','1e','1e+','1e-','1e+2','0e1000000','-0e-1000000',
                '1e1000000','-1e1000000','1e-1000000','1e40','1e39','1e-46','1e-47','1e-48',
                '3.4028234663852886e38','3.4028235677973366e38','1.1754943508222875e-38','1.1754942106924411e-38',
                '1.401298464324817e-45','7.006492321624085e-46','7.006492321624086e-46',
                '7.00649232162408535461864791644958065640130970938257885878534141944895541342930300743319094181060791015625e-46',
                '1.000000059604644775390625','1.000000178813934326171875','1.0000000596046447753906250000001',
                '1.'+'0'*200+'1','0.'+'0'*150+'1','00.000000000']
            rng=random.Random(65816)
            for _ in range(32):
                bits=rng.getrandbits(32)
                if bits&0x7f800000!=0x7f800000:texts.append(format(struct.unpack('<f',struct.pack('<I',bits))[0],'.9g'))
        rng=random.Random(816)
        if name=='hexparse':
            # Exact float encodings, random long significands, rounding boundaries,
            # invalid exponent rollback, and high-byte terminators
            for _ in range(160):
                bits=rng.getrandbits(32)
                if bits&0x7f800000!=0x7f800000:
                    value=struct.unpack('<f',struct.pack('<I',bits&0x7fffffff))[0]
                    texts.append(value.hex())
            for _ in range(80):
                digits=''.join(rng.choice('0123456789aAbBcCdDeEfF') for _ in range(rng.randrange(1,65)))
                point=rng.randrange(len(digits)+1)
                texts.append('0x'+digits[:point]+'.'+digits[point:]+'p'+str(rng.randrange(-300,300))+rng.choice(['','tail','p+']))
            texts += ['0x1'+chr(i) for i in (9,32,58,64,71,96,103,127,128,255)]
        else:
            for _ in range(80):
                digits=''.join(rng.choice('0123456789') for _ in range(rng.randrange(1,65)))
                point=rng.randrange(len(digits)+1)
                texts.append(rng.choice(['','-','+'])+digits[:point]+'.'+digits[point:]+'e'+str(rng.randrange(-100,100))+rng.choice(['','tail','e+']))
            # Exercise the low and high mantissa edges in every finite binary binade
            for exponent in range(255):
                for mantissa in (1,0x7fffff):
                    bits=(exponent<<23)|mantissa|((exponent&1)<<31)
                    texts.append(format(struct.unpack('<f',struct.pack('<I',bits))[0],'.9g'))
            texts += ['1'+chr(i) for i in (9,32,58,64,71,96,103,127,128,255)]
        for i,text in enumerate(texts):
            for j,flag in enumerate((0,1,65535) if name=='hexparse' else (0,)):
                for null_end in (False,True):
                    source=(0x7f4000,0x7efff8,sy['fixture_rom'],0x7f0000)[(i+j)%4];endptr=0 if null_end else 0x3500
                    cases.append(dict(tag=repr(text)+'/'+str(flag)+'/'+str(null_end),op=7 if name=='hexparse' else 8,bits=0,word=0,flag=flag,
                        source=source,data=text.encode('latin1')+b'\0',limit=source,endptr=endptr,raw=b'',n=7,scale=9,
                        expected_raw=bytes([165])*200 if name=='hexparse' else None,expected_n=7 if name=='hexparse' else None,expected_scale=9 if name=='hexparse' else None,
                        reg_a=endptr,reg_x=None,stack=[source&65535,source>>16]+([flag] if name=='hexparse' else []),ret16=None))
        return cases
    raise AssertionError(name)

def lua_bytes(data):return '"'+''.join('\\'+format(x,'03d') for x in data)+'"'

def run_worker(ROOT,OUT,mode,region,name,batch=None,batch_size=None):
    directory=OUT/mode;home=directory/region/name;
    if batch is not None:home=home/("batch-%03d"%batch)
    home.mkdir(parents=True,exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(directory/'driver.labels').read_text(),re.M)}
    cases=make_cases(name,sy)
    if batch is not None:
        cases=cases[batch*batch_size:(batch+1)*batch_size]
        assert cases, "empty batch"
    symbol={'ieee-decimal':'__ieee_decimal','ieee-decimal-compare':'__ieee_decimal_compare','hexparse':'decimal__hexparse','ieee-parse':'__ieee_parse'}[name]
    native=None
    if name in ('hexparse','ieee-parse'):
        native=ctypes.CDLL(str(OUT/'native.dll'));native.native_bits.argtypes=[ctypes.c_char_p];native.native_bits.restype=ctypes.c_uint32
    vectors=[]
    for v in cases:
        fields={k:v[k] for k in ('op','bits','word','flag','source','limit','endptr')}
        fields.update(n=v['n']&65535,scale=v['scale']&65535)
        if v['expected_n'] is not None:fields.update(expected_n=v['expected_n'],expected_scale=v['expected_scale'])
        if native:
            data=(b'-' if name=='hexparse' and v['flag'] else b'')+v['data'];value=native.native_bits(data)
            if value&0x7f800000==0x7f800000 and value&0x7fffff:value=0x7fc00000
            fields['ret32']=value
        for k in ('reg_a','reg_x','ret16'):
            if v.get(k) is not None:fields[k]=v[k]
        vectors.append('{'+','.join(k+'='+str(x) for k,x in fields.items())+',data='+lua_bytes(v['data'])+',raw='+lua_bytes(v['raw'])+
            ',expected_raw='+lua_bytes(v['expected_raw'] or b'')+',stack={'+','.join(map(str,v['stack']))+'}}')
    base=sy['decimal__dec_digits']&0x1ffff;naddr=sy['decimal__dec_n'];scaleaddr=sy['decimal__dec_scale'];out=sy['decimal__dec_output']&0x1ffff
    script='local function assert(ok,message)if not ok then emu.breakExecution();error(message or "assertion")end end\nlocal vectors={'+','.join(vectors)+'}\n'
    script+=f'''
local index=0;local record=nil;local registered=false;local calls,returns=0,0;local timings={{}};local snapshots={{}}
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
 put({sy['input_long']},v.bits&65535);put({sy['input_long']+2},v.bits>>16);put({sy['output']},0x4000)
 put({sy['source']},v.source&65535);put({sy['source']+2},v.source>>16)
 put({sy['limit']},v.limit&65535);put({sy['limit']+2},v.limit>>16);put({sy['endptr']},v.endptr)
 put(0x3500,0xA5A5);put(0x3502,0xA5A5)
 put({sy['errno']},0x1234)
 for i=0,199 do emu.write({base}+i,165,emu.memType.snesWorkRam)end
 seed(0x7e0000|{base},v.raw);put({naddr},v.n);put({scaleaddr},v.scale)
 for i=0,47 do emu.write({out}+i,204,emu.memType.snesWorkRam)end
 seed(v.source,v.data)
end,emu.callbackType.exec,{sy['fixture_before']},{sy['fixture_before']})
emu.addMemoryCallback(function()
 local s=emu.getState();local v=vectors[index]
 if v.reg_a~=nil then assert(s['cpu.a']==v.reg_a,'A argument case '..index)end
 if v.reg_x~=nil then assert(s['cpu.x']==v.reg_x,'X argument case '..index)end
 for i,x in ipairs(v.stack)do assert(word(s['cpu.sp']+1+2*i)==x,'stack argument '..i)end
 record=s;calls=calls+1
 if not registered then registered=true;local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
  emu.addMemoryCallback(function()
   local t=emu.getState();local s=record;local v=vectors[index];assert(s,'return without call')
   assert(t['cpu.sp']==s['cpu.sp']+2,'stack')
   for _,k in ipairs({{'y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'ABI '..k)end
   assert((t['cpu.ps']&0x3c)==(s['cpu.ps']&0x3c),'CPU modes')
   if v.ret16~=nil then assert(t['cpu.a']==v.ret16,'return case '..index)end
   if v.ret32~=nil then assert((t['cpu.a']|(t['cpu.x']<<16))==v.ret32,'binary32 return case '..index..' got '..string.format('%08X',t['cpu.a']|(t['cpu.x']<<16))..' expected '..string.format('%08X',v.ret32))end
   if v.expected_n~=nil then assert(word({naddr})==v.expected_n and word({scaleaddr})==v.expected_scale,'state counts case '..index)end
   for i=1,#v.expected_raw do assert(emu.read({base}+i-1,emu.memType.snesWorkRam,false)==string.byte(v.expected_raw,i),'raw state case '..index..' byte '..i)end
   for i=0,47 do assert(emu.read({out}+i,emu.memType.snesWorkRam,false)==204,'output buffer clobbered')end
   if v.ret32==nil then assert(word({sy['errno']})==0x1234,'errno clobbered')end
   timings[#timings+1]=index..':'..((t.masterClock-s.masterClock)&0xffffffff)..':'..((t['cpu.cycleCount']-s['cpu.cycleCount'])&0xffffffff)
   returns=returns+1;record=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{sy[symbol]},{sy[symbol]})
emu.addMemoryCallback(function()
 local v=vectors[index];if v.ret16~=nil then assert(word({sy['result_word']})==v.ret16,'stored result')end
 if v.ret32~=nil then
  local result=word({sy['result_long']})|(word({sy['result_long']+2})<<16);assert(result==v.ret32,'stored binary32')
  local endpoint=word(0x3500)|(word(0x3502)<<16);local offset=-1
  if v.endptr~=0 then assert((endpoint>>24)==0,'far padding');offset=(endpoint-v.source)&0xffffff
  else assert(endpoint==0xA5A5A5A5,'NULL endptr wrote storage')end
  snapshots[#snapshots+1]=index..':'..result..':'..offset..':'..word({sy['errno']})
 end
 if index==#vectors then put({sy['running']},0)end
end,emu.callbackType.exec,{sy['fixture_after']},{sy['fixture_after']})
emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0 and s['cpu.sp']==1279,'driver result/stack')
 assert(calls==#vectors and returns==calls and not record,'coverage')
 emu.log('TIMINGS '..table.concat(timings,','));emu.log('SNAP '..table.concat(snapshots,','));emu.log('PASS {mode} {region} {name} cases='..calls);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    (home/'check.lua').write_text(script);core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1;config.DisableFrameSkipping=True
        config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(directory/'driver.sfc',home/'check.lua',script);core.start();log=core.wait_for('PASS',1200)
        rows=[dict(case=int(i),tag=cases[int(i)-1]['tag'],master_clocks=int(m),cpu_cycles=int(cpu)) for i,m,cpu in re.findall(r'(\d+):(\d+):(\d+)',log.split('TIMINGS ',1)[1].split('SNAP ',1)[0])]
        assert len(rows)==len(cases);(home/'result.json').write_text(json.dumps(rows,indent=2)+'\n')
        if native:
            snapshots=[tuple(map(int,x)) for x in re.findall(r'(\d+):(\d+):(-?\d+):(\d+)',log.split('SNAP ',1)[1].split('PASS ',1)[0])]
            assert len(snapshots)==len(cases)
            (home/'semantics.json').write_text(json.dumps(snapshots,indent=2)+'\n')
        print(next(x for x in log.splitlines() if x.startswith('PASS ')))
    finally:core.close_with_log(home/'check.log')
