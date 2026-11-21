"""Check cached far format cursors, variadic floats, bank wraps and nested NMI printf."""
import os
import argparse,importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'printf-cursor-check';c.OUT=OUT
SOURCE=r'''
#include <stdio.h>
void arm(unsigned phase);
volatile unsigned glyph=0x141;
__noinline void emit_char(unsigned value){printf("%c",(int)value);}
int main(void){
 arm(1);if(printf("<%g|%g%%>",1.5,-2.0)!=9)return 1;
 arm(2);if(printf("F=%gZ",2.0)!=4)return 2;
 if(printf((char * __far)0x7efffcUL,1.5,-2.0)!=9)return 3;
 if(printf((char * __far)0x7fffffUL)!=0)return 4;
 if(printf((char * __far)0xfffffeUL)!=2)return 5;
 if(printf("Q%q",7)!=-1)return 6;
 if(printf("OK")!=2)return 7;
 emit_char(glyph);
 return 0;
}
'''
HELPER=r'''
.setcpu "65816"
.a16
.i16
.import _printf
.export _arm,cursor_read_probe,cursor_float_probe,__vector_nmi,__nmi_entry,nmi_entry,cursor_nmi,nmi_count
__nmi_entry = __vector_nmi
nmi_entry = __vector_nmi
.segment "BSS"
phase: .res 2
nmi_count: .res 2
.segment "RODATA"
inner: .byte "!",0
.segment "CODE"
_arm:
    stx a:.loword(phase)
    rts
cursor_read_probe:
    php
    rep #$30
    pha
    phx
    ldx #1
    bra probe
cursor_float_probe:
    php
    rep #$30
    pha
    phx
    ldx #2
probe:
    phy
    phd
    phb
    txa
    cmp a:.loword(phase)
    bne done
    stz a:.loword(phase)
    lda a:.loword(nmi_count)
    pha
    sep #$20
.a8
    lda f:$004210
    lda #$80
    sta f:$004200
    rep #$20
.a16
wait:
    lda a:.loword(nmi_count)
    cmp 1,s
    beq wait
    pla
    sep #$20
.a8
    lda #0
    sta f:$004200
    rep #$20
.a16
done:
    plb
    pld
    ply
    plx
    pla
    plp
    rts
__vector_nmi:
    jml cursor_nmi
cursor_nmi:
    rep #$30
    pha
    phx
    phy
    phd
    phb
    .repeat 16,I
    pei ($02+I*2)
    .endrepeat
    sep #$20
.a8
    lda f:$004210
    rep #$20
.a16
    pea .bankbyte(inner)
    pea .loword(inner)
    jsr .loword(_printf)
    plx
    plx
    inc a:.loword(nmi_count)
    .repeat 16,I
    pla
    sta z:$20-I*2
    .endrepeat
    plb
    pld
    ply
    plx
    pla
    rti
'''

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    helper=OUT/'probe.s';helper.write_text(HELPER)
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',helper.with_suffix('.o'),helper])
    # Only the test copy gets an exported private label and synchronous wait
    # probes. The benchmark and production library retain their real bytes
    text=(ROOT/'runtime/console.s').read_text()
    assert text.count('    lda [console_format_pointer]')==1
    text=text.replace('format_next:','.exportzp console_format_pointer\n.import cursor_read_probe,cursor_float_probe\nformat_next:')
    text=text.replace('    lda [console_format_pointer]','    jsr .loword(cursor_read_probe)\n    lda [console_format_pointer]')
    assert text.count('    jsr .loword(__format_float_hook)')==1
    text=text.replace('    jsr .loword(__format_float_hook)','    jsr .loword(cursor_float_probe)\n    jsr .loword(__format_float_hook)')
    console=OUT/'console.s';console.write_text(text)
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-D','CALC=1','-D','ZICC_BINARY64=1',
           '-I',ROOT,'-o',console.with_suffix('.o'),console])
    run=c.run
    def link(command,**kwargs):
        command=[console.with_suffix('.o') if str(p)==str(ROOT/'build/console.o') else p for p in command]
        return run(command,**kwargs)
    c.run=link
    c.compile_case('cursor',SOURCE,console=True,extra_objects=[helper.with_suffix('.o'),*[ROOT/'build'/(n+'.o') for n in ('arithmetic','integers','ieee_engine','tables','io','decimal')]])
    assembly=(OUT/'cursor.s').read_text()
    wrapper=assembly.split('_emit_char:\n',1)[1].split('__size_emit_char',1)[0]
    assert '_printf' in wrapper and 'plx' not in wrapper,wrapper

def worker(region):
    stem=OUT/'cursor';home=OUT/region;home.mkdir(exist_ok=True)
    sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
    script='''local output=''
local entries,returns,nmis,nmi_returns,floats=0,0,0,0,0
local pending,registered={},{}
local function word(a)return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false)end
local function bytes(p)local b={};for i=0,3 do b[i]=emu.read(p+i,emu.memType.snesWorkRam,false)end;return b end
local function same(p,b)for i=0,3 do assert(emu.read(p+i,emu.memType.snesWorkRam,false)==b[i],'cursor restore '..i)end end
local expected={['<%g|%g%%>']=9,['!']=1,['F=%gZ']=4,['A%g|%g%%Z']=9,['']=0,['AZ']=2,['Q%q']=65535,['OK']=2,['%c']=1}
local function text(p)local s='';for i=0,127 do local b=emu.read((p+i)&0xffffff,emu.memType.snesMemory,false);if b==0 then return s end;s=s..string.char(b)end;error('format termination')end
'''
    script+=f'''emu.addMemoryCallback(function()
 for i,b in ipairs({{0x23,0x45,0x67,0x89}})do emu.write({sy['console_format_pointer']}+i-1,b,emu.memType.snesWorkRam)end
 local fmt='A%g|%g%%Z'..string.char(0);for i=1,#fmt do emu.write(0xfffc+i-1,string.byte(fmt,i),emu.memType.snesWorkRam)end
 emu.write(0x1ffff,0,emu.memType.snesWorkRam);emu.write(0,0,emu.memType.snesWorkRam)
 emu.write(0x7ffe,65,emu.memType.snesPrgRom);emu.write(0x7fff,90,emu.memType.snesPrgRom)
end,emu.callbackType.exec,{sy['main']},{sy['main']})
emu.addMemoryCallback(function()
 output=output..string.char(emu.getState()['cpu.x']&255)
end,emu.callbackType.exec,{sy['console_putc']},{sy['console_putc']})
emu.addMemoryCallback(function()floats=floats+1 end,emu.callbackType.exec,{sy['_ieee64_format']},{sy['_ieee64_format']})
emu.addMemoryCallback(function()
 local s=emu.getState();entries=entries+1
 local fmt=text(word(s['cpu.sp']+3)|(word(s['cpu.sp']+5)<<16));assert(expected[fmt]~=nil,'format '..fmt)
 local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
 pending[target]=pending[target] or {{}};table.insert(pending[target],{{state=s,cache=bytes({sy['console_format_pointer']}),value=expected[fmt]}})
 if not registered[target]then registered[target]=true;emu.addMemoryCallback(function()
  local t=emu.getState();local list=pending[target]
  for i=#list,1,-1 do local r=list[i];local s=r.state
   if t['cpu.sp']==s['cpu.sp']+2 then
    for _,k in ipairs({{'y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'printf '..k)end
    assert((t['cpu.ps']&0x3c)==(s['cpu.ps']&0x3c),'printf modes');assert(t['cpu.a']==r.value,'printf return')
    same({sy['console_format_pointer']},r.cache);returns=returns+1;table.remove(list,i);break
   end
  end
 end,emu.callbackType.exec,target,target)end
end,emu.callbackType.exec,{sy['printf']},{sy['printf']})
emu.addMemoryCallback(function()
 nmis=nmis+1;local s=emu.getState();local sp=s['cpu.sp'];local target=(emu.read(sp+4,emu.memType.snesWorkRam,false)<<16)|word(sp+2)
 local ps=emu.read(sp+1,emu.memType.snesWorkRam,false);local dp={{}};for i=0,15 do dp[i]=word(0x02+i*2)end
 local cache=bytes({sy['console_format_pointer']});local done=false
 emu.addMemoryCallback(function()
  if done then return end;done=true;nmi_returns=nmi_returns+1;local t=emu.getState()
  for _,k in ipairs({{'a','x','y','d','dbr'}})do assert(t['cpu.'..k]==s['cpu.'..k],'NMI '..k)end
  assert(t['cpu.sp']==sp+4 and t['cpu.ps']==ps and t['cpu.k']==(target>>16),'NMI frame')
  for i=0,15 do assert(word(0x02+i*2)==dp[i],'NMI scratch')end;same({sy['console_format_pointer']},cache)
 end,emu.callbackType.exec,target,target)
end,emu.callbackType.exec,{sy['cursor_nmi']},{sy['cursor_nmi']})
emu.addMemoryCallback(function()
 local s=emu.getState();assert(s['cpu.a']==0,'result '..s['cpu.a']);assert(s['cpu.sp']==1279,'main stack')
 assert(output=='!<1.5|-2%>F=!2ZA1.5|-2%ZAZQ?OKA','text '..output)
 assert(entries==10 and returns==10 and floats==5,'work counts');assert(nmis==2 and nmi_returns==2 and word({sy['nmi_count']})==2,'NMI counts')
 same({sy['console_format_pointer']},{{[0]=0x23,0x45,0x67,0x89}})
 for i=1,#output do local cell=(i-1)//2*2+((i-1)%2)*2048;assert(emu.read(({sy['console_map']&0x1ffff}+cell)&0x1ffff,emu.memType.snesWorkRam,false)==(string.byte(output,i)*2)&255,'tilemap')end
 emu.log('PASS {region} printf='..entries..' floats='..floats..' nested-NMI='..nmis);emu.breakExecution()
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    core=Core(home)
    try:
        config=SnesConfig();config.Region=1 if region=='ntsc' else 2;config.Port1.Type=1
        config.DisableFrameSkipping=True;config.RamPowerOnState=1;config.GsuClockSpeed=100;config.BsxCustomDate=-1
        for i in range(8):config.ChannelVolumes[i]=100
        core.bind('SetSnesConfig',None,SnesConfig)(config)
        core.load(stem.with_suffix('.sfc'),home/'check.lua',script);core.start();log=core.wait_for('PASS',30)
        print(next(line for line in log.splitlines() if line.startswith('PASS ')))
    finally:core.close_with_log(home/'check.log')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--region',choices=('ntsc','pal'));a=p.parse_args()
    if a.region:worker(a.region)
    else:
        build();report={}
        for region in ('ntsc','pal'):
            report[region]=c.run([sys.executable,__file__,'--region',region],timeout=45).stdout;print(report[region].strip())
        (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
