"""Validate region detection, frame ticks, snapshot races and NMI state preservation."""
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
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'time-check'
sys.path.insert(0, str(ROOT / 'tools'))
from mesen_core import Core, SnesConfig

SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)
support.OUT = OUT
MODES = ('rate-first', 'clock-first', 'carry', 'wrap', 'race-low', 'race-verify',
         'race-wrap-low', 'race-wrap-verify', 'nmi-abi')


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    helper = OUT / 'clock_helpers.o'
    support.run([support.CC65 / 'ca65.exe', '--cpu', '65816', '-g', '-o', helper,
                 ROOT / 'tests/clock_helpers.s'])
    for name in ('rate-first', 'clock-first'):
        init = ('begin = clock(); rate = CLOCKS_PER_SEC;' if name == 'clock-first'
                else 'rate = CLOCKS_PER_SEC; begin = clock();')
        source = '''#include <time.h>
void enable_nmi(void);
clock_t begin, end, elapsed, rate;
int main(void) {
    if (sizeof(clock_t) != 4) return 1;
    ''' + init + '''
    enable_nmi();
    do { end = clock(); elapsed = end - begin; } while (elapsed < rate * 2UL);
    return 0;
}
'''
        support.compile_case(name, source, extra_objects=[helper, *[ROOT / 'build' / (n+'.o')
                             for n in ('arithmetic', 'integers', 'ieee_engine', 'tables')]])
    for name, probe in (('clock-probe', 'clock_probe'), ('nmi-probe', 'nmi_probe')):
        support.compile_case(name, '#include <time.h>\nvoid enable_nmi(void);\nint ' + probe + '(void);\n'
                             'clock_t rate; int main(void){rate=CLOCKS_PER_SEC;enable_nmi();return '
                             + probe + '();}\n', extra_objects=[helper])


def labels(stem):
    return {n.removeprefix('_'): int(a, 16) for a, n in re.findall(
        r'^al ([0-9a-fA-F]+) \.(\S+)$', stem.with_suffix('.labels').read_text(), re.M)}


def worker(region, mode):
    name = mode if mode in ('rate-first', 'clock-first') else ('nmi-probe' if mode == 'nmi-abi' else 'clock-probe')
    stem = OUT / name
    sy = labels(stem)
    home = OUT / region / mode
    home.mkdir(parents=True, exist_ok=True)
    rate = 60 if region == 'ntsc' else 50
    normal = mode in ('rate-first', 'clock-first')
    race = mode.startswith('race-')
    seed = 0xffffffff if 'wrap' in mode else 0xffff
    script = f'''
local nmis, frames, samples, retries = 0, 0, 0, 0
local last_nmi, min_period, max_period = nil, 999999999, 0
local last_sample, last_frame, initialized = nil, nil, false
local seeded, paused, pending_clock, resume_target = false, false, nil, nil
local registered, stat78 = {{}}, nil
local region_reads, acknowledgements, irq_reads = 0, 0, 0
local snapshots = {{}}
local function word(a) return emu.read16(((a)&0x1ffff),emu.memType.snesWorkRam,false) end
local function long(a) return word(a)|(word(a+2)<<16) end
local function write_long(a,v)
 for i=0,3 do emu.write(((a+i)&0x1ffff),(v>>(8*i))&255,emu.memType.snesWorkRam) end
end
local function require_value(ok,msg) if not ok then error(msg) end end
local function redirect(a)
 local s=emu.getState();s['cpu.pc']=a&65535;s['cpu.k']=a>>16;emu.setState(s)
end
emu.addMemoryCallback(function(address,v) stat78=v;region_reads=region_reads+1 end,emu.callbackType.read,0x213f)
emu.addMemoryCallback(function() acknowledgements=acknowledgements+1 end,emu.callbackType.read,0x4210)
emu.addMemoryCallback(function() irq_reads=irq_reads+1 end,emu.callbackType.read,0x4211)
emu.addMemoryCallback(function(address,v)
 if v~=0 then
  require_value(v==128,'unexpected interrupt source enabled')
  require_value(not initialized,'timer enabled more than once');initialized=true
 end
end,emu.callbackType.write,0x4200)
emu.addMemoryCallback(function()
 nmis=nmis+1
 local now=emu.getState().masterClock
 if last_nmi then
  local period=now-last_nmi;min_period=math.min(min_period,period);max_period=math.max(max_period,period)
 end
 last_nmi=now
end,emu.callbackType.exec,{sy['nmi_wrapper']},{sy['nmi_wrapper']})
emu.addEventCallback(function()
 if initialized then
  local count=long({sy['clock_frames']})
  if {str(normal).lower()} and last_frame then require_value(count-last_frame==1,'frame tick delta '..(count-last_frame)..' nmis='..nmis..' frames='..frames..' ticks='..count) end
  last_frame=count;frames=frames+1
 end
end,emu.eventType.endFrame)
emu.addMemoryCallback(function()
 local s=emu.getState()
 require_value(s['cpu.d']==0 and s['cpu.dbr']==126,'clock entry ABI')
 local target=0x800000|((word(s['cpu.sp']+1)+1)&65535)
 if not pending_clock then
  pending_clock={{target=target,sp=s['cpu.sp'],y=s['cpu.y']}}
  if not registered[target] then
   registered[target]=true
   emu.addMemoryCallback(function()
    if not pending_clock or pending_clock.target~=target then return end
    local after=emu.getState();local v=after['cpu.a']|(after['cpu.x']<<16)
    require_value(after['cpu.sp']==pending_clock.sp+2,'clock stack balance')
    require_value(after['cpu.y']==pending_clock.y and after['cpu.d']==0 and after['cpu.dbr']==126,'clock preserved ABI')
    require_value((after['cpu.ps']&0x3c)==4,'clock return widths/decimal/IRQ flags')
    if {str(normal).lower()} then
     local current=long({sy['clock_frames']})
     require_value(v==current or v==((current-1)&0xffffffff),'torn clock return')
     if last_sample then require_value(v>=last_sample,'clock went backwards') end
     last_sample=v
    end
    samples=samples+1;pending_clock=nil
   end,emu.callbackType.exec,target,target)
  end
 end
end,emu.callbackType.exec,{sy['clock']},{sy['clock']})
'''
    if not normal and mode != 'nmi-abi':
        script += f'''
emu.addMemoryCallback(function()
 if not seeded then write_long({sy['clock_frames']},{seed});seeded=true end
 retries=retries+1
end,emu.callbackType.exec,{sy['clock_snapshot']},{sy['clock_snapshot']})
'''
        if race:
            target = sy['clock_snapshot_verify'] if 'verify' in mode else sy['clock_snapshot_low']
            script += f'''
emu.addMemoryCallback(function()
 if not paused then paused=true;resume_target={target};redirect({sy['clock_pause']}) end
end,emu.callbackType.exec,{target},{target})
emu.addMemoryCallback(function()
 require_value(nmis==1,'race did not use exactly one real NMI');redirect(resume_target)
end,emu.callbackType.exec,{sy['clock_pause_resume']},{sy['clock_pause_resume']})
'''
        else:
            # Carry and full wrap are checked by reading after one natural NMI
            script += f'''
emu.addMemoryCallback(function()
 if not paused then paused=true;resume_target={sy['clock_snapshot']};redirect({sy['clock_pause']}) end
end,emu.callbackType.exec,{sy['clock_snapshot_low']},{sy['clock_snapshot_low']})
emu.addMemoryCallback(function() redirect(resume_target) end,emu.callbackType.exec,{sy['clock_pause_resume']},{sy['clock_pause_resume']})
'''
    if mode == 'nmi-abi':
        for variant in ('16', 'a8', '8', 'x8'):
            script += f'''
emu.addMemoryCallback(function()
 local s=emu.getState();snapshots['{variant}']={{state=s,count=long({sy['clock_frames']})}}
 for i=0x02,0x21 do emu.write(((i)&0x1ffff),(i*37)&255,emu.memType.snesWorkRam) end
end,emu.callbackType.exec,{sy['clock_wait_'+variant]},{sy['clock_wait_'+variant]})
emu.addMemoryCallback(function()
 local before=snapshots['{variant}'];local after=emu.getState()
 for _,k in ipairs({{'a','x','y','d','dbr','sp','ps'}}) do
  require_value(before.state['cpu.'..k]==after['cpu.'..k],'NMI {variant} changed '..k)
 end
 require_value(long({sy['clock_frames']})==before.count+1,'NMI {variant} tick')
 for i=0x02,0x21 do require_value(emu.read(((i)&0x1ffff),emu.memType.snesWorkRam,false)==((i*37)&255),'NMI changed arithmetic scratch') end
 snapshots['{variant}'].passed=true
end,emu.callbackType.exec,{sy['clock_after_'+variant]},{sy['clock_after_'+variant]})
'''
    script += f'''
emu.addMemoryCallback(function()
 local s=emu.getState()
 require_value(s['cpu.a']==0 and s['cpu.sp']==1279,'main result/stack')
 require_value(long({sy['rate']})=={rate},'CLOCKS_PER_SEC wrong region')
 require_value(stat78 and (stat78&16)=={16 if region == 'pal' else 0},'hardware region wrong')
 require_value(region_reads==1,'region detection not cached')
 require_value(acknowledgements==1 and irq_reads==0,'unexpected handler RDNMI/TIMEUP read')
'''
    if normal:
        expected_period = 262 * 1364 if region == 'ntsc' else 312 * 1364
        script += f'''
 require_value(long({sy['elapsed']})=={rate*2},'two-second elapsed ticks')
 require_value(nmis==long({sy['clock_frames']}) and nmis=={rate*2},'NMI/tick count')
 require_value(min_period>={expected_period-128} and max_period<={expected_period+128},'physical frame period')
'''
    elif mode == 'nmi-abi':
        script += " for _,v in pairs(snapshots) do require_value(v.passed,'incomplete NMI ABI check') end\n require_value(nmis==4,'four NMI ABI cases')\n"
    else:
        script += f" require_value(long({sy['clock_result']})=={(seed+1)&0xffffffff},'carry/wrap snapshot')\n require_value(nmis==1,'one rollover NMI')\n"
        if race:
            script += " require_value(retries==2,'torn snapshot did not retry exactly once')\n"
    script += " emu.log('PASS nmis='..nmis..' frames='..frames..' samples='..samples..' retries='..retries..' period='..min_period..'..'..max_period);emu.breakExecution()\nend,emu.callbackType.exec," + str(sy['main_exit']) + ',' + str(sy['main_exit']) + ')\n'
    lua = home / 'check.lua'; lua.write_text(script)
    core = Core(home)
    try:
        config = SnesConfig()
        config.Region = 1 if region == 'ntsc' else 2
        config.Port1.Type = 1; config.DisableFrameSkipping = True
        config.RamPowerOnState = 1; config.GsuClockSpeed = 100; config.BsxCustomDate = -1
        for i in range(8): config.ChannelVolumes[i] = 100
        core.bind('SetSnesConfig', None, SnesConfig)(config)
        core.load(stem.with_suffix('.sfc'), lua, script); core.start()
        log = core.wait_for('PASS', 30)
        print(region, mode, log.splitlines()[-1], flush=True)
    finally:
        core.close_with_log(home / 'check.log')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', choices=('ntsc', 'pal'))
    parser.add_argument('--mode', choices=MODES)
    args = parser.parse_args()
    if bool(args.region) != bool(args.mode):
        parser.error('--region and --mode must be supplied together')
    if args.region:
        worker(args.region, args.mode); return
    build()
    for region in ('ntsc', 'pal'):
        for mode in MODES:
            result = subprocess.run([sys.executable, __file__, '--region', region, '--mode', mode],
                                    cwd=ROOT, env=dict(os.environ, ZICC_LOGS_DIR=str(OUT.parent)),
                                    capture_output=True, text=True, timeout=60,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            assert result.returncode == 0, result.stdout + result.stderr
            print(result.stdout.strip(), flush=True)
    paths = [ROOT / 'include/time.h', ROOT / 'runtime/nmi.s', ROOT / 'runtime/clock.s', ROOT / 'runtime/clock_rate.s', ROOT / 'runtime/startup.s',
             ROOT / 'build/zicc.exe', ROOT / 'build/nmi.o']
    report = dict(regions=['ntsc', 'pal'], modes=list(MODES), cases=2*len(MODES),
                  sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (OUT / 'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print('PASS: 18 NTSC/PAL clock/frame/rollover/race/NMI-ABI cases')


if __name__ == '__main__': main()
