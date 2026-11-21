"""Pass and return eight-byte integers between C files compiled separately."""
import os
import importlib.util
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compiler_check',ROOT/'tests/check-compiler.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
c.OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'int64-abi-check';c.OUT.mkdir(parents=True,exist_ok=True)
MASK=(1<<64)-1
A=0x123456789abcdef0
B=0x0102030405060708
EXPECTED={'result':(A+B-7)&MASK,'nested':(A+B-7)&MASK,
          'product':(A*B+0xabcdef0123456789)&MASK,'abi_zero_result':0,'literal_result':0xfedcba9876543210,
          'sumcalls':(A+B)&MASK,'recur_result':(A+6)&MASK,'pointer_result':(A+B-7)&MASK}
KERNEL=r'''
extern volatile unsigned calls_identity,calls_mix,calls_mul,calls_accept,calls_void,calls_recur;
unsigned long long identity(unsigned long long x){calls_identity++;return x;}
unsigned long long mixed(unsigned long long x,int n,unsigned long long y){
    calls_mix++;x+=y;return x+(long long)n;
}
unsigned long long multiply_add(unsigned long long x,unsigned long long y,unsigned long long z){
    calls_mul++;return (x*y)+z;
}
unsigned long long nested_call(unsigned long long x,unsigned long long y){
    return mixed(identity(x),-7,identity(y));
}
int accept(unsigned long long x,unsigned int y){calls_accept++;return x>y;}
void consume(unsigned long long x){if(x)calls_void++;}
unsigned long long return_literal(void){return 0xfedcba9876543210ULL;}
unsigned long long recurse_wide(unsigned long long x,int n){
    calls_recur++;
    if(n==0)return x;
    return recurse_wide(x+1ULL,n-1);
}
'''
DRIVER=r'''
volatile unsigned long long a=0x123456789abcdef0ULL,b=0x0102030405060708ULL;
volatile unsigned long long result,nested,product,abi_zero_result,literal_result,sumcalls,recur_result,pointer_result;
volatile unsigned calls_identity,calls_mix,calls_mul,calls_accept,calls_void,calls_recur,calls_pointer;
unsigned long long identity(unsigned long long);
unsigned long long mixed(unsigned long long,int,unsigned long long);
unsigned long long multiply_add(unsigned long long,unsigned long long,unsigned long long);
unsigned long long nested_call(unsigned long long,unsigned long long);
unsigned long long return_literal(void);
unsigned long long recurse_wide(unsigned long long,int);
int accept(unsigned long long,unsigned int);
void consume(unsigned long long);
volatile unsigned long long *destination(void){calls_pointer++;return &pointer_result;}
int check(void){return accept(a,7);}
void driver(void){
    result=mixed(a,-7,b);
    nested=nested_call(a,b);
    product=multiply_add(a,b,0xabcdef0123456789ULL);
    abi_zero_result=identity(0ULL);
    literal_result=return_literal();
    sumcalls=identity(a)+identity(b);
    recur_result=recurse_wide(a,6);
    *destination()=mixed(a,-7,b);
    consume(a);
    identity(a);
}
int main(void){driver();return check()!=1||calls_identity!=6||calls_mix!=3||calls_mul!=1||calls_accept!=1||calls_void!=1||calls_recur!=7||calls_pointer!=1;}
'''
CALLBACK_DRIVER=r'''
typedef unsigned long long (*WideFn)(unsigned long long,int,unsigned long long);
typedef int (*NarrowFn)(unsigned long long,unsigned int);
unsigned long long mixed(unsigned long long,int,unsigned long long);
unsigned long long identity(unsigned long long);
int accept(unsigned long long,unsigned int);
volatile unsigned calls_identity,calls_mix,calls_mul,calls_accept,calls_void,calls_recur,choose_calls;
volatile unsigned long long a=0x123456789abcdef0ULL,b=0x0102030405060708ULL;
volatile unsigned long long cb_result,cb_nested,cb_sum;
WideFn callback=mixed;
NarrowFn narrow_callback=accept;
WideFn choose(void){choose_calls++;return callback;}
int check_callback(void){return narrow_callback(a,7);}
void driver(void){
    cb_result=callback(a,-7,b);
    cb_nested=choose()(identity(a),-7,identity(b));
    cb_sum=callback(a,-7,b)+callback(a,-7,b);
    callback(a,-7,b);
}
int main(void){driver();return check_callback()!=1||calls_mix!=5||calls_identity!=2||calls_accept!=1||choose_calls!=1;}
'''
VARARG_KERNEL=r'''
#include <stdarg.h>
extern volatile unsigned var_calls;
unsigned long long var_wide(unsigned long long base, int count, ...){
    va_list ap; unsigned long long x,y; int delta; unsigned long n;
    var_calls++;
    va_start(ap,count);
    delta=va_arg(ap,int); x=va_arg(ap,unsigned long long);
    n=va_arg(ap,unsigned long); y=va_arg(ap,unsigned long long);
    va_end(ap);
    return base+x+y+(long long)delta+(unsigned long long)n;
}
int var_narrow(int count,...){
    va_list ap; unsigned long long x; int n,large;
    var_calls++; va_start(ap,count);
    x=va_arg(ap,unsigned long long); n=va_arg(ap,int); va_end(ap);
    if(x>0xffffffffULL)large=1;else large=0;
    return large && n==42;
}
unsigned long long var_named(int first,int second,unsigned long long base,...){
    va_list ap; unsigned long long x; int n,sum;
    var_calls++; va_start(ap,base);
    x=va_arg(ap,unsigned long long); n=va_arg(ap,int); va_end(ap);
    sum=first+second+n;
    return base+x+(long long)sum;
}
'''
VARARG_DRIVER=r'''
typedef unsigned long long (*VarFn)(unsigned long long,int,...);
unsigned long long var_wide(unsigned long long,int,...);
int var_narrow(int,...);
unsigned long long var_named(int,int,unsigned long long,...);
volatile unsigned var_calls;
volatile unsigned long long a=0x123456789abcdef0ULL,b=0x0102030405060708ULL;
volatile unsigned long long var_direct,var_indirect,var_stack_named;
VarFn var_cb=var_wide;
int check_var(void){return var_narrow(2,b,42);}
int main(void){
    var_direct=var_wide(a,4,-7,b,0x12345678UL,a);
    var_indirect=var_cb(a,4,-7,b,0x12345678UL,a);
    var_stack_named=var_named(1,2,a,b,3);
    return check_var()!=1||var_calls!=4;
}
'''


def main():
    kernel=c.OUT/'abi-kernel.c';kernel.write_text(KERNEL)
    driver=c.OUT/'abi-driver.c';driver.write_text(DRIVER)
    kasm=c.OUT/'abi-kernel.s';kobj=c.OUT/'abi-kernel.o'
    c.run([ROOT/'build/zicc.exe',kernel,'-o',kasm])
    c.run([c.CC65/'ca65.exe','--cpu','65816','-g','-o',kobj,kasm])
    workspace=c.OUT/'workspace.s'
    workspace.write_text('.exportzp __arith_lhs,__arith_rhs\n.segment "DP_SCRATCH": zeropage\n'
                         '__arith_lhs: .res 4\n__arith_rhs: .res 28\n')
    c.run([c.CC65/'ca65.exe','-o',c.OUT/'workspace.o',workspace])
    _,rom,labels=c.compile_case('abi-driver',DRIVER,extra_objects=[kobj,c.OUT/'workspace.o',ROOT/'build/libc.a'])
    def verify(rom,labels):
        checks=['local once=false','emu.addMemoryCallback(function()',' if once then return end',' once=true']
        for name,value in EXPECTED.items():
            address=labels[name]&0x1ffff
            for i in range(8):
                checks.append(f" require_value(emu.read({address+i},emu.memType.snesWorkRam,false)=={(value>>(8*i))&255},'{name} byte {i}')")
        checks.append(f"end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})")
        c.emulate(rom,labels,0,extra_checks='\n'.join(checks))
    verify(rom,labels)
    for stage in (3,4):
        raw=c.OUT/f'banked-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',driver,kernel,'--stage',str(stage),'-o',raw],timeout=120)
        labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(
            r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        verify(rom,labels)
    callback=c.OUT/'callback-driver.c';callback.write_text(CALLBACK_DRIVER)
    callback_expected={'cb_result':(A+B-7)&MASK,'cb_nested':(A+B-7)&MASK,
                       'cb_sum':(2*(A+B-7))&MASK}
    for stage in (1,3,4):
        raw=c.OUT/f'callback-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',callback,kernel,'--stage',str(stage),'-o',raw],timeout=120)
        labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(
            r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        assert '_fnptr64_mixed' in labels and '_fnptr_accept' in labels
        rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        checks=['local once=false','emu.addMemoryCallback(function()',' if once then return end',' once=true']
        for name,value in callback_expected.items():
            address=labels[name]&0x1ffff
            for i in range(8):
                checks.append(f" require_value(emu.read({address+i},emu.memType.snesWorkRam,false)=={(value>>(8*i))&255},'{name} byte {i}')")
        checks.append(f"end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})")
        c.emulate(rom,labels,0,extra_checks='\n'.join(checks))
    var_kernel=c.OUT/'vararg-kernel.c';var_kernel.write_text(VARARG_KERNEL)
    var_driver=c.OUT/'vararg-driver.c';var_driver.write_text(VARARG_DRIVER)
    var_expected=(2*A+B-7+0x12345678)&MASK
    for stage in (1,3,4):
        raw=c.OUT/f'vararg-{stage}.raw'
        c.run([sys.executable,ROOT/'tools/build-rom.py',var_driver,var_kernel,'--stage',str(stage),'-o',raw],timeout=120)
        labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(
            r'^al ([0-9A-Fa-f]+) \.(\S+)$',raw.with_suffix('.labels').read_text(),re.M)}
        rom=raw.with_suffix('.sfc');c.run([ROOT/'build/romtool.exe',raw,rom,ROOT/'tests/title.txt'])
        checks=['local once=false','emu.addMemoryCallback(function()',' if once then return end',' once=true']
        for name,value in (('var_direct',var_expected),('var_indirect',var_expected),('var_stack_named',(A+B+6)&MASK)):
            address=labels[name]&0x1ffff
            for i in range(8):
                checks.append(f" require_value(emu.read({address+i},emu.memType.snesWorkRam,false)=={(value>>(8*i))&255},'{name} byte {i}')")
        checks.append(f"end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})")
        c.emulate(rom,labels,0,extra_checks='\n'.join(checks))
    print('PASS: 64-bit fixed and variadic ABI, direct and indirect calls, LoROM and banked stages 3/4')


if __name__=='__main__':main()
