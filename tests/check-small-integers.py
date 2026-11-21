"""Test all byte inputs and a range of word dividends. Check arithmetic results, hardware timing and calling rules."""
import os
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from mesen_core import Core
SPEC = importlib.util.spec_from_file_location('support', ROOT / 'tests/check-compiler.py')
support = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(support)


def quotient(a, b):
    return abs(a) // abs(b) * (-1 if (a < 0) != (b < 0) else 1)


def vectors(kind):
    if kind != 'word':
        pairs = [(a, b) for a in range(256) for b in range(256)]
    else:
        divisors = (1, 3, 7, 127, 255, 256, 257, 32767, 32768, 65535)
        pairs = [(a, divisors[a % len(divisors)]) for a in range(65536)]
        edges = (0, 1, 2, 127, 128, 255, 256, 257, 32767, 32768, 32769, 65534, 65535)
        pairs += [(a, b) for a in edges for b in edges]
        rng = random.Random(65816)
        pairs += [(rng.randrange(65536), rng.randrange(65536)) for _ in range(4096)]
    rows = []
    for a, b in pairs:
        if kind == 'signed-byte':
            sa = a if a < 128 else a - 256
            sb = b if b < 128 else b - 256
        else:
            sa = a if a < 32768 else a - 65536
            sb = b if b < 32768 else b - 65536
        valid = b != 0 and not (sa == -32768 and sb == -1)
        sq = quotient(sa, sb) if valid else 0
        uq, ur = (a // b, a % b) if b else (0, 0)
        product = sa * sb if kind == 'signed-byte' else a * b
        rows.append((a, b, product & 65535, uq, ur, sq & 65535,
                     (sa - sq * sb) & 65535 if valid else 0, int(valid)))
    return rows


def batch_plan(kind=None):
    plan = []
    for selected in (kind,) if kind else ('byte', 'signed-byte', 'word'):
        count = len(vectors(selected))
        for batch, first in enumerate(range(0, count, 4096)):
            plan.append(dict(kind=selected, batch=batch, cases=min(4096, count-first)))
    return plan


def collect_results(args, plan):
    report = {}
    compiler_hash = hashlib.sha256(args.compiler.read_bytes()).hexdigest()
    runtime_hash = hashlib.sha256(args.runtime_object.read_bytes()).hexdigest()
    for item in plan:
        kind, batch = item['kind'], item['batch']
        result = json.loads((args.output/kind/str(batch)/'results.json').read_text())
        assert result['cases'] == item['cases'], (kind, batch, 'case count')
        assert result['compiler_sha256'] == compiler_hash, (kind, batch, 'compiler')
        assert result['runtime_sha256'] == runtime_hash, (kind, batch, 'runtime')
        assert result['poisoned_high_words'] == args.expect_widths, (kind, batch, 'width assertions')
        group = report.setdefault(kind, dict(cases=0, batches=[]))
        group['cases'] += result['cases']
        group['batches'].append(result)
    (args.output/'results.json').write_text(json.dumps(report, indent=2)+'\n')


def worker(args):
    rows = vectors(args.worker)[args.batch*4096:(args.batch+1)*4096]
    out = args.output.resolve() / args.worker / str(args.batch)
    out.mkdir(parents=True, exist_ok=True)
    support.OUT = out
    original_run = support.run
    def run(command, **kw):
        command = list(command)
        if Path(command[0]) == ROOT / 'build/zicc.exe':
            command[0] = args.compiler.resolve()
        return original_run(command, **kw)
    support.run = run
    value_type = {'byte': 'unsigned char', 'signed-byte': 'signed char', 'word': 'unsigned int'}[args.worker]
    source = f'{value_type} a,b; unsigned int p,uq,ur,valid; int sq,sr;\n'
    source += 'int check(void){\n'
    if args.worker == 'signed-byte':
        source += 'if(a*b!=(int)p)return 1;if(valid){if(a/b!=sq)return 2;if(a%b!=sr)return 3;}\n'
    else:
        source += 'if((unsigned int)a*b!=p)return 1;if(b){if(a/b!=uq)return 2;if(a%b!=ur)return 3;}\n'
        if args.worker == 'word':
            source += 'if(valid){if((int)a/(int)b!=sq)return 4;if((int)a%(int)b!=sr)return 5;}\n'
    source += 'return 0;}\n'
    source += f'int main(void){{unsigned int i;for(i=0;;i++){{if(check())return 1;if(i=={len(rows)-1}U)break;}}return 0;}}\n'
    workspace = out / 'workspace.s'
    workspace.write_text('.exportzp __arith_lhs,__arith_rhs\n.segment "DP_SCRATCH": zeropage\n'
                         '__arith_lhs: .res 4\n__arith_rhs: .res 28\n')
    run([support.CC65 / 'ca65.exe', '-o', out / 'workspace.o', workspace])
    _, rom, labels = support.compile_case(args.worker, source,
        extra_objects=(out / 'workspace.o', args.runtime_object.resolve()))
    assembly = (out / (args.worker + '.s')).read_text()
    if args.expect_widths:
        required = {'byte': ('__mul8', '__udiv8'),
                    'signed-byte': ('__mul16', '__sdivmod16'),
                    'word': ('__mul16', '__udiv16', '__sdivmod16')}[args.worker]
        for name in required:
            assert '.import ' + name + '\n' in assembly, name
        assert not re.search(r'\.import __(?:mul|[su]div|[su]mod)32\b', assembly), assembly
    rows_text = ','.join('{' + ','.join(map(str, row)) + '}' for row in rows)
    addresses = [labels[n] for n in ('a','b','p','uq','ur','sq','sr','valid')]
    assignments = ''.join(f'{"byte" if i<2 and args.worker!="word" else "word"}({address},c[{i+1}]);'
                          for i,address in enumerate(addresses))
    if args.expect_widths:
        # Narrow helpers must not depend on zero-filled unused upper words
        assignments += f'word({labels["_arith_lhs"]+2},0xa55a~index);word({labels["_arith_rhs"]+2},0x5aa5~index);word({labels["_arith_lhs"]+10},0xc33c~index);'
    if not args.expect_widths:
        byte_limit = 127 if args.worker == 'signed-byte' else 255
        expected_mul = sum(4 if 'mul32_byte' in labels and b <= byte_limit else 10
                           for _,b,*_ in rows)
    elif args.worker != 'word':
        expected_mul = len(rows)
    else:
        expected_mul = sum(1 + (0 < a >> 8 < 255) + (0 < b >> 8 < 255) for a,b,*_ in rows)
    expected_div = 0
    for a,b,_,_,_,_,_,valid in rows:
        if args.worker == 'byte':
            expected_div += b != 0
        elif args.worker == 'signed-byte':
            expected_div += valid
        else:
            sb = b if b < 32768 else b-65536
            expected_div += int(0 < b <= 255) + int(valid and abs(sb) <= 255)
    script = f'''local cases={{{rows_text}}}
local index,muls,divs=0,0,0
local trigger,kind=0,''
local minmul,mindiv=1000000,1000000
local entry_sp,entry_y,start=0,0,0
local check_sp,check_y=nil,nil
local function byte(p,v) emu.write(((p)&0x1ffff),v&255,emu.memType.snesWorkRam) end
local function word(p,v) byte(p,v);byte(p+1,v>>8) end
emu.addMemoryCallback(function()
 index=index+1;local c=cases[index];if not c then error('extra case') end
 local s=emu.getState()
 if check_sp and check_sp~=s['cpu.sp'] then error('call ABI') end
 check_sp=s['cpu.sp'];check_y=s['cpu.y']
 -- The caller may keep its own values in Y (callee-saved); check must
 -- return with the Y and stack pointer it was entered with
 if not return_hooked then
  return_hooked=true
  local ret=emu.read((check_sp+1)&0x1ffff,emu.memType.snesWorkRam)+emu.read((check_sp+2)&0x1ffff,emu.memType.snesWorkRam)*256+1
  ret=({labels['check']}&0xff0000)|(ret&0xffff)
  emu.addMemoryCallback(function()
   local r=emu.getState()
   if r['cpu.sp']~=check_sp+2 or r['cpu.y']~=check_y then error('call ABI') end
  end,emu.callbackType.exec,ret,ret)
 end
 {assignments}
end,emu.callbackType.exec,{labels['check']},{labels['check']})
emu.addMemoryCallback(function() local s=emu.getState();entry_sp=s['cpu.sp'];entry_y=s['cpu.y'];start=s.masterClock end,emu.callbackType.exec,{labels['main']},{labels['main']})
emu.addMemoryCallback(function() muls=muls+1;trigger=emu.getState().masterClock;kind='mul' end,emu.callbackType.write,0x004203,0x004203)
emu.addMemoryCallback(function() divs=divs+1;trigger=emu.getState().masterClock;kind='div' end,emu.callbackType.write,0x004206,0x004206)
local function read()
 local elapsed=emu.getState().masterClock-trigger
 if kind=='mul' then if elapsed<48 then error('multiply latency') end;minmul=math.min(minmul,elapsed)
 elseif kind=='div' then if elapsed<96 then error('divide latency') end;mindiv=math.min(mindiv,elapsed) end
end
emu.addMemoryCallback(read,emu.callbackType.read,0x004214,0x004217)
emu.addMemoryCallback(function()
 local s=emu.getState()
 if s['cpu.a']~=0 or index~={len(rows)} then error('arithmetic case '..index..' returned '..s['cpu.a']) end
 if s['cpu.sp']~=entry_sp+3 or s['cpu.y']~=entry_y or s['cpu.d']~=0 or s['cpu.dbr']~=126 then error('exit ABI') end
 if muls~={expected_mul} or divs~={expected_div} then error('ALU counts '..muls..' '..divs) end
 emu.log('PASS '..index..' '..muls..' '..divs..' '..minmul..' '..mindiv..' '..(s.masterClock-start))
 emu.log('DONE');emu.breakExecution()
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
    scriptfile = out / 'measure.lua'
    scriptfile.write_text(script)
    core = Core(out / 'home')
    try:
        core.load(rom, scriptfile, script)
        core.start()
        log = core.wait_for('DONE', 60)
        match = re.search(r'PASS (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)', log)
        assert match, log
        result = dict(zip(('cases','multiply_writes','divide_writes','minimum_multiply_clocks','minimum_divide_clocks','master_clocks'), map(int,match.groups())))
        result.update(compiler_sha256=hashlib.sha256(args.compiler.read_bytes()).hexdigest(),
                      runtime_sha256=hashlib.sha256(args.runtime_object.read_bytes()).hexdigest(),
                      source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                      vectors_sha256=hashlib.sha256(rows_text.encode()).hexdigest(), poisoned_high_words=args.expect_widths, emulator=core.version)
        (out / 'results.json').write_text(json.dumps(result,indent=2)+'\n')
        print(args.worker, args.batch, result['cases'], result['master_clocks'], flush=True)
    finally:
        core.close_with_log(out / 'measure.log')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, default=ROOT / 'build/zicc.exe')
    parser.add_argument('--runtime-object', type=Path, default=ROOT / 'build/integers.o')
    parser.add_argument('--output', type=Path, default=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'small-integer-check')
    parser.add_argument('--worker', choices=('byte','signed-byte','word'))
    parser.add_argument('--batch', type=int)
    parser.add_argument('--expect-widths', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--list-batches', action='store_true', help='print the batch manifest without running tests')
    mode.add_argument('--collect', action='store_true', help='collect successful batch results by test type and batch number')
    args = parser.parse_args()
    if args.batch is not None and not args.worker:
        parser.error('--batch requires --worker')
    if args.list_batches:
        print(json.dumps(batch_plan(args.worker)))
        return
    if args.collect:
        collect_results(args, batch_plan(args.worker))
        return
    if args.worker and args.batch is not None:
        worker(args)
    else:
        plan = batch_plan(args.worker)
        for item in plan:
            command = [sys.executable,__file__,'--compiler',str(args.compiler),'--runtime-object',str(args.runtime_object),
                       '--output',str(args.output),'--worker',item['kind'],'--batch',str(item['batch'])]
            if args.expect_widths:
                command.append('--expect-widths')
            subprocess.run(command,check=True)
        collect_results(args, plan)


if __name__ == '__main__':
    main()
