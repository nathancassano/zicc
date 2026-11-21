"""Exercise compiler-emitted binary64 values and helper calls."""
import os
import importlib.util
from pathlib import Path
import re
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'ieee64-codegen-check';c.OUT.mkdir(parents=True,exist_ok=True)

KERNEL=r'''
#include <stdarg.h>
extern volatile long double a,b,sum,difference,product,quotient,negated,composed,call_result,callback_result;
extern volatile unsigned calls;
extern volatile long input32;extern volatile unsigned long long input64;
extern volatile float input_float,narrow_float;
extern volatile float literal_array[1];
extern volatile float mixed_narrow,mixed_float_call;
extern volatile long double from_float_mixed;
extern volatile long double from32,from64,from_float;
extern volatile long double mixed_int,mixed_float,mixed_compound;
extern volatile long narrow32;extern volatile long long narrow64;
extern volatile long double near_value,post_near,pre_near,post_far,pre_far,far_value;
extern volatile long double rounding_value,rounding_old,rounding_after;
extern volatile unsigned near_calls,far_calls;
extern volatile unsigned var_calls;
extern volatile long double var_direct,var_indirect;
extern volatile double promoted_var;
extern volatile int narrow_compound;
volatile long double *near_address(void){near_calls++;return &near_value;}
volatile long double * __far far_address(void){far_calls++;return (volatile long double * __far)0x7efffcUL;}
long double compute(long double x,long double y){calls++;return (x+y)*x;}
float add_float(float x,float y){return x+y;}
typedef long double (*Binary)(long double,long double);
Binary callback=compute;
long double var_calc(int tag,long double base,...){
    va_list ap;int n;long double x,y;unsigned long long u;
    var_calls++;if(tag!=5)var_calls+=100;va_start(ap,base);n=va_arg(ap,int);x=va_arg(ap,long double);
    u=va_arg(ap,unsigned long long);y=va_arg(ap,long double);va_end(ap);
    return base+x+y+(long double)n+(long double)u;
}
typedef long double (*Variadic)(int,long double,...);
Variadic var_callback=var_calc;
double promoted_argument(int tag,...){va_list ap;double value;va_start(ap,tag);value=va_arg(ap,double);va_end(ap);return value;}
int count_positive(double value){return value>0.0?3:4;}
int compare_values(void){return a>b && b<a && a!=b && a>=a && a<=a && a>input32 && a>input_float;}
void kernel(void){
    long double local;
    sum=a+b;difference=a-b;product=a*b;quotient=a/b;
    negated=-a;composed=(a+b)*(a-b);
    call_result=compute(a,b);callback_result=callback(a,b);
    from32=(long double)input32;from64=(long double)input64;from_float=(long double)input_float;
    narrow32=(long)a;narrow64=(long long)b;narrow_float=(float)a;
    mixed_int=a+input32;mixed_float=input_float+a;
    local=a;local+=input_float;mixed_compound=local;
    post_near=(*near_address())++;pre_near=++(*near_address());
    *far_address()=b;post_far=(*far_address())--;pre_far=--(*far_address());
    far_value=*far_address();
    rounding_old=rounding_value++;rounding_after=rounding_value;--rounding_value;
    var_direct=var_calc(5,a,-4,b,7ULL,a);
    var_indirect=var_callback(5,a,-4,b,7ULL,a);
    promoted_var=promoted_argument(0,input_float);
    narrow_compound=5;narrow_compound+=count_positive(a);narrow_compound*=count_positive(b);
    literal_array[0]=3.5;
    mixed_narrow=(float)a+input_float;
    mixed_float_call=add_float((float)a,(float)b);
    from_float_mixed=(long double)((float)b+input_float);
}
'''
DRIVER=r'''
volatile long double a=1.5L,b=-2.25L;
volatile long double sum,difference,product,quotient,negated,composed,call_result,callback_result;
volatile long double negative_zero=-0.0L;
union Bits { unsigned long long bits; long double value; } nan={0x7ff8000000001234ULL};
volatile unsigned calls;
volatile long input32=-1234567L;volatile unsigned long long input64=0x123456789abcdef0ULL;
volatile float input_float=1.25F,narrow_float;
volatile float literal_array[1];
volatile float mixed_narrow,mixed_float_call;
volatile long double from_float_mixed;
volatile long double from32,from64,from_float;
volatile long double mixed_int,mixed_float,mixed_compound;
volatile long narrow32;volatile long long narrow64;
volatile long double near_value=1.5L,post_near,pre_near,post_far,pre_far,far_value;
volatile long double rounding_value=9007199254740992.0L,rounding_old,rounding_after;
volatile unsigned near_calls,far_calls;
volatile unsigned var_calls;
volatile long double var_direct,var_indirect;
volatile double promoted_var;
volatile int narrow_compound;
typedef char verify_double[(sizeof(double)==8 && sizeof(long double)==8 && sizeof(float)==4 && sizeof(1.0)==8 && sizeof(1.0F)==4)?1:-1];
void kernel(void);int compare_values(void);
int nan_checks(void){return nan.value!=a && !(nan.value==a) && !(nan.value<a) && !(nan.value>a) && !(nan.value<=a) && !(nan.value>=a);}
int main(void){kernel();if(negative_zero)return 1;if(!compare_values())return 2;
 if(!nan_checks())return 3;if(narrow32!=1L||narrow64!=-2LL)return 4;
 return calls!=2||near_calls!=2||far_calls!=4||var_calls!=2||narrow_compound!=32;}
'''
EXPECTED={'sum':-0.75,'difference':3.75,'product':-3.375,'quotient':-2/3,
          'negated':-1.5,'composed':-2.8125,'call_result':-1.125,'callback_result':-1.125,
          'from32':-1234567.0,'from64':float(0x123456789abcdef0),'from_float':1.25}
EXPECTED.update(mixed_int=-1234565.5,mixed_float=2.75,mixed_compound=2.75)
EXPECTED.update(near_value=3.5,post_near=1.5,pre_near=3.5,post_far=-2.25,pre_far=-4.25,far_value=-4.25)
EXPECTED.update(rounding_value=9007199254740991.0,rounding_old=9007199254740992.0,rounding_after=9007199254740992.0)
EXPECTED.update(var_direct=3.75,var_indirect=3.75)
EXPECTED.update(promoted_var=1.25)
EXPECTED.update(from_float_mixed=-1.0)

def main():
    kernel=c.OUT/'kernel.c';kernel.write_text(KERNEL)
    driver=c.OUT/'driver.c';driver.write_text(DRIVER)
    for stage in (1,3,4):
        raw=c.OUT/f'ieee64-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',driver,kernel,'--stage',str(stage),'-o',raw],timeout=120)
        sy={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        for name in ('_dadd','_dsub','_dmul','_ddiv','_dcmp','_fnptr64_compute','_fnptr64_var_calc'):assert name in sy,name
        rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        checks=['local once=false','emu.addMemoryCallback(function()',' if once then return end',' once=true']
        for name,value in EXPECTED.items():
            address=sy[name]&0x1ffff
            for i,byte in enumerate(struct.pack('<d',value)):
                checks.append(f" require_value(emu.read({address+i},emu.memType.snesWorkRam,false)=={byte},'{name} byte {i}')")
        for name,value in (('narrow_float',1.5),('mixed_narrow',2.75),('mixed_float_call',-0.75),('literal_array',3.5)):
            for i,byte in enumerate(struct.pack('<f',value)):
                checks.append(f" require_value(emu.read({(sy[name]&0x1ffff)+i},emu.memType.snesWorkRam,false)=={byte},'{name} byte {i}')")
        checks.append(f"end,emu.callbackType.exec,{sy['main_exit']},{sy['main_exit']})")
        c.emulate(rom,sy,0,extra_checks='\n'.join(checks))
    print('PASS: binary64 arithmetic, comparisons, calls and callbacks in LoROM and banked stages 3/4')

if __name__=='__main__':main()
