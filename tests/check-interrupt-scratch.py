"""Check minimal handler scratch sets and preservation through actual interrupts."""
import os
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'interrupt-scratch-check'
SPEC = importlib.util.spec_from_file_location('interrupts', ROOT/'tests/check-interrupts.py')
interrupts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(interrupts)
interrupts.OUT = OUT
interrupts.support.OUT = OUT
EXPECTED = {'supervisor': [0x02, 0x04, 0x06, 0x08], 'vblank': [],
            'raster': [0x04], 'software_break': [0x02]}


def helper_contracts():
    # Audit independently against the assembly runtime, including shared exits
    expected = {'__ucmp16': 0, '__scmp16': 0, '__ucmp32': 0, '__scmp32': 0,
                '__shl32': 3, '__ushr32': 3, '__sshr32': 3}
    bases = {'L': 0, 'R': 4, 'T': 8, 'SIGN': 12}
    blocks = {}
    for path in sorted((ROOT/'runtime/integers').glob('*.s')):
        text = path.read_text()
        global_labels = list(re.finditer(r'^(\w+):', text, re.M))
        for i, m in enumerate(global_labels):
            blocks[m[1]] = text[m.end():global_labels[i+1].start() if i+1<len(global_labels) else len(text)]
        for name, offset in bases.items():
            expression = '__arith_lhs' if name != 'R' else '__arith_rhs'
            if offset not in (0, 4): expression += '+'+str(offset)
            if re.search(r'^'+name+'=', text, re.M):
                assert re.search(r'^'+name+'='+re.escape(expression)+r'$', text, re.M), (path.name, name)
    allowed = set(expected)

    def footprint(name, visited):
        if name in visited: return 0
        visited.add(name); mask = 0
        for line in blocks[name].splitlines():
            line = line.split(';')[0].strip()
            if not line or line.startswith(('@', ':', '.')): continue
            parts = line.split(None, 1); op = parts[0]; operand = parts[1] if len(parts)>1 else ''
            assert op in ('lda','ldx','and','cmp','cpx','sbc','eor','sec','tax','dex','xba','rts',
                          'bcc','bcs','beq','bne','bpl','bmi','bvc','bvs','bra','jmp',
                          'sta','stx','stz','asl','lsr','rol','ror'), (name, line)
            target = re.sub(r'^\.loword\((\w+)\)$', r'\1', operand)
            if (op == 'jmp' or op.startswith('b')) and re.fullmatch(r'\w+', target):
                assert target in allowed, (name, line)
                mask |= footprint(target, visited)
            if op in ('sta','stx','sty','stz','inc','dec','asl','lsr','rol','ror','trb','tsb') and operand != 'a':
                m = re.fullmatch(r'z:(L|R|T|SIGN)(?:\+(\d+))?', operand)
                assert m, (name, line)
                byte = bases[m[1]] + int(m[2] or 0)
                mask |= (1 << (byte//2)) | (1 << ((byte+1)//2))
        return mask

    for name, mask in expected.items():
        assert footprint(name, set()) == mask, name
    # Audit every memory write in each wide helper module against the compiler's
    # conservative clobber contract, including internal shared labels
    for filename, allowed in (('shift.s',0x000f),('mul.s',0x0fff),
                              ('div.s',0x1fff),('cmp.s',0)):
        wide=(ROOT/'runtime/int64'/filename).read_text()
        aliases={name:int(offset or 0) for name,offset in re.findall(
            r'^(\w+)\s*=\s*__arith_lhs(?:\+(\d+))?\s*$',wide,re.M)}
        mask=0
        label = macro = ''
        for line in wide.splitlines():
            line=line.split(';')[0].strip()
            if re.fullmatch(r'\w+:',line):label=line[:-1]
            if line.startswith('.macro '):macro=line.split()[1]
            if line=='.endmacro':macro=''
            call=re.match(r'^js[rl]\s+(?:\.loword\()?([\w]+)',line)
            if call:assert re.search(r'^\s*'+re.escape(call[1])+r':',wide,re.M),(filename,line)
            m=re.match(r'^(sta|stx|sty|stz|inc|dec|asl|lsr|rol|ror|trb|tsb)\s+(\S+)$',line)
            if not m or m[2]=='a':continue
            if filename=='div.s' and label=='divide64_hardware' and m[2] in ('f:$004204','f:$004206'):
                continue
            if filename=='div.s' and (macro or label) in ('divide64_byte','divide64_word','divide_words') and m[2]=='z:L,x':
                mask |= 0x000f
                continue
            if filename=='div.s' and macro=='divide_words' and m[2] in ('z:M+I*2','z:M+top'):
                assert set(re.findall(r'^\s+divide_words (\d+)$',wide,re.M)) == {'2','3','4'}
                assert 'top = (words-1)*2' in wide and '.repeat words-1, I' in wide
                mask |= 0x0f00
                continue
            if filename=='div.s' and label=='divide64_single' and m[2]=='z:M+I*2':
                assert re.search(r'\.repeat 4, I\s+lda z:L\+I\*2\s+sbc z:R\+I\*2\s+sta z:M\+I\*2\s+\.endrepeat',wide)
                mask |= 0x0f00
                continue
            if filename=='div.s' and macro=='seed_remainder' and m[2] in ('z:M+2*I','z:L+2*(4-words+I)'):
                # The three macro expansions touch only the dividend and
                # remainder words. Each index is in [0, 3]
                mask |= 0x0f0f
                continue
            if filename=='mul.s' and label=='multiply64_columns':
                if m[2] in ('1,s','3,s','5,s','f:$004202','f:$004203'):
                    continue
                if m[2]=='z:P,x':
                    mask |= 0x0f00
                    continue
            op=re.fullmatch(r'z:(\w+)(?:\+(\d+))?',m[2])
            assert op and op[1] in aliases,(filename,line)
            byte=aliases[op[1]]+int(op[2] or 0)
            mask |= (1<<(byte//2)) | (1<<((byte+1)//2))
        assert mask==allowed,(filename,mask,allowed)
        expected['int64/'+filename]=mask
    environment = {name: (ROOT/'runtime/ieee64'/f'{name}.s').read_text()
                   for name in ('environment', 'environment-state')}
    env_calls = {'__fp_round_increment': 0, '__fp_raise': 0,
                 '__fp_overflow': 0x000f, '__fp_tiny': 0x000f}
    for helper, mask in env_calls.items():
        source = environment['environment-state' if helper == '__fp_raise' else 'environment']
        body = source.split(helper + ':', 1)[1].split('\n__fp_', 1)[0].split('\n_fegetround:', 1)[0]
        writes = {int(offset or 0) // 2 for offset in re.findall(
            r'\bz:__arith_lhs(?:\+(\d+))?\b', body)}
        assert sum(1 << word for word in writes) == mask, helper
    for filename,allowed in (('addsub.s',0x3fff),('cmp.s',0),('div.s',0x7fff),
                             ('extend.s',0x01ff),('fromint32.s',0x00ff),('fromint64.s',0x003f),
                             ('fromint64-to-float.s',0x007f),
                             ('mul.s',0x1fff),('neg.s',0x0008),('toint32.s',0x0073),
                             ('toint64.s',0x001f),('truncate.s',0x0ff3)):
        wide=(ROOT/'runtime/ieee64'/filename).read_text()
        aliases={name:int(offset or 0) for name,offset in re.findall(
            r'^(\w+)\s*=\s*__arith_lhs(?:\+(\d+))?\s*$',wide,re.M)}
        aliases['__arith_lhs']=0;mask=0
        label = ''
        for line in wide.splitlines():
            line=line.split(';')[0].strip()
            if re.fullmatch(r'\w+:',line):label=line[:-1]
            call=re.match(r'^js[rl]\s+(?:\.loword\()?([\w]+)',line)
            if call:
                if filename=='div.s' and call[1]=='digits':
                    assert set(re.findall(r'^\s+quotient_words (\w+)$',wide,re.M)) == {'div64_word_digits','div64_digit'}
                elif call[1] in env_calls:
                    mask |= env_calls[call[1]]
                else:
                    assert re.search(r'^\s*'+re.escape(call[1])+r':',wide,re.M),(filename,line)
            m=re.match(r'^(sta|stx|sty|stz|inc|dec|asl|lsr|rol|ror|trb|tsb)\s+(\S+)$',line)
            if not m or m[2]=='a':continue
            if filename=='mul.s' and re.fullmatch(r'\d+,s',m[2]):continue
            if filename=='mul.s':
                if label in ('mul64_columns','mul64_high_bytes') and m[2] in ('f:$004202','f:$004203'):
                    continue
                if label=='mul64_columns' and m[2]=='COL+1,s':
                    assert '.repeat 13, COL' in wide
                    continue
                if label=='mul64_high_bytes' and m[2]=='WORD*2+1,s':
                    continue
            if filename=='div.s':
                if label=='div64_hardware' and m[2] in ('f:$004204','f:$004206'):
                    continue
                if label=='div64_byte_digit' and m[2]=='z:Q,x':
                    mask |= 0x0f00
                    continue
                if label=='div64_scale_significand' and m[2]=='z:Q+I*2':
                    assert re.search(r'\.repeat 4, I\s+lda z:L\+I\*2\s+sta z:Q\+I\*2\s+\.endrepeat',wide)
                    mask |= 0x0f00
                    continue
            op=re.fullmatch(r'z:(\w+)(?:\+(\d+))?',m[2])
            assert op and op[1] in aliases,(filename,line)
            byte=aliases[op[1]]+int(op[2] or 0)
            mask |= (1<<(byte//2)) | (1<<((byte+1)//2))
        assert mask==allowed,(filename,mask,allowed)
        expected['ieee64/'+filename]=mask
    return expected


def preservation(assembly, names):
    entries = list(re.finditer(r'^_(\w+):\n', assembly, re.M))
    blocks = {m[1]: assembly[m.end():entries[i+1].start() if i+1<len(entries) else len(assembly)]
              for i, m in enumerate(entries)}
    result = {}
    for name, expected in names.items():
        body = blocks[name]
        saves = [int(n, 16) for n in re.findall(r'^    pei \(\$(\w+)\)', body, re.M)]
        restores = [int(n, 16) for n in re.findall(r'^    pla\n    sta z:\$(\w+)', body, re.M)]
        assert saves == expected, (name, saves, expected)
        assert restores == expected[::-1], (name, restores, expected)
        result[name] = dict(words=saves, scratch_stack_bytes=2*len(saves))
    return result


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    helper = OUT/'driver.s'; helper.write_text(interrupts.driver(15, 1))
    interrupts.support.run([interrupts.support.CC65/'ca65.exe','--cpu','65816','-g','-o',helper.with_suffix('.o'),helper])
    source = (ROOT/'tests/interrupt_scratch.c').read_text()
    interrupts.support.compile_case('handlers-15-clock-1', source,
        extra_objects=[helper.with_suffix('.o'), *[ROOT/'build'/(name+'.o')
            for name in ('arithmetic','integers','ieee_engine','tables')]])
    asm = (OUT/'handlers-15-clock-1.s').read_text()
    result = preservation(asm, EXPECTED)
    # Direct indexed addition reads table[q] as an ADC operand, removing the
    # RHS workspace write. Retain the sparse-save contract on its fallback
    interrupts.support.compile_case('handlers-indexed-fallback', source,
        extra_objects=[helper.with_suffix('.o'), *[ROOT/'build'/(name+'.o')
            for name in ('arithmetic','integers','ieee_engine','tables')]],
        flags=['--no-indexed-operands'])
    fallback = preservation((OUT/'handlers-indexed-fallback.s').read_text(),
        {**EXPECTED, 'software_break': [0x02, 0x06]})
    result['software_break_indexed_fallback'] = fallback['software_break']
    for name in ('__shl32','__ushr32','__sshr32','__ucmp32','__scmp32'):
        assert f'jsr .loword({name})' in asm, name
    # cg.arithmetic can be true for register-only shifts; unreachable expressions
    # can reference helpers. Neither should cause scratch saves without writes
    source = '''unsigned long a; unsigned int p, count, user__arith_lhs;
__interrupt(irq) void register_only(void){a=a>>1;}
__interrupt(nmi) void dead_helper(void){return;a=a<<p;}
__interrupt(cop) void empty(void){}
__interrupt(brk) void increment(void){count++;user__arith_lhs=5;}
int main(void){return 0;}
'''
    path = OUT/'zero.c'; path.write_text(source)
    interrupts.support.run([ROOT/'build/zicc.exe', path, '-o', OUT/'zero.s'])
    result.update(preservation((OUT/'zero.s').read_text(), {n:[] for n in ('register_only','dead_helper','empty','increment')}))
    return result


def auto_addressing():
    support = interrupts.support
    stem = OUT/'automatic'
    source = stem.with_suffix('.c')
    source.write_text('''#include <time.h>
#define REG(a) (*(volatile unsigned char * __far)(a##UL))
volatile __dpage unsigned char done;
volatile unsigned ticks;
__interrupt(nmi) void user_nmi(void){
    REG(0x4300)=1; REG(0x4301)=2; REG(0x4302)=3;
    REG(0x4303)=4; REG(0x4304)=5; REG(0x4305)=6;
    (void)REG(0x4210);
    ticks=1; done=1;
}
int main(void){clock_t before=clock();
    (void)REG(0x4210); REG(0x4200)=0x80;
    while(!done){}
    REG(0x4200)=0;
    return ticks!=1 || clock()==before;
}
''')
    raw = stem.with_suffix('.raw')
    support.run([sys.executable, ROOT/'tools/build-rom.py', source, '-o', raw])
    allocation = json.loads(stem.with_suffix('.allocation.json').read_text())
    directory = Path(allocation['evidence'])/f"stage{allocation['stage']}"
    asm = next(directory.glob('*_automatic.s')).read_text()
    nmi = asm.split('interrupt_body_user_nmi:\n', 1)[1].split('.segment "NMI_END"', 1)[0]
    assert 'lda f:$004210' in nmi
    sy = interrupts.labels(stem)
    rom = stem.with_suffix('.sfc')
    support.run([ROOT/'build/romtool.exe', raw, rom, ROOT/'tests/title.txt'])
    boundary = sy['_nmi_library_bank']
    extra = f'''local user_seen=false
local boundary_seen=false
emu.addMemoryCallback(function()
 local state=emu.getState()
 require_value(state['cpu.d']==0x4300 and state['cpu.dbr']==0x80,'user interrupt D/DBR')
 user_seen=true
end,emu.callbackType.exec,{sy['interrupt_body_user_nmi']+17},{sy['interrupt_body_user_nmi']+17})
emu.addMemoryCallback(function()
 local state=emu.getState()
 require_value(state['cpu.d']==0 and state['cpu.dbr']==0x7f,'library interrupt D/DBR')
 boundary_seen=true
end,emu.callbackType.exec,{boundary+5},{boundary+5})
emu.addMemoryCallback(function()
 require_value(user_seen and boundary_seen,'user and library interrupt both ran')
 local state=emu.getState()
 require_value(state['cpu.d']==0 and state['cpu.dbr']==0x7e,'foreground D/DBR restored')
end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})
'''
    return support.emulate(rom, sy, 0, seed=True, extra_checks=extra)


def wide_interrupt():
    support = interrupts.support
    source = r'''
volatile unsigned long long a=0x123456789abcdef0ULL,b=0x12345ULL;
volatile unsigned long long product,quotient,remainder,shifted,far_copy;
volatile long long sa=-1234567890123LL,sb=12345LL,signed_quotient;
volatile unsigned count=13,events;
volatile unsigned long long * __far pointer=(volatile unsigned long long * __far)0x7f1234UL;
int test_driver(void);
__interrupt(cop) void wide_handler(void){
    product=a*b; quotient=a/b; remainder=a%b; shifted=a>>count;
    signed_quotient=sa/sb; *pointer=a; far_copy=*pointer; events++;
}
int main(void){
    test_driver();
    if(product!=0x1c71c71c71b8cfb0ULL)return 1;
    if(quotient!=0x100005b00205ULL)return 2;
    if(remainder!=0xa497ULL)return 3;
    if(shifted!=0x91a2b3c4d5e6ULL)return 4;
    if(signed_quotient!=-100005499LL)return 5;
    if(far_copy!=a)return 6;
    return events!=4;
}
'''
    # Independent host calculations prevent accidental transcription errors
    a=0x123456789abcdef0; b=0x12345
    source=source.replace('0x1c71c71c71b8cfb0ULL',hex(a*b & ((1<<64)-1))+'ULL')
    source=source.replace('0x100005b00205ULL',hex(a//b)+'ULL')
    source=source.replace('0xa497ULL',hex(a%b)+'ULL')
    source=source.replace('0x91a2b3c4d5e6ULL',hex(a>>13)+'ULL')
    source=source.replace('-100005499LL',str(-(1234567890123//12345))+'LL')
    driver=['.setcpu "65816"','.a16','.i16','.export _test_driver',
            '.export before0,before1,before2,before3,after0,after1,after2,after3',
            '.segment "CODE"','_test_driver:','phy']
    for i in range(4):
        driver+=['sed']
        if i&1: driver+=['sep #$20','.a8']
        if i&2: driver+=['sep #$10','.i8']
        driver += [f'before{i}:','.byte $02,$73',f'after{i}:','rep #$30','.a16','.i16','cld']
    driver+=['ply','lda #0','rts']
    path=OUT/'wide-driver.s';path.write_text('\n'.join(driver)+'\n')
    support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',path.with_suffix('.o'),path])
    _,rom,sy=support.compile_case('wide-interrupt',source,extra_objects=[path.with_suffix('.o'),ROOT/'build/libc.a'])
    asm=(OUT/'wide-interrupt.s').read_text()
    saved=preservation(asm,{'wide_handler':[x for x in range(0x02,0x22,2) if x!=0x1c]})
    for name in ('__mul64_soft','__udiv64_soft','__umod64_soft','__sdiv64_soft','__ushr64'):
        assert f'jsr .loword({name})' in asm,name
    checks=['local hits=0']
    for i in range(4):
        checks += [f'emu.addMemoryCallback(function() for j=0x02,0x21 do emu.write(j,(j*37+{i})&255,emu.memType.snesWorkRam) end end,emu.callbackType.exec,{sy["before"+str(i)]},{sy["before"+str(i)]})',
                   f'emu.addMemoryCallback(function() for j=0x02,0x21 do require_value(emu.read(j,emu.memType.snesWorkRam,false)==((j*37+{i})&255),"wide interrupt scratch") end hits=hits+1 end,emu.callbackType.exec,{sy["after"+str(i)]},{sy["after"+str(i)]})']
    checks += [f'emu.addMemoryCallback(function() require_value(hits==4,"wide interrupt count") end,emu.callbackType.exec,{sy["main_exit"]},{sy["main_exit"]})']
    support.emulate(rom,sy,0,extra_checks='\n'.join(checks))
    return saved


def binary64_interrupt():
    support=interrupts.support
    source=r'''
volatile long double a=1.5L,b=-2.25L,sum,difference,product,quotient,from_float,from_int,from_wide,far_copy;
volatile float single=1.25F,to_float,from_signed_wide,from_unsigned_wide;
volatile long integer=-123L,to_int;
volatile long long wide=-9876543210LL,to_wide;
volatile unsigned long long unsigned_wide=4294967296ULL;
volatile unsigned events,compared;
volatile long double * __far pointer=(volatile long double * __far)0x7f1234UL;
int test_driver(void);
__interrupt(cop) void binary_handler(void){
    sum=a+b;difference=a-b;product=a*b;quotient=a/b;
    from_float=(long double)single;from_int=(long double)integer;from_wide=(long double)wide;
    to_float=(float)a;to_int=(long)b;to_wide=(long long)b;
    from_signed_wide=(float)wide;from_unsigned_wide=(float)unsigned_wide;
    if(a>b)compared++;*pointer=a;far_copy=*pointer;events++;
}
int main(void){test_driver();
    if(sum!=-0.75L||difference!=3.75L||product!=-3.375L||quotient!=(-2.0L/3.0L))return 1;
    if(from_float!=1.25L||from_int!=-123.0L||from_wide!=-9876543210.0L||far_copy!=a)return 2;
    if(to_float!=1.5F||to_int!=-2L||to_wide!=-2LL||compared!=4||events!=4||
       from_signed_wide!=-9876543488.0F||from_unsigned_wide!=4294967296.0F)return 3;
    return 0;
}
'''
    driver=OUT/'wide-driver.o'
    _,rom,sy=support.compile_case('binary64-interrupt',source,extra_objects=[driver,ROOT/'build/libc.a',
                                *[ROOT/'build'/(name+'.o') for name in ('arithmetic','integers','ieee_engine','tables')]])
    asm=(OUT/'binary64-interrupt.s').read_text()
    saved=preservation(asm,{'binary_handler':list(range(0x02,0x22,2))})
    for name in ('__dadd','__dsub','__dmul_soft','__ddiv_soft','__dcmp','__fext32_64',
                 '__ftrunc64_32','__sfloat64_32','__sfloat64_64','__fix64_32','__fix64_64',
                 '__sfloat32_64','__ufloat32_64'):
        assert f'jsr .loword({name})' in asm,name
    checks=['local hits=0','local snapshots={}']
    for i in range(4):
        checks += [f'emu.addMemoryCallback(function() snapshots[{i}]=emu.getState(); for j=0x02,0x21 do emu.write(j,(j*37+{i})&255,emu.memType.snesWorkRam) end end,emu.callbackType.exec,{sy["before"+str(i)]},{sy["before"+str(i)]})',
                   f'emu.addMemoryCallback(function() local s=emu.getState(); for _,k in ipairs({{"a","x","y","d","dbr","sp","ps","k"}}) do require_value(s["cpu."..k]==snapshots[{i}]["cpu."..k],"binary64 interrupt register "..k) end; for j=0x02,0x21 do require_value(emu.read(j,emu.memType.snesWorkRam,false)==((j*37+{i})&255),"binary64 interrupt scratch") end hits=hits+1 end,emu.callbackType.exec,{sy["after"+str(i)]},{sy["after"+str(i)]})']
    checks += [f'emu.addMemoryCallback(function() require_value(hits==4,"binary64 interrupt count") end,emu.callbackType.exec,{sy["main_exit"]},{sy["main_exit"]})']
    support.emulate(rom,sy,0,extra_checks='\n'.join(checks))
    return saved


def no_wide_handler_overhead():
    # Compile the same handler with and without wide foreground operations
    # Adding a foreground helper must not enlarge or alter the interrupt body
    path=OUT/'handler-overhead.c'; asm_path=OUT/'handler-overhead.s'
    handler='''volatile unsigned long value; volatile unsigned count;
__interrupt(cop) void narrow_handler(void){value=value>>count;}
'''
    bodies=[]
    for foreground in ('int main(void){return 0;}',
                       'volatile unsigned long long x,y,z; int main(void){z=x*y;return 0;}',
                       'volatile unsigned long long x,y,z; int main(void){z=x+y;return 0;}'):
        path.write_text(handler+foreground+'\n')
        interrupts.support.run([ROOT/'build/zicc.exe',path,'-o',asm_path])
        text=asm_path.read_text()
        body=text.split('_narrow_handler:\n',1)[1].split('__size_narrow_handler',1)[0]
        bodies.append(body)
        preservation(text,{'narrow_handler':[0x02,0x04,0x06]})
        assert '    cld\n' not in body
    assert bodies[0]==bodies[1]==bodies[2],'foreground wide arithmetic changed the narrow handler'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', choices=('ntsc','pal')); args = parser.parse_args()
    if args.region:
        interrupts.worker(args.region, 15, 1); return
    contracts = helper_contracts(); result = build(); result.update(wide_interrupt()); result.update(binary64_interrupt()); no_wide_handler_overhead()
    for region in ('ntsc','pal'):
        checked = interrupts.run([sys.executable,__file__,'--region',region],timeout=40)
        assert checked.returncode == 0, checked.stdout+checked.stderr
    paths = [ROOT/'src/codegen/codegen.inc',*sorted((ROOT/'runtime/integers').glob('*.s')),ROOT/'build/zicc.exe',ROOT/'tests/interrupt_scratch.c',
             *sorted((ROOT/'runtime/ieee64').glob('*.s'))]
    report = dict(handlers=result,helper_clobbers=contracts,regions=['ntsc','pal'],auto_addressing=auto_addressing(),
                  sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: zero, one-word, sparse and helper scratch sets; NTSC/PAL preservation in all four interrupt width modes')


if __name__ == '__main__': main()
