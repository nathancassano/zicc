"""Compare loops over bytes and structures in far memory, compiling the loops separately from their callers."""
import os
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'far-loop-check';c.OUT.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);args=parser.parse_args()
report={}
for mode in (('optimized','unoptimized','baseline') if args.baseline else ('optimized','unoptimized')):
    stem=c.OUT/(mode+'_kernel')
    command=[args.baseline if mode=='baseline' else ROOT/'build/zicc.exe',ROOT/'tests/far_loop_kernels.c','-o',stem.with_suffix('.s')]
    if mode=='unoptimized':command+=['--no-register-loops','--no-strength-reduction']
    c.run(command)
    asm=stem.with_suffix('.s').read_text()
    if mode=='optimized':
        assert asm.count('; far byte loop:')==12,asm
        assert asm.count('; far byte loop: indexed Y')==9,asm
        for name in ('reverse_far','copy_next','double_step'):
            body=asm.split('_'+name+':',1)[1].split('__size_'+name,1)[0]
            assert '; far byte loop: private DP cursors' in body,name
        assert '; far counted reduction:' in asm and '; shared far element address' in asm
        expanded=asm.split('; bounded far sentinel word loop:',1)[1].split('__size_expand_far_words',1)[0]
        assert expanded.count('    lda [__arith_lhs]')==1
        rows=asm.split('_merge_far_rows:',1)[1].split('__size_merge_far_rows',1)[0]
        assert '; retained far/near word rows: 2 rows' in rows
        assert '; compact wrapping word rows' in rows
        assert '    ora a:$0080,x' in rows and '    cmp #$FF7A' in rows
        wrapper=asm.split('_draw_wrapper_words:',1)[1].split('__size_draw_wrapper_words',1)[0]
        assert 'inlined call: draw_wrapper_words' in wrapper
        assert '; bounded far sentinel word loop:' in wrapper
        assert not any('write_wrapper_words' in line for line in wrapper.splitlines() if 'jsr' in line)
        fixed=asm.split('_merge_fixed_rows:',1)[1].split('__size_merge_fixed_rows',1)[0]
        assert '; fixed font and buffer offsets' in fixed and '; compact wrapping word rows' in fixed
        assert 'lda f:' in fixed and 'ora a:.loword(_fixed_tiles+$0002),y' in fixed
        switch=asm.split('_merge_fixed_switch:',1)[1].split('__size_merge_fixed_switch',1)[0]
        assert '; fixed word-row switch: 5 cases' in switch
        assert switch.count('    cpx #$0009')==1
        assert switch.count('; shared wrapping word rows')==2
        assert '; compact wrapping word rows' not in switch
        bounded=asm.split('_merge_bounded_switch:',1)[1].split('__size_merge_bounded_switch',1)[0]
        assert '; fixed word-row switch: 2 cases' in bounded
        assert '    cpx' not in bounded and 'wrapping word rows' not in bounded
        copied=asm.split('_copy_far:',1)[1].split('__size_copy_far',1)[0]
        assert '    pei' not in copied and '    phx' not in copied and '    pha' not in copied
        equal=asm.split('_equal_far:',1)[1].split('__size_equal_far',1)[0]
        assert equal.count('    lda [$02],y')==1
        nullable=asm.split('_pointer_value:',1)[1].split('__size_pointer_value',1)[0]
        assert '    cmp #0' in nullable and '    ldx #$0000' in nullable
        mixed=asm.split('_signed_mixed:' ,1)[1].split('__size_signed_mixed',1)[0]
        assert '; far byte loop:' not in mixed
    elif mode=='unoptimized':
        assert '; far byte loop:' not in asm and '; far counted reduction:' not in asm
        assert '; fixed word-row switch:' not in asm
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',stem.with_suffix('.o'),stem.with_suffix('.s')])
    _,rom,labels=c.compile_case(mode,(ROOT/'tests/far_loop_driver.c').read_text(),extra_objects=[stem.with_suffix('.o'),ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
    report[mode]=c.emulate(rom,labels,0)
    report[mode]+=c.run([sys.executable,ROOT/'tests/check-libc.py','--pal-rom',rom],timeout=30).stdout
    print('PASS far loops '+mode+' NTSC/PAL')
report['sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'build/zicc.exe',ROOT/'build/integers.o',ROOT/'tests/far_loop_kernels.c',ROOT/'tests/far_loop_driver.c']}
(c.OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
