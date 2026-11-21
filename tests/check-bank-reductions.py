"""Check totals from structures in RAM and ROM, including signed fields and reads across bank boundaries."""
import os
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'bank-reduction-check';c.OUT.mkdir(parents=True,exist_ok=True)
TEMPLATE=r'''
LAYOUT
const struct R rom[5]={VALUES};
struct R ram[5]={VALUES};
unsigned long reduce_any(const struct R * __far p,int count);
int count_value(int n){return n;}
int main(void){
 unsigned long keep=0x12345678UL;
 struct R * __far edge=(struct R * __far)0x7effffUL;
 if(reduce_any((struct R * __far)0,0)||reduce_any((struct R * __far)0,-1)||reduce_any(rom,-32768))return 1;
 if(reduce_any(rom,0)||reduce_any(ram,-1))return 2;
 if(reduce_any(rom,1)!=32768UL||reduce_any(rom,2)!=0x80007fffUL||reduce_any(rom,3)!=0x80007fffUL)return 3;
 if(reduce_any(rom,count_value(4))!=0x7ffe0000UL||reduce_any(rom,5)!=0x7ffdfffeUL)return 4;
 if(reduce_any(ram,5)!=0x7ffdfffeUL||reduce_any(ram+1,1)!=0x7fffffffUL)return 5;
 if(keep+reduce_any(rom,2)!=0x9234d677UL||keep!=0x12345678UL)return 6;
 edge[0].quantity=-3;edge[0].price=10UL;edge[1].quantity=4;edge[1].price=20UL;
 if(reduce_any(edge,2)!=50UL||reduce_any(edge+1,1)!=80UL)return 7;
 return 0;
}
unsigned long reduce_any(const struct R * __far p,int count){
 unsigned long total=0;int i;
 for(i=0;i<count;++i)total+=(unsigned long)p[i].quantity*p[i].price;
 return total;
}
'''
layouts={
 'six':('struct R {short quantity;unsigned long price;};','{-32768,0xffffffffUL},{-1,0x80000001UL},{0,0x12345678UL},{32767,0x1ffffUL},{2,0xffffffffUL}'),
 'eight':('struct R {unsigned id;short quantity;unsigned long price;};','{1,-32768,0xffffffffUL},{2,-1,0x80000001UL},{3,0,0x12345678UL},{4,32767,0x1ffffUL},{5,2,0xffffffffUL}'),
 'twelve':('struct R {unsigned long pad;short quantity;unsigned tag;unsigned long price;};','{0,-32768,1,0xffffffffUL},{0,-1,2,0x80000001UL},{0,0,3,0x12345678UL},{0,32767,4,0x1ffffUL},{0,2,5,0xffffffffUL}'),
}
run=c.run;report={}
for name,(layout,values) in layouts.items():
    source=TEMPLATE.replace('LAYOUT',layout).replace('VALUES',values)
    for mode in ('on','off','unoptimized'):
        def command(args,*a,**kw):
            if Path(args[0]).name=='zicc.exe':
                if mode=='off':args=[*args,'--no-bank-specialization']
                if mode=='unoptimized':args=[*args,'--no-register-loops','--no-strength-reduction']
            return run(args,*a,**kw)
        c.run=command
        _,rom,labels=c.compile_case(name+'_'+mode,source,extra_objects=[ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
        asm=rom.with_suffix('.s').read_text();body=asm.split('\n_reduce_any:\n',1)[1].split('__size_reduce_any',1)[0]
        if mode!='unoptimized':
            assert 'frame 6' in body and '    pei' not in body
            # One entry save: the stack-relative frame frees Y for the far loads
            assert body.count('    phy\n')==1 and body.count('    ply\n')==1
            assert 'lda [__arith_lhs+16],y\n    sta z:__arith_lhs\n    bpl' in body
        entries=re.findall(r'^; bank specialization: (\w+) reduce_any ([NR]W)$',asm,re.M)
        assert len(entries)==(2 if mode=='on' else 0),(name,mode,entries)
        report[name+'-'+mode]=c.emulate(rom,labels,0)
        report[name+'-'+mode]+=run([sys.executable,ROOT/'tests/check-libc.py','--pal-rom',rom],timeout=30).stdout
        print('PASS bank reductions '+name+' '+mode+' NTSC/PAL')
c.run=run
(c.OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
