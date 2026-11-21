"""Give the integer routines inputs at run time. Check the results, calling rules and wait time for hardware math."""
import os
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'integer-check'
sys.path.insert(0, str(ROOT / 'tools'))
from mesen_core import Core

spec = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def vectors():
    pairs = [(a, b) for b in range(1, 256) for a in
             (0, 255, 65535, 65536, 0x12345678, 0xffffffff)]
    pairs += [(a, b) for a in (0, 1, 255, 65535, 65536, 0x7fffffff, 0x80000000, 0xffffffff)
              for b in (256, 257, 0x1234, 65535, 65536, 0x7fffffff, 0x80000000, 0xffffffff)]
    rng = random.Random(65816)
    pairs += [(rng.getrandbits(32), rng.randrange(1, 1 << 32)) for _ in range(512)]
    # Word divisors above 255 take the 16-bit-remainder software loop; the
    # dividend's high word against the divisor selects 16 or 32 steps, and
    # divisors above $8000 exercise the remainder's shifted-out 17th bit
    words = random.Random(32816)
    for b in (256, 257, 0x1234, 0x7fff, 0x8000, 0x8001, 0xfffe, 0xffff,
              *(words.randrange(256, 65536) for _ in range(24))):
        for high in (0, 1, b - 2, b - 1, b, b + 1, 0xffff):
            if 0 <= high <= 0xffff:
                pairs += [((high << 16) | low, b) for low in (0, b - 1, 0xffff, words.getrandbits(16))]
    pairs += [(words.getrandbits(32), 1 << 16 | words.getrandbits(16)) for _ in range(64)]
    result = []
    for a, b in pairs:
        result.append((0, a, b, (a * b) & 0xffffffff, a // b, a % b))
        sa = a if a < 0x80000000 else a - (1 << 32)
        sb = b if b < 0x80000000 else b - (1 << 32)
        if not (sa == -0x80000000 and sb == -1):
            q = abs(sa) // abs(sb)
            if (sa < 0) != (sb < 0):
                q = -q
            result.append((1, a, b, (a * b) & 0xffffffff, q & 0xffffffff, (sa - q * sb) & 0xffffffff))
    # Negative small divisors exercise signed magnitudes and remainder signs
    for a in (-0x80000000, -1234567, -65536, -1, 0, 1, 1234567, 0x7fffffff):
        for b in (-255, -97, -1, 1, 97, 255):
            if a == -0x80000000 and b == -1:
                continue
            q = abs(a) // abs(b) * (-1 if (a < 0) != (b < 0) else 1)
            result.append((1, a & 0xffffffff, b & 0xffffffff, (a * b) & 0xffffffff,
                           q & 0xffffffff, (a - q * b) & 0xffffffff))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    support.OUT = OUT
    cases = vectors()
    cases += [(mode + 2, a, b, p, q, r) for mode, a, b, p, q, r in cases
              if a in (0, 65535, 65536, 0x12345678, 0x80000000, 0xffffffff)
              and b in (1, 255, 256, 65537, 0x80000000, 0xffffffff)]
    expected_multiplies = sum(4 if b <= 255 else 10 for _, _, b, _, _, _ in cases)
    expected_divides = expected_remainder_reads = 0
    for mode, a, b, _, _, _ in cases:
        if mode & 1:
            a = abs(a if a < 0x80000000 else a - (1 << 32))
            b = abs(b if b < 0x80000000 else b - (1 << 32))
        if b <= 255:
            divisions = 1 if a <= 65535 else 2 if a >> 16 < b else 3
            expected_divides += divisions
            expected_remainder_reads += divisions - (1 if mode & 2 else 0)
    source = '''unsigned long a,b,p,q,r; unsigned int mode;
__noinline unsigned long unsigned_quotient(void) { return a/b; }
__noinline long signed_quotient(void) { return (long)a/(long)b; }
int check(void) {
    if (a*b!=p) return 1;
    if (mode & 2) return (mode & 1) ? signed_quotient()!=(long)q : unsigned_quotient()!=q;
    if (mode) {
        if ((long)a/(long)b!=(long)q) return 2;
        if ((long)a%(long)b!=(long)r) return 3;
    } else {
        if (a/b!=q) return 4;
        if (a%b!=r) return 5;
    }
    return 0;
}
int main(void) { int i; for(i=0;i<COUNT;i++) { if(check()) return i+1; } return 0; }
'''.replace('COUNT', str(len(cases)))
    # Reserve scratch without linking the unrelated floating kernels
    workspace = OUT / 'workspace.s'
    workspace.write_text('.exportzp __arith_lhs, __arith_rhs\n.segment "DP_SCRATCH": zeropage\n'
                         '__arith_lhs: .res 4\n__arith_rhs: .res 28\n', encoding='ascii')
    support.run([support.CC65 / 'ca65.exe', '-o', OUT / 'workspace.o', workspace])
    _, rom, labels = support.compile_case('hardware', source,
                                          extra_objects=(OUT / 'workspace.o', ROOT / 'build/integers.o'))
    rows = ',\n'.join('{' + ','.join(map(str, row)) + '}' for row in cases)
    script = f'''local cases={{{rows}}}
local index=0
local start=0
local writes_mul,writes_div,remainder_reads=0,0,0
local trigger,kind=0,''
local min_mul,min_div=1000000,1000000
local function word(address,v)
 emu.write(((address)&0x1ffff),v&255,emu.memType.snesWorkRam)
 emu.write(((address+1)&0x1ffff),(v>>8)&255,emu.memType.snesWorkRam)
end
local function long(address,v) word(address,v);word(address+2,v>>16) end
emu.addMemoryCallback(function()
 index=index+1
 local c=cases[index]
 if not c then error('extra kernel call') end
 word({labels['mode']},c[1])
 long({labels['a']},c[2]);long({labels['b']},c[3]);long({labels['p']},c[4])
 long({labels['q']},c[5]);long({labels['r']},c[6])
end,emu.callbackType.exec,{labels['check']},{labels['check']})
emu.addMemoryCallback(function() start=emu.getState().masterClock end,emu.callbackType.exec,{labels['main']},{labels['main']})
emu.addMemoryCallback(function()
 writes_mul=writes_mul+1;trigger=emu.getState().masterClock;kind='mul'
end,emu.callbackType.write,0x004203,0x004203)
emu.addMemoryCallback(function()
 writes_div=writes_div+1;trigger=emu.getState().masterClock;kind='div'
end,emu.callbackType.write,0x004206,0x004206)
emu.addMemoryCallback(function(address)
 local elapsed=emu.getState().masterClock-trigger
 if kind=='mul' then
  if elapsed<48 then error('early multiply read '..elapsed) end
  min_mul=math.min(min_mul,elapsed)
 elseif kind=='div' then
  if address==0x004216 then remainder_reads=remainder_reads+1 end
  if elapsed<96 then error('early divide read '..elapsed) end
  min_div=math.min(min_div,elapsed)
 end
end,emu.callbackType.read,0x004214,0x004217)
emu.addMemoryCallback(function()
 local s=emu.getState()
 if s['cpu.a']~=0 then error('case '..index..' returned '..s['cpu.a']) end
 if index~=#cases then error('case count') end
 if s['cpu.sp']~=0x04ff or s['cpu.y']~=0 or s['cpu.d']~=0 or s['cpu.dbr']~=0x7e or (s['cpu.ps']&0x38)~=0 then error('ABI') end
 if writes_mul~={expected_multiplies} or writes_div~={expected_divides} then error('unexpected hardware operation count; divmod not reused') end
 if remainder_reads~={expected_remainder_reads} then error('unexpected divider remainder reads '..remainder_reads) end
 emu.log('PASS '..index..' cases MUL '..writes_mul..' DIV '..writes_div..' MIN '..min_mul..' '..min_div)
 emu.log('CLOCKS '..(s.masterClock-start));emu.log('DONE');emu.breakExecution()
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
    scriptfile = OUT / 'hardware.lua'
    scriptfile.write_text(script, encoding='ascii')
    core = Core(OUT / 'emulator')
    try:
        core.load(rom, scriptfile, script)
        core.start()
        # The hardware-thread queue can more than double wall time under load;
        # retain every vector, emulated operation and assertion at 20 workers
        log = core.wait_for('DONE', 60)
    finally:
        core.close()
    assert 'PASS' in log, log
    report = dict(cases=len(cases), seed=65816, log=log,
                  master_clocks=int(re.search(r'CLOCKS (\d+)', log)[1]))
    (OUT / 'hardware-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(re.search(r'PASS[^\r\n]*', log)[0])


if __name__ == '__main__':
    main()
