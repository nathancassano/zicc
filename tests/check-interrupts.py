"""Native vectors and optional NMI composition with real NTSC/PAL delivery."""
import os
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'interrupt-check'
sys.path.insert(0, str(ROOT / 'tools'))
from mesen_core import Core, SnesConfig
SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT
KINDS = ('nmi', 'irq', 'brk', 'cop')
NAMES = ('vblank', 'raster', 'software_break', 'supervisor')
OFFSETS = (0x7fea, 0x7fee, 0x7fe6, 0x7fe4)
COMBINATIONS = [(mask, timer) for mask in range(16) for timer in (0, 1)] + [(0, 2), (1, 2)]


def run(command, timeout=30):
    return subprocess.run(list(map(str, command)), cwd=ROOT, capture_output=True, text=True,
                          timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)


def labels(stem):
    return {n.removeprefix('_'): int(a, 16) for a, n in re.findall(
        r'^al ([0-9a-fA-F]+) \.(\S+)$', stem.with_suffix('.labels').read_text(), re.M)}


def driver(mask, timer):
    lines = ['.setcpu "65816"', '.a16', '.i16', '.export _test_driver',
             '.segment "BSS"', 'clock_before: .res 4', 'clock_after: .res 4',
             '.segment "CODE"', '_test_driver:', 'phy']
    if timer == 1:
        lines += ['.import _clock', 'jsr .loword(_clock)', 'sta a:clock_before', 'stx a:clock_before+2']
    for kind in ('brk', 'cop', 'irq', 'nmi'):
        if kind == 'irq' and not mask & 2: continue
        if kind == 'nmi' and not (mask & 1 or timer == 1): continue
        for variant in (range(4) if mask == 15 else range(1)):
            if kind == 'irq':
                lines += ['sep #$20', '.a8', f'wait_vblank_{kind}_{variant}:', 'lda f:$004212',
                          'and #$80', f'beq wait_vblank_{kind}_{variant}',
                          'lda f:$004211', 'lda #1', 'sta f:$004209', 'lda #0', 'sta f:$00420a',
                          'lda #$20', 'sta f:$004200', 'rep #$20', '.a16', 'cli']
            if kind == 'nmi':
                lines += ['sep #$20', '.a8', 'lda #0', 'sta f:$004300', 'sta f:$004302', 'sta f:$004303',
                          'lda #$18', 'sta f:$004301', 'lda #$7e', 'sta f:$004304',
                          'lda f:$004210', 'lda #$80', 'sta f:$004200',
                          'rep #$20', '.a16']
            lines += ['lda #$3456', 'tcd', 'sep #$20', '.a8', 'lda #$7e', 'pha', 'plb',
                      'rep #$20', '.a16', 'ldx #$abcd', 'ldy #$5a3c', 'lda #$1234', 'cld', 'sec']
            if variant & 1: lines += ['sep #$20', '.a8']
            if variant & 2: lines += ['sep #$10', '.i8']
            lines += [f'before_{kind}_{variant}:']
            lines += [f'.byte ${"00" if kind == "brk" else "02"},$73'] if kind in ('brk', 'cop') else ['wai']
            lines += [f'after_{kind}_{variant}:', 'rep #$30', '.a16', '.i16', 'sei',
                      'lda #0', 'tcd', 'sep #$20', '.a8', 'lda #$7e', 'pha', 'plb', 'rep #$20', '.a16']
            if kind in ('irq', 'nmi'):
                lines += ['sep #$20', '.a8']
                if kind == 'nmi': lines += ['lda f:$004210']
                lines += ['lda #0', 'sta f:$004200', 'rep #$20', '.a16']
    if timer == 1: lines += ['jsr .loword(_clock)', 'sta a:clock_after', 'stx a:clock_after+2']
    return '\n'.join(lines + ['ply', 'lda #0', 'rts']) + '\n'


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    for mask, timer in COMBINATIONS:
        name = f'handlers-{mask:02d}-clock-{timer}'
        helper = OUT / (name + '-driver.s'); helper.write_text(driver(mask, timer))
        obj = helper.with_suffix('.o')
        support.run([support.CC65/'ca65.exe', '--cpu', '65816', '-g', '-o', obj, helper])
        source = '#include <time.h>\nunsigned int counts[4], irq_status;\nunsigned long wide, rate;\nint test_driver(void);\n'
        for i, (kind, function) in enumerate(zip(KINDS, NAMES)):
            if not mask & (1 << i): continue
            source += f'__interrupt({kind}) void {function}(void){{\nunsigned int local;unsigned int * __far selected=counts+{i}; local=*selected; *selected=local+1;\n'
            if kind == 'irq': source += 'irq_status=*(unsigned char * __far)0x4211UL;\n'
            if kind == 'nmi': source += '*(unsigned int * __far)0x4305UL=2; *(unsigned char * __far)0x420bUL=1;\n'
            source += f'if(counts[{i}]&1) return;\nwide=(wide<<(counts[{i}]&7))+0x10001UL;\n}}\n'
        source += 'int main(void){' + ('rate=CLOCKS_PER_SEC;' if timer else '') + 'return test_driver();}\n'
        support.compile_case(name, source, extra_objects=[obj, *[ROOT/'build'/(n+'.o')
                             for n in ('arithmetic', 'integers', 'ieee_engine', 'tables')]])
        sy = labels(OUT/name); rom = (OUT/(name+'.sfc')).read_bytes()
        for i, offset in enumerate(OFFSETS):
            expected = sy[NAMES[i]] if mask & (1 << i) else (sy['nmi_entry'] if i == 0 and timer == 1 else sy['unused_interrupt'])
            assert int.from_bytes(rom[offset:offset+2], 'little') == expected & 65535, (name, KINDS[i])
        assert ('clock_frames' in sy) == (timer == 1), name
        assert ('nmi_entry' in sy) == bool(timer == 1 and not mask & 1), name
    invalid = {
        'unknown': '__interrupt(abort) void f(void){}',
        'parameters': '__interrupt(irq) void f(int x){}',
        'return_type': '__interrupt(brk) int f(void){return 1;}',
        'unspecified': '__interrupt(cop) void f(){}',
        'object': '__interrupt(nmi) int f;',
        'static': 'static __interrupt(nmi) void f(void){}',
        'struct_attribute': '__interrupt(nmi) struct S;',
        'inherited_static': 'static void f(void); __interrupt(nmi) void f(void){}',
        'late_static': '__interrupt(nmi) void f(void); static void f(void){}',
        'duplicate_attribute': '__interrupt(nmi) __interrupt(nmi) void f(void){}',
        'duplicate': '__interrupt(nmi) void f(void){} __interrupt(nmi) void g(void){}',
        'conflict': '__interrupt(irq) void f(void); __interrupt(brk) void f(void){}',
        'call': '__interrupt(nmi) void f(void){} int main(void){f();return 0;}',
        'earlier_call': 'void f(void);int main(void){f();return 0;} __interrupt(nmi) void f(void){}',
        'ordinary_call': 'void g(void);__interrupt(irq) void f(void){g();}',
        'return_value': '__interrupt(cop) void f(void){return 7;}',
        'hardware_helper': 'int a,b,c;__interrupt(irq) void f(void){c=a*b;}',
        'late_attribute': 'void f(void){} __interrupt(nmi) void f(void);',
    }
    for name, source in invalid.items():
        path = OUT/('bad-'+name+'.c'); path.write_text(source)
        result = run([ROOT/'build/zicc.exe', path, '-o', OUT/'invalid.s'])
        assert result.returncode and re.search(r':\d+:\d+: error:', result.stderr), (name, result.stderr)
    objects = []
    for name in ('first', 'second'):
        path = OUT/('duplicate-'+name+'.c'); path.write_text('__interrupt(nmi) void '+name+'(void){}\n')
        support.run([ROOT/'build/zicc.exe', path, '-o', path.with_suffix('.s')])
        support.run([support.CC65/'ca65.exe', '--cpu', '65816', '-o', path.with_suffix('.o'), path.with_suffix('.s')])
        objects.append(path.with_suffix('.o'))
    result = run([support.CC65/'ld65.exe', '-C', ROOT/'linker/lorom32.cfg', '-o', OUT/'invalid.raw', *objects])
    assert result.returncode and 'Duplicate external identifier' in result.stderr, result.stderr
    print('Built 34 combinations; rejected 18 malformed handlers and duplicate vector definitions', flush=True)


def worker(region, mask, timer):
    name = f'handlers-{mask:02d}-clock-{timer}'; stem = OUT/name; sy = labels(stem)
    home = OUT/region/name; home.mkdir(parents=True, exist_ok=True)
    script = f'''
local active, snapshot = nil, nil
local events={{nmi=0,irq=0,brk=0,cop=0}}
local rd,irqrd,enabled,dmas=0,0,false,0
local in_main=false
local function require_value(ok,msg) if not ok then error(msg) end end
local function word(a) return emu.read16(((a)&0x1ffff),emu.memType.snesWorkRam,false) end
local function long(a) return word(a)|(word(a+2)<<16) end
emu.addMemoryCallback(function(a,v) enabled=v~=0 end,emu.callbackType.write,0x4200)
local function check_rdnmi()
 if active then rd=rd+1;error('RDNMI read inside '..active) end
end
local function check_timeup()
 if active then require_value(active=='irq','TIMEUP read outside user IRQ');irqrd=irqrd+1 end
end
emu.addMemoryCallback(check_rdnmi,emu.callbackType.read,0x4210)
emu.addMemoryCallback(check_rdnmi,emu.callbackType.read,0x804210)
emu.addMemoryCallback(check_timeup,emu.callbackType.read,0x4211)
emu.addMemoryCallback(check_timeup,emu.callbackType.read,0x804211)
emu.addMemoryCallback(function() in_main=true end,emu.callbackType.exec,{sy['main']},{sy['main']})
emu.addMemoryCallback(function(a,v)
 if not in_main or v==0 then return end
 require_value(active=='nmi','unexpected DMA source');dmas=dmas+1
end,emu.callbackType.write,0x00420b)
'''
    if timer:
        script += f'''
emu.addMemoryCallback(function() require_value(not enabled,'time API enabled interrupts') end,
 emu.callbackType.exec,{sy['__clock_rate']},{sy['__clock_rate']})
'''
        if mask & 1 and timer == 1:
            script += f'''
emu.addMemoryCallback(function()
 if not enabled then return end
 require_value(active=='nmi','clock tick outside NMI')
 require_value(word({sy['counts']})==events.nmi,'library tick ran before user body')
 require_value(dmas==events.nmi,'library tick ran before user DMA')
end,emu.callbackType.write,{sy['clock_frames']},{sy['clock_frames']})
'''
    for i, kind in enumerate(KINDS):
        has = bool(mask & (1 << i)); present = has or kind == 'nmi' and timer == 1
        if present:
            address = sy[NAMES[i]] if has else sy['nmi_entry']
            script += f'''
emu.addMemoryCallback(function()
 require_value(active==nil,'unexpected nested interrupt');active='{kind}';events.{kind}=events.{kind}+1
end,emu.callbackType.exec,{address&65535},{address&65535})
'''
        for variant in (range(4) if mask == 15 else range(1)):
            before = f'before_{kind}_{variant}'; after = f'after_{kind}_{variant}'
            if before not in sy: continue
            expected = "'"+kind+"'" if present else 'nil'
            script += f'''
emu.addMemoryCallback(function()
 require_value(active==nil,'interrupt did not finish');snapshot=emu.getState()
 for i=0x02,0x21 do emu.write(((i)&0x1ffff),(i*37+{variant})&255,emu.memType.snesWorkRam) end
end,emu.callbackType.exec,{sy[before]},{sy[before]})
emu.addMemoryCallback(function()
 local s=emu.getState()
 for _,k in ipairs({{'a','x','y','d','dbr','sp','ps','k'}}) do
  require_value(s['cpu.'..k]==snapshot['cpu.'..k],'{kind}/{variant} failed to preserve '..k)
 end
 for i=0x02,0x21 do require_value(emu.read(((i)&0x1ffff),emu.memType.snesWorkRam,false)==((i*37+{variant})&255),'{kind} scratch corruption') end
 require_value(active=={expected},'{kind} vector entry not observed');active=nil
end,emu.callbackType.exec,{sy[after]},{sy[after]})
'''
    count = 4 if mask == 15 else 1
    script += f'''
emu.addMemoryCallback(function()
 local s=emu.getState();require_value(s['cpu.a']==0 and s['cpu.sp']==1279,'main result/stack')
 require_value(active==nil and rd==0,'handler acknowledgement')
 require_value(irqrd=={count if mask&2 else 0},'explicit user TIMEUP count')
 require_value(dmas=={count if mask&1 else 0},'user DMA count')
'''
    for i, kind in enumerate(KINDS):
        expected = count if mask & (1 << i) else 0
        entries = count if expected or kind == 'nmi' and timer == 1 else 0
        script += f" require_value(word({sy['counts']+i*2})=={expected},'{kind} user count')\n require_value(events.{kind}=={entries},'{kind} entry count')\n"
    if timer:
        script += f" require_value(long({sy['rate']})=={60 if region=='ntsc' else 50},'clock region')\n"
    if timer == 1:
        script += f" require_value(long({sy['clock_before']})==0 and long({sy['clock_after']})=={count},'clock library count')\n"
    script += " emu.log('PASS "+region+' '+name+"');emu.breakExecution()\nend,emu.callbackType.exec,"+str(sy['main_exit'])+','+str(sy['main_exit'])+')\n'
    lua = home/'check.lua'; lua.write_text(script); core = Core(home)
    try:
        config = SnesConfig(); config.Region = 1 if region == 'ntsc' else 2
        config.Port1.Type = 1; config.DisableFrameSkipping = True; config.RamPowerOnState = 1
        config.GsuClockSpeed = 100; config.BsxCustomDate = -1
        for i in range(8): config.ChannelVolumes[i] = 100
        core.bind('SetSnesConfig', None, SnesConfig)(config)
        core.load(stem.with_suffix('.sfc'), lua, script); core.start(); core.wait_for('PASS', 20)
    finally:
        core.close_with_log(home/'check.log')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', choices=('ntsc', 'pal')); parser.add_argument('--mask', type=int)
    parser.add_argument('--timer', type=int, choices=(0, 1, 2)); args = parser.parse_args()
    if args.region:
        worker(args.region, args.mask, args.timer); return
    build()
    for region in ('ntsc', 'pal'):
        for mask, timer in COMBINATIONS:
            result = run([sys.executable, __file__, '--region', region, '--mask', mask, '--timer', timer], timeout=40)
            assert result.returncode == 0, (region, mask, timer, result.stdout+result.stderr)
        print('PASS '+region+': all 34 attribute/library combinations', flush=True)
    files = [ROOT/p for p in ('src/main.c', 'src/parser.inc', 'src/codegen/codegen.inc', 'src/relax.c', 'runtime/nmi.s',
                              'runtime/clock.s', 'runtime/clock_rate.s', 'runtime/vectors.s', 'linker/lorom32.cfg', 'build/zicc.exe', 'build/nmi.o')]
    (OUT/'results.json').write_text(json.dumps(dict(cases=68, negative_cases=19,
        sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}), indent=2)+'\n')
    print('PASS: 68 NTSC/PAL combinations, native vectors, DMA ordering, explicit enables, returns, scratch and ABI preservation')


if __name__ == '__main__': main()
