"""Check far-pointer comparisons, discarded updates and argument passing between separately compiled C files."""
import os
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('support',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'far-pointer-cost-check';c.OUT.mkdir(parents=True,exist_ok=True)
KERNEL=r'''
const unsigned rom_words[8]={101,203,307,409,503,601,701,809};
__noinline unsigned pair4(unsigned a,unsigned b,unsigned c,unsigned d){return a+b*3+c*5+d*7;}
unsigned rom_args(unsigned i){return pair4(1,2,rom_words[i],rom_words[i+1]);}
unsigned rom_indices(unsigned i,unsigned j){return pair4(1,2,rom_words[i],rom_words[j]);}
unsigned observations;
char * __far global_pointer;
__dpage char * __far dp_pointer;
unsigned order(const char * __far a,const char * __far b){
 return (a==b)|((a!=b)<<1)|((a<b)<<2)|((a<=b)<<3)|((a>b)<<4)|((a>=b)<<5);
}
const char * __far mark(const char * __far p,unsigned n){observations+=n;return p;}
int effects(const char * __far a,const char * __far b){observations=0;return mark(a,1)<mark(b,10);}
char * __far byte_up(char * __far p){p++;return p;}
char * __far byte_down(char * __far p){--p;return p;}
char * __far post_result(char * __far p){return p++;}
char * __far loop_steps(char * __far p,unsigned n){unsigned i=0;for(;i<n;++p)++i;return p;}
void globals(unsigned long value){global_pointer=(char * __far)value;dp_pointer=(char * __far)value;global_pointer++;dp_pointer--;}
int global_order(void){return global_pointer<dp_pointer;}
unsigned five(unsigned a,unsigned b,unsigned c,unsigned d,unsigned e){return a+3*b+5*c+7*d+11*e;}
unsigned six(unsigned a,unsigned b,unsigned c,unsigned d,unsigned e,unsigned f){if(a+b+c+d+e+f!=21)return 0;return 0x8001U;}
unsigned byte(const char * __far p){return (unsigned char)*p;}
extern const unsigned char fixed_data[];
unsigned array_order(const unsigned char * __far p){
 return (p<fixed_data)|((p<=fixed_data)<<1)|((p>fixed_data)<<2)|((p>=fixed_data)<<3);
}
int near_array_order(const unsigned char *p){return p>fixed_data;}
extern unsigned array_sink(const char * __far);
unsigned array_argument(void){return array_sink((const char * __far)fixed_data);}
unsigned near_high(const char *p){return (unsigned char)((unsigned long)p>>16);}
unsigned far_byte_equal(const unsigned char * __far p){if(*p==3)return 1;return 0;}
unsigned far_byte_less(const unsigned char * __far p){if(*p<128)return 1;return 0;}
struct stride14 { unsigned char data[14]; };
struct stride6 { unsigned char data[6]; };
struct stride3 { unsigned char data[3]; };
unsigned long far14(unsigned long p,int i){return (unsigned long)((struct stride14 * __far)p+i);}
unsigned long far6(unsigned long p,unsigned i){return (unsigned long)((struct stride6 * __far)p+i);}
unsigned long far3(unsigned long p,int i){return (unsigned long)((struct stride3 * __far)p-i);}
unsigned long far14_loop(struct stride14 * __far p,unsigned n){
 unsigned long sum=0;
 for(unsigned i=0;i<n;i++)sum+=(unsigned long)(p+i);
 return sum;
}
'''
HEADER=r'''
unsigned rom_args(unsigned);unsigned rom_indices(unsigned,unsigned);
unsigned order(const char * __far,const char * __far);
extern unsigned observations;
extern char * __far global_pointer;
extern __dpage char * __far dp_pointer;
int effects(const char * __far,const char * __far);
char * __far byte_up(char * __far);char * __far byte_down(char * __far);
char * __far post_result(char * __far);char * __far loop_steps(char * __far,unsigned);
void globals(unsigned long);int global_order(void);
unsigned five(unsigned,unsigned,unsigned,unsigned,unsigned);
unsigned six(unsigned,unsigned,unsigned,unsigned,unsigned,unsigned);
unsigned byte(const char * __far);
unsigned array_argument(void);
unsigned array_order(const unsigned char * __far);int near_array_order(const unsigned char *);
unsigned near_high(const char *);
unsigned far_byte_equal(const unsigned char * __far);
unsigned far_byte_less(const unsigned char * __far);
unsigned long far14(unsigned long,int);unsigned long far6(unsigned long,unsigned);unsigned long far3(unsigned long,int);
struct stride14 { unsigned char data[14]; };
unsigned long far14_loop(struct stride14 * __far,unsigned);
'''
VALUES=(0,1,0x8000,0xffff,0x10000,0x7dffff,0x7e0000,0x7effff,0x7f0000,0x7f8000,0x7fffff,0x800000,0x80ffff,0xfeffff,0xff0000,0xffffff)
def vector(name,values,wide):
    return 'const '+('unsigned long ' if wide else 'unsigned ')+name+'['+str(len(values))+']={'+','.join(hex(x)+('UL' if wide else 'U') for x in values)+'};\n'
DRIVER=HEADER+vector('values',VALUES,True)+vector('next_values',[(x+1)&0xffffff for x in VALUES],True)+vector('previous_values',[(x-1)&0xffffff for x in VALUES],True)+vector('steps',[(x+3)&0xffffff for x in VALUES],True)+vector('expected',[41 if a==b else 14 if a<b else 50 for a in VALUES for b in VALUES],False)+r'''
const unsigned char fixed_data[2]={'K',0};
unsigned array_sink(const char * __far p){return (unsigned char)*p;}
char local[2]={'Y',0};
__dpage char small[2];
int main(void){
 unsigned i,j;char * __far p;char *near_zero=0;
 small[0]='Z';small[1]=0;
 for(i=0;i<16;++i){
  for(j=0;j<16;++j)if(order((char * __far)values[i],(char * __far)values[j])!=expected[i*16+j])return 1;
  p=(char * __far)values[i];
  if((unsigned long)byte_up(p)!=next_values[i]||(unsigned long)byte_down(p)!=previous_values[i])return 2;
  if((unsigned long)post_result(p)!=values[i]||(unsigned long)loop_steps(p,3)!=steps[i])return 3;
  globals(values[i]);
  if((unsigned long)global_pointer!=next_values[i]||(unsigned long)dp_pointer!=previous_values[i])return 4;
  if(global_order()!=(values[i]==0||values[i]==0xffffffUL))return 5;
 }
 if(!effects((char * __far)0x7effffUL,(char * __far)0x800000UL)||observations!=11)return 6;
 if(five(1,2,3,4,5)!=105||six(1,2,3,4,5,6)!=0x8001U)return 7;
 if(order(near_zero,(char * __far)0)!=41||byte(local)!='Y'||byte(small)!='Z')return 8;
 if(byte((const char * __far)(const char * __far)"Q")!='Q')return 9;
 if(far14(0x7effffUL,1)!=0x7f000dUL||far14(0x7f0000UL,-1)!=0x7efff2UL||
    far14(0xfffff8UL,1)!=6||far14(0,-1)!=0xfffff2UL)return 10;
 if(far6(0xfffffcUL,1)!=2||far6(0x7efffeUL,65535U)!=0x84fff8UL)return 11;
 if(far3(1,1)!=0xfffffdUL||far3(0x7effffUL,-1)!=0x7f0003UL)return 12;
 if(array_argument()!='K')return 13;
 if(array_order(fixed_data)!=10||array_order(fixed_data+1)!=12||
    array_order((const unsigned char * __far)0)!=3||near_array_order((unsigned char *)small)||near_array_order((const unsigned char *)0))return 19;
 if(rom_args(0)!=1933||rom_args(3)!=5573||rom_indices(1,6)!=5929)return 18;
 if(near_high((const char *)0)!=0||near_high((const char *)0xffffU)!=0)return 15;
 {unsigned char data[2]={3,2};if(!far_byte_equal(data)||far_byte_equal(data+1))return 16;}
 {unsigned char data[4]={0,127,128,255};if(!far_byte_less(data)||!far_byte_less(data+1)||far_byte_less(data+2)||far_byte_less(data+3))return 17;}
 if(far14_loop((struct stride14 * __far)0xfffff0UL,0)!=0||far14_loop((struct stride14 * __far)0xfffff0UL,3)!=0x01fffffaUL||
    far14_loop((struct stride14 * __far)0x7efff8UL,2)!=0x00fdfffeUL)return 14;
 return 0;
}
'''

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',type=Path);a=p.parse_args()
    run=c.run;report={}
    for mode in (('on','off','baseline') if a.baseline else ('on','off')):
        def command(args,**kwargs):
            args=list(args)
            if Path(args[0]).name=='zicc.exe':
                if mode=='off':args.append('--no-strength-reduction')
                elif mode=='baseline':args[0]=a.baseline
            return run(args,**kwargs)
        c.run=command
        path=c.OUT/(mode+'_kernel.c');path.write_text(KERNEL)
        c.run([ROOT/'build/zicc.exe',path,'-o',path.with_suffix('.s')])
        text=path.with_suffix('.s').read_text()
        if mode=='on':
            assert '; direct far-pointer comparison:' in text
            assert '; discarded far-byte pointer update' in text
            body=text.split('_post_result:\n',1)[1].split('__size_post_result',1)[0]
            assert '; discarded far-byte pointer update' not in body
            assert text.count('; far offset multiply by shifted difference')>=2
            array_call=text.split('_array_argument:\n',1)[1].split('__size_array_argument',1)[0]
            assert 'pea .bankbyte(_fixed_data)' in array_call and 'pea .loword(_fixed_data)' in array_call
            compare=text.split('_array_order:\n',1)[1].split('__size_array_order',1)[0]
            assert 'cpx #.bankbyte(_fixed_data)' in compare and '__ucmp32' not in compare,compare
            compare=text.split('_far_byte_equal:\n',1)[1].split('__size_far_byte_equal',1)[0]
            assert 'cmp #$03\n    rep #$20' in compare
        elif mode=='off':assert '; direct far-pointer comparison:' not in text and '; discarded far-byte pointer update' not in text
        c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',path.with_suffix('.o'),path.with_suffix('.s')])
        _,rom,labels=c.compile_case(mode,DRIVER,extra_objects=[path.with_suffix('.o'),ROOT/'build/arithmetic.o',ROOT/'build/integers.o',ROOT/'build/ieee_engine.o'])
        if mode=='on':assert '; register-preserved argument cleanup' in rom.with_suffix('.s').read_text()
        report[mode]=c.emulate(rom,labels,0)
        report[mode]+=run([sys.executable,ROOT/'tests/check-libc.py','--pal-rom',rom],timeout=30).stdout
        print('PASS far pointer costs '+mode+' NTSC/PAL: 256 pairs, six relations, wrapping updates and call ABI')
    report['sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT/'src/codegen/codegen.inc',ROOT/'src/codegen/far.inc',ROOT/'build/zicc.exe')}
    (c.OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
