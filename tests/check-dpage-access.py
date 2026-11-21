"""Compare runs with and without direct-page pointers. Check volatile accesses and saved values."""
import hashlib, importlib.util, json, re, subprocess, sys
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'dpage-access-check'
DECLS='''typedef unsigned char U8;
typedef unsigned U16;
typedef unsigned long U32;
struct Row {U16 a;U32 b;U8 c;};
extern __dpage U8 *nb;
extern __dpage volatile U8 *vnb;
extern __dpage signed char *nsb;
extern __dpage U16 *nw;
extern __dpage U32 *nl;
extern __dpage U8 * __far fb;
extern __dpage signed char * __far fsb;
extern __dpage float * __far ffloat;
extern __dpage U16 * __far fw;
extern __dpage U32 * __far fl;
extern __dpage volatile U8 * __far vfb;
extern __dpage volatile U32 * __far vfl;
extern __dpage U8 * __far volatile vptr;
extern __dpage struct Row * __far row;
extern __dpage U8 dp_array[8];
extern U8 * __far plain,* __far other;
extern U8 * __far *alias;
U16 change_pointer(void);
U16 change_index(void);
'''
# Function-local assertions avoid mistaking another function's scratch or
# ordinary loads/stores of the pointer object for an indirect target transfer
FUNCTIONS=[
 ('load_nb','U16','void','return *nb;','(_nb)'),
 ('load_s','int','void','return *nsb;','(_nsb)'),
 ('load_fs','int','void','return *fsb;','[_fsb]'),
 ('load_float','float','void','return *ffloat;','[_ffloat],y'),
 ('load_nw','U16','void','return *nw;','(_nw)'),
 ('add_nw','U16','U16 x','return x+*nw;','(_nw)'),
 ('sub_nw','U16','U16 x','return x-*nw;','(_nw)'),
 ('xor_nw','U16','U16 x','return x^*nw;','(_nw)'),
 ('load_nl','U32','void','return *nl;',None),
 ('load_fb','U16','void','return *fb;','[_fb]'),
 ('load_fw','U16','void','return *fw;','[_fw]'),
 ('load_fl','U32','void','return *fl;','[_fl],y'),
 ('load_vb','U16','void','return *vfb;','[_vfb]'),
 ('load_vnear','U16','void','return *vnb;','(_vnb)'),
 ('load_vl','U32','void','return *vfl;','[_vfl],y'),
 ('load_vptr','U16','void','return *vptr;',None),
 ('load_plain','U16','void','return *plain;',None),
 ('array_dp','U16','U8 i','return dp_array[i];',None),
 ('array_plain','U16','void','return *dp_array;',None),
 ('auto_ptr','U16','U8 * __far p','return *p;',None),
 ('load_cast','U16','void','return *(U8 * __far)nb;',None),
 ('index_byte','U16','U16 i','return fb[i];','[_fb],y'),
 ('index_word','U16','U8 i','return fw[i];','[_fw],y'),
 ('index_long','U32','U8 i','return fl[i];','[_fl],y'),
 ('index_mask','U16','int i','return fw[i&31];','[_fw],y'),
 ('index_signed','U16','int i','return fb[i];',None),
 ('index_overflow','U16','U16 i','return fw[i];',None),
 ('index_near','U16','U8 i','return nb[i];',None),
 ('offset_far','U16','void','return *(fb+3);','[_fb],y'),
 ('offset_negative','U16','void','return *(fb-1);',None),
 ('field_word','U16','void','return row->a;','[_row]'),
 ('field_long','U32','void','return row->b;','[_row],y'),
 ('field_byte','U16','void','return row->c;','[_row],y'),
 ('field_index','U32','U8 i','return row[i].b;','[_row],y'),
 ('framed','U32','U16 x','U16 local[3];local[0]=x;local[2]=x+3;return fl[2]+local[0]+local[2];','[_fl],y'),
 ('store_nb','U16','U16 x','return *nb=(U8)x;','(_nb)'),
 ('store_fb','U16','U16 x','return *fb=(U8)x;','[_fb]'),
 ('store_fw','U16','U16 x','return *fw=x;','[_fw]'),
 ('store_index','U16','U8 i,U16 x','return fw[i]=x;','[_fw],y'),
 ('store_field','U16','U16 x','return row->c=(U8)x;','[_row],y'),
 ('store_vb','U16','U16 x','return *vfb=(U8)x;','[_vfb]'),
 ('store_vnear','U16','U16 x','return *vnb=(U8)x;','(_vnb)'),
 ('store_vwide','U32','U32 x','return *vfl=x;',None),
 ('store_wide','U32','U32 x','return *fl=x;',None),
 ('store_call','U16','void','return *fb=(U8)change_pointer();',None),
 ('store_alias','U16','void','return *fb=(U8)(*alias=other);',None),
 ('load_effect','U16','void','return fb[change_index()];',None),
 ('compound','U16','void','return *fw+=3;',None),
 ('post_far','U16','void','return *fb++;',None),
 ('post_near','U16','void','return *nb++;','(_nb)'),
]
PROTOS='\n'.join(f'{ret} {name}({params});' for name,ret,params,_,_ in FUNCTIONS)
KERNELS=DECLS+'\n'+'\n'.join(f'{ret} {name}({params}){{{body}}}' for name,ret,params,body,_ in FUNCTIONS)
DRIVER=DECLS+'\n'+PROTOS+'''
U8 bytes[64];U16 words[32];U32 longs[8];float floats[2];struct Row rows[4];
U16 changes;
U16 change_pointer(void){fb=other;changes++;return 77;}
U16 change_index(void){fb=other;changes++;return 0;}
int main(void){
 nb=bytes;vnb=bytes;nsb=(signed char *)bytes;fsb=(signed char *)bytes;nw=words;nl=longs;
 ffloat=floats;floats[0]=3.5;
 fb=bytes;fw=words;fl=longs;vfb=bytes;vfl=longs;vptr=bytes;plain=bytes;row=rows;
 bytes[0]=0x80;bytes[3]=23;words[0]=0xbeef;words[3]=0x1234;
 longs[0]=0x89abcdefUL;longs[2]=0x12345678UL;
 rows[0].a=73;rows[0].b=0xabcdef01UL;rows[0].c=91;rows[2].b=0x76543210UL;
 dp_array[0]=19;dp_array[3]=17;
 if(array_dp(3)!=17||array_plain()!=19||auto_ptr(bytes)!=128)return 19;
 plain=dp_array;if(load_plain()!=19)return 20;plain=bytes;
 if(load_nb()!=128||load_s()!=-128||load_nw()!=0xbeef||load_nl()!=0x89abcdefUL)return 1;
 if(add_nw(0x5555)!=0x1444u||sub_nw(0x1234)!=0x5345u||xor_nw(0x00ff)!=0xbe10u)return 24;
 if(load_fs()!=-128||load_float()!=3.5||load_vnear()!=128)return 21;
 if(load_fb()!=128||load_fw()!=0xbeef||load_fl()!=0x89abcdefUL)return 2;
 if(load_vb()!=128||load_vl()!=0x89abcdefUL||load_vptr()!=128||load_plain()!=128||load_cast()!=128)return 3;
 if(index_byte(3)!=23||index_word(3)!=0x1234||index_long(2)!=0x12345678UL||index_mask(35)!=0x1234)return 4;
 if(index_signed(3)!=23||index_overflow(3)!=0x1234||index_near(3)!=23||offset_far()!=23)return 5;
 fb=bytes+1;if(index_signed(-1)!=128||offset_negative()!=128)return 6;fb=bytes;
 if(field_word()!=73||field_long()!=0xabcdef01UL||field_byte()!=91||field_index(2)!=0x76543210UL)return 7;
 if(framed(7)!=0x12345689UL)return 8;
 if(store_nb(0x1aa)!=170||bytes[0]!=170||store_fb(0x155)!=85||bytes[0]!=85)return 9;
 if(store_fw(0x2345)!=0x2345||words[0]!=0x2345||store_index(3,0x9876)!=0x9876||words[3]!=0x9876)return 10;
 if(store_field(0x166)!=102||rows[0].c!=102||store_vb(0x177)!=119||bytes[0]!=119)return 11;
 if(store_vnear(0x188)!=136||bytes[0]!=136)return 22;
 if(store_vwide(0x31415926UL)!=0x31415926UL||longs[0]!=0x31415926UL)return 23;
 if(store_wide(0xfedcba98UL)!=0xfedcba98UL||longs[0]!=0xfedcba98UL)return 12;
 other=bytes+16;bytes[16]=33;fb=bytes;
 if(store_call()!=77||bytes[0]!=77||bytes[16]!=33||fb!=other)return 13;
 fb=bytes;alias=&fb;if(store_alias()!=(U8)(unsigned)other||bytes[0]!=(U8)(unsigned)other||fb!=other)return 14;
 fb=bytes;bytes[0]=41;if(load_effect()!=41||fb!=other||changes!=2)return 15;
 words[0]=10;if(compound()!=13||words[0]!=13)return 16;
 fb=bytes;if(post_far()!=41||fb!=bytes+1)return 17;
 nb=bytes;if(post_near()!=41||nb!=bytes+1)return 18;
 return 0;
}
'''
BOUNDARY=DECLS+'\n'+PROTOS+'''
U16 running=1,operation,index;
U32 input,result;
U16 change_pointer(void){return 0;}
U16 change_index(void){return 0;}
__noinline void boundary_ready(void){}
__noinline void boundary_after(void){}
int main(void){while(running){boundary_ready();
 switch(operation){
 case 0:result=load_fb();break;
 case 1:result=load_fw();break;
 case 2:result=load_fl();break;
 case 3:result=load_vl();break;
 case 4:result=index_byte(index);break;
 case 5:result=index_overflow(index);break;
 case 6:result=index_signed((int)index);break;
 case 7:result=index_near((U8)index);break;
 case 8:result=store_wide(input);break;
 case 9:result=load_vptr();break;
 }
 boundary_after();}return 0;}
'''


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def build(mode):
    directory=OUT/mode;directory.mkdir(parents=True,exist_ok=True);c.OUT=directory
    header=directory/'api.h';header.write_text(DECLS+'\n'+PROTOS+'\n')
    globals=directory/'globals.c';globals.write_text(DECLS.replace('extern ','').replace('U16 change_pointer(void);','').replace('U16 change_index(void);',''))
    kernels=directory/'kernels.c';kernels.write_text(KERNELS)
    objects=[]
    for source in (globals,kernels):
        flags=['--no-direct-dpage'] if mode=='fallback' else []
        c.run([ROOT/'build/zicc.exe',source,'-o',source.with_suffix('.s'),*flags])
        c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',source.with_suffix('.o'),source.with_suffix('.s')]);objects.append(source.with_suffix('.o'))
    assembly=kernels.with_suffix('.s').read_text();selected={}
    debug=c.run([c.CC65/'od65.exe','--dump-dbgsyms',kernels.with_suffix('.o')]).stdout
    (directory/'kernels.debug-symbols.txt').write_text(debug)
    sizes={name:int(value,16) for name,value in re.findall(r'Name:\s+"__size_(\w+)"\s+Value:\s+0x([0-9A-F]+)',debug)}
    for name,_,_,_,operand in FUNCTIONS:
        body=assembly.split('_'+name+':\n',1)[1].split('__size_'+name+' =',1)[0]
        indirect=re.findall(r'\b(?:lda|sta|adc|sbc|eor)\s+([\[(]_[A-Za-z][^\n]+)',body)
        if mode=='direct' and operand:
            assert any(operand in value for value in indirect),(name,body)
            mnemonic={'add_nw':'adc','sub_nw':'sbc','xor_nw':'eor'}.get(name)
            if mnemonic: assert f'{mnemonic} {operand}' in body,(name,body)
            pointer=re.search(r'_([A-Za-z]+)',operand)[1]
            assert not re.search(r'\b(?:lda|ldx) z:_'+pointer+r'(?:\+|\n)',body),(name,'redundant pointer reload',body)
        elif mode=='direct' and operand is None:
            assert not indirect,(name,'unsupported direct access',body)
        elif mode=='fallback':assert not indirect,(name,body)
        selected[name]=dict(indirect=indirect,code_bytes=sizes[name])
    _,rom,sy=c.compile_case('driver',DRIVER,extra_objects=[*objects,ROOT/'build/integers.o',ROOT/'build/arithmetic.o',ROOT/'build/ieee_engine.o',ROOT/'build/tables.o'])
    c.compile_case('boundary',BOUNDARY,extra_objects=[*objects,ROOT/'build/integers.o',ROOT/'build/arithmetic.o',ROOT/'build/ieee_engine.o',ROOT/'build/tables.o'])
    return rom,sy,selected


def boundary_worker(mode):
    directory=OUT/mode;home=directory/'boundary-run';home.mkdir(exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(directory/'boundary.labels').read_text(),re.M)}
    cases=[]
    def add(op,pointer,base,target,value,size,index=0):
        cases.append(dict(op=op,pointer=sy[pointer],base=base,target=target,value=value,size=size,index=index))
    for base in (0x7efffe,0x7effff,0xfffffe,0xffffff):
        add(0,'fb',base,base,0x87,1)
        add(1,'fw',base,base,0x3412,2)
        # Four bytes from $FF:FFFF include the compiler-owned scratch at $00:0002
        # $FF:FFFE already covers the same wrap for the four-byte loads
        if base != 0xffffff:
            add(2,'fl',base,base,0x78563412,4)
            add(3,'vfl',base,base,0x98765432,4)
    add(4,'fb',0x7e6001,0x7f6000,0x83,1,65535)
    add(5,'fw',0x7e6000,0x7f6000,0x9988,2,32768)
    add(6,'fb',0x7f0000,0x7effff,0x71,1,65535)
    # Near addition truncates before dereference; indirect,Y would carry into
    # $7F instead. This must remain the captured-address fallback
    add(7,'nb',0xfffe,0x7e0001,0x52,1,3)
    # Explicit machine-address overlap fixture: a wide store overwrites its own
    # DP pointer bytes. The saved address must survive the first component
    add(8,'fl',0x7e0000|sy['fl'],0x7e0000|sy['fl'],0x12345678,4)
    add(9,'vptr',0x7e6000,0x7e6000,0x64,1)
    table='{'+','.join('{'+','.join(k+'='+str(v) for k,v in row.items())+'}' for row in cases)+'}'
    script=f'''local cases={table}
local id=0
local active=false
local events={{}}
local all={{}}
local function put(a,v)emu.write(a&0x1ffff,v&255,emu.memType.snesWorkRam)end
local function putword(a,v)put(a,v);put(a+1,v>>8)end
local function seed(a,v)
 a=a&0xffffff;local bank=a>>16;local lo=a&65535
 if bank==0x7e or bank==0x7f then put(a,v)
 elseif lo<0x2000 and (bank<0x40 or bank>=0x80 and bank<0xc0) then put(lo,v)
 else emu.write(a&0x7fff,v,emu.memType.snesPrgRom)end
end
emu.addMemoryCallback(function()
 id=id+1;local c=cases[id];assert(c,'boundary coverage')
 events={{}};putword({sy['operation']},c.op);putword({sy['index']},c.index)
 putword({sy['input']},c.value);putword({sy['input']+2},c.value>>16)
 -- Poison the non-address padding byte: [dp] must consume three bytes only
 putword(c.pointer,c.base&65535);put(c.pointer+2,c.base>>16);put(c.pointer+3,165)
 if c.op~=8 then for i=0,c.size-1 do seed(c.target+i,(c.value>>(8*i))&255)end end
 active=true
end,emu.callbackType.exec,{sy['boundary_ready']},{sy['boundary_ready']})
emu.addMemoryCallback(function(a)
 if not active then return end
 local c=cases[id]
 for i=0,c.size-1 do if a==((c.target+i)&0xffffff) then events[#events+1]='R:'..a end end
end,emu.callbackType.read,0,0xffffff)
emu.addMemoryCallback(function(a,v)
 if not active then return end
 local c=cases[id]
 for i=0,c.size-1 do if a==((c.target+i)&0xffffff) then events[#events+1]='W:'..a..':'..v end end
end,emu.callbackType.write,0,0xffffff)
emu.addMemoryCallback(function()
 active=false;local c=cases[id]
 local result=emu.read16({sy['result']}&0x1ffff,emu.memType.snesWorkRam,false)|(emu.read16(({sy['result']}+2)&0x1ffff,emu.memType.snesWorkRam,false)<<16)
 local expected=c.op==7 and (c.value&255) or c.value
 assert(result==expected,'boundary '..id..' result '..result..' expected '..expected)
 if c.op==8 then for i=0,3 do assert(emu.read(c.pointer+i,emu.memType.snesWorkRam,false)==((c.value>>(8*i))&255),'overlap snapshot')end end
 all[#all+1]=id..'='..table.concat(events,',')
 if id==#cases then putword({sy['running']},0)end
end,emu.callbackType.exec,{sy['boundary_after']},{sy['boundary_after']})
emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0 and s['cpu.sp']==0x4ff and s['cpu.y']==0 and s['cpu.dbr']==0x7e and s['cpu.d']==0,'boundary ABI')
 assert(id==#cases,'boundary count');for _,row in ipairs(all)do emu.log('TRACE '..row)end
 emu.log('PASS boundary cases='..id);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    script="local function assert(ok,msg)if not ok then emu.breakExecution();error(msg or 'assertion')end end\n"+script
    core=Core(home,cache=False)
    try:
        lua=home/'check.lua';lua.write_text(script);core.load(directory/'boundary.sfc',lua,script);core.start();log=core.wait_for('PASS boundary',30)
    finally:core.close_with_log(home/'check.log')
    trace=re.findall(r'^TRACE (.*)',log,re.M);assert len(trace)==len(cases)
    (home/'result.json').write_text(json.dumps(trace,indent=2)+'\n')


def placement_checks():
    directory=OUT/'placement';directory.mkdir(exist_ok=True);c.OUT=directory
    for mode in ('direct','fallback'):
        units=[]
        for name,source in [('definitions','__dpage char fill[218];__dpage volatile unsigned char * __far limit;'),
                            ('leaf','extern __dpage volatile unsigned char * __far limit;unsigned read_limit(void){return *limit;}')]:
            file=directory/(name+'-'+mode+'.c');file.write_text(source)
            flags=['--no-direct-dpage'] if mode=='fallback' else []
            c.run([ROOT/'build/zicc.exe',file,'-o',file.with_suffix('.s'),*flags])
            c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',file.with_suffix('.o'),file.with_suffix('.s')]);units.append(file.with_suffix('.o'))
        source='extern __dpage volatile unsigned char * __far limit;unsigned read_limit(void);unsigned char data;int main(void){data=87;limit=&data;return read_limit()!=87;}'
        _,rom,sy=c.compile_case('limit-'+mode,source,extra_objects=[*units,ROOT/'build/dp-scratch.o',ROOT/'build/arithmetic.o',ROOT/'build/ieee_engine.o',ROOT/'build/tables.o'])
        assert sy['limit']==0xfc
        assert sy['_dp_scratch']==sy['_arith_lhs']==2 and sy['_arith_rhs']==6
        if mode=='direct':assert 'lda [_limit]' in (directory/'leaf-direct.s').read_text()
        c.emulate(rom,sy,0)
    # External assembly must obey the placement promise too, not merely export
    # a zero-page-typed symbol that overlaps reserved arithmetic workspace
    for address in (0x21, 0xff):
        bad=directory/f'bad-{address:02x}.s';bad.write_text(f'.exportzp _limit\n_limit=${address:02X}\n')
        c.run([c.CC65/'ca65.exe','-o',bad.with_suffix('.o'),bad])
        result=subprocess.run([str(c.CC65/'ld65.exe'),'-C',str(ROOT/'linker/lorom32.cfg'),'-o',str(bad.with_suffix('.raw')),str(ROOT/'build/startup.o'),str(directory/'limit-direct.o'),str(directory/'leaf-direct.o'),str(bad.with_suffix('.o')),str(ROOT/'build/nmi.o'),str(ROOT/'build/vectors.o'),str(ROOT/'build/rom_header.o')],capture_output=True,text=True)
        assert result.returncode and '__dpage pointer exceeds allocated direct page' in result.stderr,result.stderr


def worker(mode,repeat):
    directory=OUT/mode;home=directory/('run'+str(repeat));home.mkdir(exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',(directory/'driver.labels').read_text(),re.M)}
    script=f'''local started=false
local first=0
local calls={{}}
local pending={{}}
local registered={{}}
local vb={{}}
local vl={{}}
local vp={{}}
local stores={{}}
local function word(a)return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false)end
local function hook(name,address)
 emu.addMemoryCallback(function()
  calls[name]=(calls[name] or 0)+1
  if name=='load_vnear' or name=='load_vb' then vb={{}} end
  if name=='store_vnear' or name=='store_vb' or name=='store_vwide' then stores={{}} end
  local s=emu.getState();local target=(s['cpu.k']<<16)|((word(s['cpu.sp']+1)+1)&65535)
  pending[target]={{name=name,sp=s['cpu.sp'],y=s['cpu.y']}}
  if not registered[target] then registered[target]=true
   emu.addMemoryCallback(function()
    local p=pending[target];if not p then return end
    local t=emu.getState();assert(t['cpu.sp']==p.sp+2 and t['cpu.y']==p.y and t['cpu.d']==0 and t['cpu.dbr']==0x7e,'call ABI '..p.name)
    if p.name=='load_vb' or p.name=='load_vnear' then assert(#vb==1 and vb[1]=={sy['bytes']},'volatile byte width') end
    if p.name=='load_vl' then assert(#vl==4,'volatile wide width');for i=1,4 do assert(vl[i]=={sy['longs']}+i-1,'volatile wide order')end end
    if p.name=='load_vptr' then assert(#vp==4,'volatile pointer object width');for i=1,4 do assert(vp[i]=={sy['vptr']}+i-1,'volatile pointer order')end end
    if p.name=='store_vnear' or p.name=='store_vb' then assert(#stores==1 and stores[1]=={sy['bytes']},'volatile byte store width')end
    if p.name=='store_vwide' then assert(#stores==4,'volatile wide store width');for i=1,4 do assert(stores[i]=={sy['longs']}+i-1,'volatile wide store order')end end
    pending[target]=nil
   end,emu.callbackType.exec,target,target)
  end
 end,emu.callbackType.exec,address,address)
end
'''
    for name,*_ in FUNCTIONS:script+=f"hook('{name}',{sy[name]})\n"
    script+=f'''emu.addMemoryCallback(function(a)
 for _,p in pairs(pending)do if p.name=='load_vb' or p.name=='load_vnear' then vb[#vb+1]=a elseif p.name=='load_vl' then vl[#vl+1]=a end end
end,emu.callbackType.read,{sy['bytes']},{sy['longs']+31})
emu.addMemoryCallback(function(a)
 for _,p in pairs(pending)do if p.name=='store_vnear' or p.name=='store_vb' or p.name=='store_vwide' then stores[#stores+1]=a end end
end,emu.callbackType.write,{sy['bytes']},{sy['longs']+31})
emu.addMemoryCallback(function(a) for _,p in pairs(pending)do if p.name=='load_vptr' then vp[#vp+1]=a end end end,emu.callbackType.read,{sy['vptr']},{sy['vptr']+3})
emu.addMemoryCallback(function() started=true;first=emu.getState().masterClock end,emu.callbackType.exec,{sy['main']},{sy['main']})
emu.addMemoryCallback(function()
 local s=emu.getState();assert(started and s['cpu.a']==0,'driver result '..s['cpu.a']);assert(s['cpu.sp']==0x4ff and s['cpu.y']==0 and s['cpu.d']==0 and s['cpu.dbr']==0x7e,'main ABI')
'''
    for name,*_ in FUNCTIONS:script+=f" assert(calls['{name}']=={2 if name in ('load_plain','index_signed') else 1},'call coverage {name}')\n"
    script+=" emu.log('CLOCKS '..(s.masterClock-first));emu.log('PASS direct-page pointer accesses');emu.breakExecution()\nend,emu.callbackType.exec,"+str(sy['main_exit'])+','+str(sy['main_exit'])+')\n'
    script="local function assert(ok,msg)if not ok then emu.breakExecution();error(msg or 'assertion')end end\n"+script
    core=Core(home,cache=False)
    try:
        lua=home/'check.lua';lua.write_text(script);core.load(directory/'driver.sfc',lua,script);core.start();log=core.wait_for('PASS direct-page',30)
    finally:core.close_with_log(home/'check.log')
    report=dict(master_clocks=int(re.search(r'CLOCKS (\d+)',log)[1]),rom_sha256=sha(directory/'driver.sfc'),compiler_sha256=sha(ROOT/'build/zicc.exe'))
    (home/'result.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if len(sys.argv)>1:
        if sys.argv[1]=='boundary':boundary_worker(sys.argv[2])
        else:worker(sys.argv[1],int(sys.argv[2]))
        return
    results={}
    for mode in ('direct','fallback'):
        _,_,selection=build(mode)
        for repeat in (1,2):c.run([sys.executable,__file__,mode,str(repeat)],timeout=60)
        runs=[json.loads((OUT/mode/('run'+str(i))/'result.json').read_text()) for i in (1,2)]
        assert runs[0]==runs[1],mode
        results[mode]=dict(selection=selection,runs=runs)
        c.run([sys.executable,__file__,'boundary',mode],timeout=60)
    traces=[json.loads((OUT/m/'boundary-run/result.json').read_text()) for m in ('direct','fallback')]
    assert traces[0]==traces[1],'bank/wrap/overlap transfer traces differ'
    results['boundaries']=traces[0]
    placement_checks()
    for name,_,_,_,operand in FUNCTIONS:
        if operand:assert results['direct']['selection'][name]['code_bytes']<results['fallback']['selection'][name]['code_bytes'],name
    assert results['direct']['runs'][0]['master_clocks']<results['fallback']['runs'][0]['master_clocks']
    results['input_sha256']={str(p.relative_to(ROOT)):sha(p) for folder in ('src','runtime') for p in (ROOT/folder).rglob('*') if p.is_file()}
    results['input_sha256'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    results['fixture_sha256']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.suffix in ('.c','.s','.o','.sfc','.lua')}
    results['tool_sha256']={str(p):sha(p) for p in [c.CC65/'ca65.exe',c.CC65/'ld65.exe',c.CC65/'od65.exe',Path(os.environ.get('MESEN_CORE_DLL','D:/dev/dragon/tools/mesen/MesenCore.dll'))]}
    (OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PASS direct-page pointer loads/stores/indexed/fields, negative selectors, snapshots, volatile widths/order and paired execution')


if __name__=='__main__':main()
