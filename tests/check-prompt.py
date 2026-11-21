"""Exercise typed C calls, the text console, ABI preservation and VBlank DMA."""
import os
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'prompt-check'
spec = importlib.util.spec_from_file_location('compiler_checks', Path(__file__).with_name('check-compiler.py'))
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def terminal(text):
    cells=[0]*2048;cursor=0;origin=0
    for char in text:
        if char=='\r':cursor=cursor//64*64
        elif char=='\n':cursor=(cursor//64+1)*64
        else:
            logical=(origin*64+cursor)&2047
            physical=(logical//64)*32+(logical%64)//2+(logical%2)*1024
            cells[physical]=(ord(char) if 32<=ord(char)<127 else ord('?'))*2
            cursor+=1
        if cursor==1792:
            origin=(origin+1)&31;cursor=1728
            row=((origin+27)&31)*32
            for layer in (0,1024):cells[layer+row:layer+row+32]=[0]*32
    return [byte for cell in cells for byte in (cell&255,cell>>8)],cursor*2,origin



def emulate(name, rom, labels, text, returns, flushes, return_value=None, error=0, screenshot=False):
    expected, cursor, origin = terminal(text)
    lua_array = lambda values: '{' + ','.join(map(str, values)) + '}'
    font = (ROOT / 'assets/console/ascii8x8.2bpp').read_bytes()
    vram_font = b''.join(font[i:i + 16] + bytes(padding)
                         for padding in (48, 16) for i in range(0, len(font), 16))
    palette = (ROOT / 'assets/console/palette.bgr555').read_bytes()
    loop = next((address for label, address in labels.items() if label.startswith('cg_prompt_')), labels.get('main'))
    end = labels['main_exit'] if return_value is not None else loop
    nmi_entry = int.from_bytes(rom.read_bytes()[0xffea:0xffec] if len(rom.read_bytes()) >= 65536 and rom.read_bytes()[0xffd5] == 0x31 else rom.read_bytes()[0x7fea:0x7fec], 'little')
    assert end is not None
    lua = f'''
local bad,ready,entered=false,false,false
local output=''
local bgmode,setini=nil,nil
emu.addMemoryCallback(function(a,v) bgmode=v end,emu.callbackType.write,0x002105)
emu.addMemoryCallback(function(a,v) setini=v end,emu.callbackType.write,0x002133)
emu.addMemoryCallback(function()
 output=output..string.char(emu.getState()['cpu.x']&255)
end,emu.callbackType.exec,{labels['console_putc']},{labels['console_putc']})
local frames,printf_returns,flush_returns,flush_dmas,nmis=0,0,0,0,0
local enables,acks=0,0
local vaddr=0
emu.addMemoryCallback(function(a,v) vaddr=(vaddr&0xff00)|v end,emu.callbackType.write,0x002116)
emu.addMemoryCallback(function(a,v) vaddr=(vaddr&0x00ff)|(v<<8) end,emu.callbackType.write,0x002117)
local in_flush=false
local pending={{}}
local registered={{}}
local expected={lua_array(expected)}
local printf_expected={lua_array([value & 0xffff for value in returns])}
local function check(ok,message)
 if not ok then print('FAIL '..message);bad=true end
end
local function byte(address,kind) return emu.read(kind==emu.memType.snesWorkRam and (address&0x1ffff) or address,kind,false) end
emu.addMemoryCallback(function()
 for i=0,12287 do emu.write(i,0xff,emu.memType.snesVideoRam,false) end
end,emu.callbackType.exec,{labels['console_init']},{labels['console_init']})
local function verify_abi(s,message,y)
 check((y==false or s['cpu.y']==(y or 0x5a3c)) and s['cpu.d']==0 and s['cpu.dbr']==0x7e,message..' preserved registers')
 check((s['cpu.ps'] & 0x3c)==4,message..' width/interrupt flags')
end
emu.addMemoryCallback(function()
 nmis=nmis+1
end,emu.callbackType.exec,{nmi_entry},{nmi_entry})
emu.addMemoryCallback(function()
 if entered then return end
 entered=true
 check(bgmode==5 and setini==0,'512x224 without interlace or overscan')
 local s=emu.getState()
 check(s['cpu.a']==0 and s['cpu.x']==0 and s['cpu.y']==0,'startup registers')
 check(s['cpu.sp']==0x04fc and s['cpu.d']==0 and s['cpu.dbr']==0x7e,'startup environment')
 for i=0,4095 do check(byte({labels['console_map']}+i,emu.memType.snesWorkRam)==0,'initial map') end
 s['cpu.y']=0x5a3c
 emu.setState(s)
end,emu.callbackType.exec,{labels['main']},{labels['main']})
local function call_entry(is_flush)
 local s=emu.getState()
 verify_abi(s,'call entry',false)
 local target=(s['cpu.k']<<16) | ((emu.read16(((s['cpu.sp']+1)&0x1ffff),emu.memType.snesWorkRam,false)+1)&0xffff)
 local record={{sp=s['cpu.sp'],y=s['cpu.y'],flush=is_flush}}
 if not registered[target] then
  registered[target]=true
  emu.addMemoryCallback(function()
   local entry=pending[target]
   if not entry then return end
   local r=emu.getState()
   verify_abi(r,'call return',entry.y)
   check(r['cpu.sp']==entry.sp+2,'callee stack balance')
   if entry.flush then
    flush_returns=flush_returns+1
    check(r['cpu.a']=={0xffff if error == 2 else 0},'fflush return')
    in_flush=false
   else
    printf_returns=printf_returns+1
    check(r['cpu.a']==printf_expected[printf_returns],'printf count/error return')
   end
   pending[target]=false
  end,emu.callbackType.exec,target,target)
 end
 pending[target]=record
 if is_flush then in_flush=true end
end
emu.addMemoryCallback(function() call_entry(false) end,emu.callbackType.exec,{labels['printf']},{labels['printf']})
emu.addMemoryCallback(function() call_entry(true) end,emu.callbackType.exec,{labels['fflush']},{labels['fflush']})
emu.addMemoryCallback(function()
 acks=acks+1
end,emu.callbackType.read,0x004210)
emu.addMemoryCallback(function(address,value)
 if value==0x80 then
  enables=enables+1
  check(not entered and acks==1,'NMI enabled after setup and stale-flag read')
 else check(value==0,'unexpected interrupt configuration') end
end,emu.callbackType.write,0x004200)
emu.addMemoryCallback(function(address,value)
 if entered then
  flush_dmas=flush_dmas+1
  check(value==1,'DMA channel selection')
  check((byte(0x4212,emu.memType.snesMemory)&0x80)~=0,'DMA outside VBlank')
  local size=emu.read16(0x4305,emu.memType.snesMemory,false)
  local source=emu.read16(0x4302,emu.memType.snesMemory,false)-{labels['console_map']&65535}
  check(size>0 and size%64==0 and source>=0 and source%64==0 and source+size<=4096,'dirty row DMA range')
  check(byte(0x4304,emu.memType.snesMemory)==0x7f,'DMA source bank')
  check(vaddr==0x3000+source//2,'DMA VRAM destination')
 end
end,emu.callbackType.write,0x00420b)
emu.addMemoryCallback(function()
 check((byte(0x4212,emu.memType.snesMemory)&0x80)~=0,'presentation exceeded VBlank')
end,emu.callbackType.exec,{labels['console_present_done']},{labels['console_present_done']})
emu.addMemoryCallback(function()
 if ready then return end
 ready=true
 local s=emu.getState()
 verify_abi(s,'main completion')
 check(s['cpu.sp']=={1279 if return_value is not None else 1276},'caller stack cleanup')
 check(enables==1 and acks==1,'console NMI enablement')
 check(printf_returns==#printf_expected,'printf return callbacks')
 check(emu.read16((({labels['console_error']})&0x1ffff),emu.memType.snesWorkRam,false)=={error},'console error')
 check(emu.read16((({labels['console_cursor']})&0x1ffff),emu.memType.snesWorkRam,false)=={cursor},'cursor')
 for i=0,4095 do
  check(byte({labels['console_map']}+i,emu.memType.snesWorkRam)==expected[i+1],'WRAM tilemap byte '..i)
 end
 local font={lua_array(vram_font)}
 for i=0,12287 do check(byte(i,emu.memType.snesVideoRam)==font[i+1],'font byte '..i) end
 local palette={lua_array(palette)}
 for i=0,7 do check(byte(i,emu.memType.snesCgRam)==palette[i+1],'palette byte '..i) end
'''
    if return_value is not None:
        lua += f"check(s['cpu.a']=={return_value & 0xffff},'main result')\n"
    lua += f'''
end,emu.callbackType.exec,{end},{end})
emu.addEventCallback(function()
 if ready then
  frames=frames+1
  if frames==2 then
   check(flush_returns=={flushes},'flush return count')
   for i=0,4095 do check(byte(0x6000+i,emu.memType.snesVideoRam)==expected[i+1],'presented VRAM tilemap byte '..i) end
'''
    if screenshot:
        lua += "local png=emu.takeScreenshot();print('PNG '..(png:gsub('.',function(c)return string.format('%02x',string.byte(c))end)))\n"
    lua += "check(nmis>0,'console NMI delivery');if bad then print('OUTPUT '..output) end;print(bad and 'FAILED' or 'PASS');emu.stop(bad and 1 or 0)\nend end\nend,emu.eventType.endFrame)\n"
    script = OUT / f'{name}.lua'
    script.write_text(lua)
    result = support.run([support.mesen_executable(OUT), '--testRunner', '--doNotSaveSettings', '--snes.disableFrameSkipping=true',
                          '--timeout=8', rom, script], cwd=OUT)
    assert 'PASS' in result.stdout and 'FAIL' not in result.stdout, result.stdout
    for line in result.stdout.splitlines():
        if line.startswith('PNG '): (OUT / f'{name}.png').write_bytes(bytes.fromhex(line[4:]))
    if screenshot:
        image = Image.open(OUT / f'{name}.png').convert('RGB')
        # Mesen doubles each scanline in a hires screenshot, without PPU interlace
        assert image.size == (512,448)
        assert all(image.getpixel((x,2*y)) == image.getpixel((x,2*y+1))
                   for y in range(224) for x in range(512))
        image=image.resize((512,224),Image.Resampling.NEAREST)
        image.save(OUT / f'{name}-native.png')
        for y in range(224):
            for x in range(512):
                tile = expected[(((y // 8 + origin)&31)*32+x//16)*2+(x//8%2)*2048]//2
                offset = tile * 16 + (y % 8) * 2
                pixel = ((font[offset] >> (7-x%8)) & 1) | (((font[offset+1] >> (7-x%8)) & 1) << 1)
                color = (255,255,255) if pixel == 3 else (0,0,0)
                assert image.getpixel((x,y)) == color, (x,y,'rendered glyph/scroll mismatch')
    return {'text': text, 'printf_returns': returns, 'flush_calls': flushes, 'cursor': cursor, 'error': error}


def native(name, source):
    cfile, exe = OUT / f'{name}-host.c', OUT / f'{name}-host.exe'
    cfile.write_text(source)
    support.run([ROOT / 'tools/msvc.cmd', '/nologo', '/std:c17', '/W4', '/O2',
                 '/Fo' + str(OUT / f'{name}-host.obj'), '/Fe' + str(exe), cfile])
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=5)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    support.OUT = OUT
    report = {}
    labels = support.symbols(ROOT / 'build/prompt.sym')
    # Execution probes use raw linker labels, including internal DMA markers
    labels.update({name.removeprefix('_'): int(address, 16)
                   for address, name in re.findall(r'^al (\w+) \.(\S+)$',
                       (ROOT/'build/prompt.labels').read_text(), re.M)})
    dbg = (ROOT / 'build/prompt.dbg').read_text()
    first_loop = re.search(r'name="cg_prompt_1"[^\n]*val=0x([0-9a-fA-F]+)',dbg)
    assert first_loop
    labels['cg_prompt_loop'] = int(first_loop[1],16)
    raw = (ROOT / 'build/prompt.labels').read_text()
    labels.update({name.removeprefix('_'): int(address,16) for address,name in
                   re.findall(r'^al ([0-9a-fA-F]+) \.(_main_while_\w+)$',raw,re.M)})
    report['prompt'] = emulate('prompt',ROOT / 'build/prompt.sfc',labels,'> ',[2],1,screenshot=True)
    cases = [
        ('escapes', '#include <stdio.h>\n#include <stdio.h>\nint main(void){printf("A%%B\\n" "C\\rD");return fflush(stdout);}', 'A%B\nC\rD', [7], 1, 0, 0),
        ('count', '#include <stdio.h>\nint main(void){return printf("A%%B\\n");}', 'A%B\n', [4], 0, 4, 0),
        ('long_count', '#include <stdio.h>\nint main(void){return printf("'+'abc'*100+'");}', 'abc'*100, [300], 0, 300, 0),
        ('null_flush', '#include <stdio.h>\nint main(void){printf("ok");return fflush(0);}', 'ok', [2], 1, 0, 0),
        ('unsupported', '#include <stdio.h>\nint main(void){return printf("%q",7);}', '?', [-1], 0, -1, 1),
    ]
    for name, source, text, returns, flushes, value, error in cases:
        _, rom, labels = support.compile_case(name,source,console=True)
        report[name] = emulate(name,rom,labels,text,returns,flushes,value,error)
        if not error:
            host = native(name,source)
            # Windows text output translates LF to CRLF; text=True normalizes it
            assert host.returncode & 0xffff == value & 0xffff
            assert host.stdout == text.replace('\r','\n')
    # Target ABI fixtures: explicit expected text, with no host printf involved
    formats = [
        ('integers', '"%d %d %u %ld %ld %lu %c",(int)-32768,32767,65535U,-2147483647L-1L,2147483647L,4294967295UL,\'Z\'',
         '-32768 32767 65535 -2147483648 2147483647 4294967295 Z', ''),
        ('padding', '"[%06d][%-6d][%6.4u][%.0u][%ld]",-42,42,7U,0U,0L',
         '[-00042][42    ][  0007][][0]', ''),
        ('strings', '"[%8.3s][%-5s][%S]%d",ram,ram,"ROM",19',
         '[     abc][abcde][ROM]19', 'char ram[6];ram[0]=97;ram[1]=98;ram[2]=99;ram[3]=100;ram[4]=101;ram[5]=0;'),
        ('empty', '"[%4.0s][%.0d][%5c][%%]",ram,0,\'X\'',
         '[    ][][    X][%]', 'char ram[1];ram[0]=0;'),
    ]
    for name, args, text, setup in formats:
        source = '#include <stdio.h>\nint main(void){'+setup+'return printf('+args+');}'
        _, rom, labels = support.compile_case(name,source,console=True)
        report[name] = emulate(name,rom,labels,text,[len(text)],0,len(text))
    floats = [
        ('fixed', '"[%6.1f][%.0f][%.0f][%.2f][%.2f][%08.1f]%d",12.25,2.5,3.5,0.009,9.999,-1.25,17',
         '[  12.2][2][4][0.01][10.00][-00001.2]17'),
        ('general', '"[%g][%.8g][%.1f][%.1f]",30.0,1.2345678,1e20,-0.0',
         '[30][1.2345678][100000000000000000000.0][-0.0]'),
    ]
    extra=[ROOT/f'build/{n}.o' for n in ('arithmetic','integers','ieee_engine','tables','io','decimal')]
    for name,args,text in floats:
        source='#include <stdio.h>\nint main(void){return printf('+args+');}'
        _,rom,labels=support.compile_case(name,source,console=True,console_object='float_console',extra_objects=extra)
        report[name]=emulate(name,rom,labels,text,[len(text)],0,len(text))
    source='''#include <stdio.h>
int main(void){
*(char * __far)0x7effffUL='A';*(char * __far)0x7f0000UL='B';*(char * __far)0x7f0001UL=0;
printf("%S/%d",(char * __far)0x7effffUL,7);
*(char * __far)0x7effffUL='%';*(char * __far)0x7f0000UL='d';
return printf((char * __far)0x7effffUL,9);
}'''
    _,rom,labels=support.compile_case('format_banks',source,console=True)
    report['format_banks']=emulate('format_banks',rom,labels,'AB/79',[4,1],0,1)
    text = ''.join(chr(65 + i % 26) + '\n' for i in range(70))
    literal = text.replace('\n','\\n')
    source = '#include <stdio.h>\nint main(void){printf("' + literal + '");return fflush(stdout);}'
    _, rom, labels = support.compile_case('scroll',source,console=True)
    report['scroll'] = emulate('scroll',rom,labels,text,[len(text)],1,0,screenshot=True)
    host = native('scroll',source)
    assert host.returncode == 0 and host.stdout == text
    # Distinct adjacent glyphs, automatic wrap and a complete circular-map wrap
    for name,count in [('columns',193),('full_page',1791),('full_ring',4517)]:
        text=''.join(chr(33+i%94) for i in range(count))
        chunks=[text[i:i+200] for i in range(0,len(text),200)]
        source='#include <stdio.h>\nint main(void){'+'\n'.join('printf('+json.dumps(chunk.replace('%','%%'))+');' for chunk in chunks)+'return fflush(stdout);}'
        _,rom,labels=support.compile_case(name,source,console=True)
        report[name]=emulate(name,rom,labels,text,list(map(len,chunks)),1,0,screenshot=True)
    stub = OUT / 'abi_helpers.o'
    support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',stub,ROOT/'tests/abi_helpers.s'])
    for name, source in [
        ('three_arguments','int abi_probe(int,int,int); int main(void){return abi_probe(17,23,42);}'),
        ('nested_arguments','int abi_probe(int,int,int);int abi_first(void);int abi_second(void);int abi_third(void);int main(void){return abi_probe(abi_first(),abi_second(),abi_third());}')
    ]:
        _, rom, labels = support.compile_case(name,source,extra_objects=[stub])
        report[name] = support.emulate(rom,labels,82)
    source = 'char abi_char(void);int abi_promoted(int);int main(void){return abi_promoted(abi_char());}'
    _, rom, labels = support.compile_case('char_promotion',source,extra_objects=[stub])
    report['char_promotion'] = support.emulate(rom,labels,65)
    source = '#include <stdio.h>\nint abi_tick(void);int main(void){while(abi_tick()){printf(".");}return fflush(stdout);}'
    _, rom, labels = support.compile_case('dynamic_condition',source,console=True,extra_objects=[stub])
    report['dynamic_condition'] = emulate('dynamic_condition',rom,labels,'...',[1,1,1],1,0)
    host = native('dynamic_condition','int abi_tick(void){static int n;return n++<3;}\n'+source)
    assert host.returncode == 0 and host.stdout == '...'
    failures = [
        '#include <stdio.h>\nint main(void){fflush("> ");}',
        '#include <stdio.h>\nint main(void){printf();}',
        '#include <stdio.h>\nint main(void){fflush(stdout,1);}',
        'int main(void){return undeclared;}',
        '#include <stdio.h>\nint printf(int);\nint main(void){}',
        '#include <stdio.h>\nint main(void){printf("unterminated);}',
        '#include <missing.h>\nint main(void){}',
        '#ifdef BROKEN\nint main(void){}',
        'int probe(); int probe(int); int main(void){return probe();}',
        'int main(void){}\x00ignored',
        'int main(void){main();}',
    ]
    for i, source in enumerate(failures):
        path = OUT / f'bad_{i}.c'; path.write_text(source)
        result = subprocess.run([str(ROOT / 'build/zicc.exe'),str(path),'-o',str(OUT/'bad.s')],capture_output=True,text=True)
        assert result.returncode and re.search(r':\d+:\d+: error:',result.stderr), result.stderr
    report['rejected_sources'] = len(failures)
    report['presentation'] = support.run([sys.executable,ROOT/'tests/check-console.py'],timeout=120).stdout
    (OUT / 'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: visible prompt, ABI, ROM font/palette, NMI dirty-row DMA, circular scrolling, NTSC/PAL deadlines, MSVC references, and frontend diagnostics')


if __name__ == '__main__': main()
