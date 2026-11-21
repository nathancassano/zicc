"""Execute every signed/unsigned byte through typedef aliases and arrays."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('typedef_support',ROOT/'tests/check-compiler.py')
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)

def main():
    support.OUT.mkdir(parents=True,exist_ok=True)
    source="""
#include <stdint.h>
typedef int8_t Signed;
typedef Signed Again;
typedef uint8_t Unsigned;
volatile Again values[256];
volatile Unsigned unsigned_values[256];
__noinline int read_signed(Again x){return x;}
__noinline int read_pointer(volatile Again *p){return *p;}
int main(void){
 int i,expected;
 for(i=0;i<256;i++){values[i]=(Again)i;unsigned_values[i]=(Unsigned)i;}
 for(i=0;i<256;i++){
  expected=i<128?i:i-256;
  if(values[i]!=expected)return 1;
  if(read_signed(values[i])!=expected)return 2;
  if(read_pointer(values+i)!=expected)return 3;
  if(unsigned_values[i]!=i)return 4;
 }
 return 0;
}
"""
    _,rom,labels=support.compile_case('typedef_char',source,flags=['-I',ROOT/'include'])
    support.emulate(rom,labels,0)
    print('PASS all 256 signed/unsigned typedef values, alias chains, parameters and pointers')
    for name, declaration, diagnostic in (
        ('duplicate_sign', 'int signed unsigned x;', 'conflicting signed/unsigned'),
        ('mixed_rank', 'long short x;', 'conflicting integer type'),
        ('mixed_char', 'int char x;', 'char cannot be combined'),
        ('char_unsigned_conflict', 'int f(char); int f(unsigned char);', 'conflicting parameter type'),
        ('char_signed_conflict', 'int f(char); int f(signed char);', 'conflicting parameter type'),
        ('char_pointer_conflict', 'typedef char Byte; int f(Byte *); int f(unsigned char *);', 'conflicting parameter type'),
        ('short_conflict', 'int f(short); int f(int);', 'conflicting parameter type'),
        ('deep_qualifier', 'int *p; const int **q=&p;', 'incompatible pointer initializer'),
        ('deep_qualifier_assignment', 'int *p; const int **q; void f(void){q=&p;}', 'incompatible nested pointer assignment'),
        ('nested_layout_assignment', 'int *p; int * __far *q; void f(void){q=&p;}', 'incompatible nested pointer assignment'),
        ('array_layout_initializer', 'int *a[2]; int * __far (*q)[2]=&a;', 'incompatible pointer initializer'),
        ('array_layout_assignment', 'int *a[2]; int * __far (*q)[2]; void f(void){q=&a;}', 'incompatible pointer-to-array assignment'),
        ('array_layout_argument', 'int *a[2]; void take(int * __far (*)[2]); void f(void){take(&a);}', 'incompatible argument'),
        ('discard_pointer_qualifier', 'int *const p=0; int **q=&p;', 'incompatible pointer initializer'),
        ('void_discards_qualifier', 'int *const volatile p=0; void *q=&p;', 'incompatible pointer initializer'),
        ('void_assignment_discards_qualifier', 'void f(void){int *const p=0;void *q=&p;}', 'discards const qualification'),
        ('void_double_pointer', 'int *p; void **q=&p;', 'incompatible pointer initializer'),
        ('short_pointer_conflict', 'int f(short *); int f(int *);', 'conflicting parameter type'),
        ('pointer_add', 'int f(int *a,int *b){return (int)(a+b);}', 'pointer arithmetic'),
        ('float_remainder', 'float f(float x){return x%2;}', 'integer operands'),
        ('float_compound', 'float f(float x){x%=2;return x;}', 'integer operands'),
    ):
        path = support.OUT / f'{name}.c'
        path.write_text(declaration)
        result = support.run([ROOT/'build/zicc.exe', path, '-o', path.with_suffix('.s')], expected=1)
        assert diagnostic in result.stderr, result.stderr

    callee = support.OUT / 'short_callee.c'
    callee.write_text("long widen(unsigned short x, short y){return x+0L+y;}")
    assembly = callee.with_suffix('.s')
    obj = callee.with_suffix('.o')
    support.run([ROOT/'build/zicc.exe', callee, '-o', assembly])
    support.run([support.CC65/'ca65.exe', '--cpu', '65816', '-o', obj, assembly])
    _, rom, labels = support.compile_case('short_promotions', """
long widen(unsigned short, short);
short volatile int unsigned u=65535U;
volatile short s=-2;
char volatile unsigned c=255;
volatile char plain=255;
int literal(const char * __far s){return *s;}
int through_pointer(int *const volatile *p){return **p;}
int pointee=37;
int *pointer=&pointee;
int *const volatile *qualified=&pointer;
int * __far far_elements[2]={&pointee,&pointee};
int * __far * __far outer;
int * __far (* __far far_row)[2];
int * __far read_far_row(int * __far (* __far row)[2]){return (*row)[1];}
int *const volatile held=&pointee;
const volatile void *opaque=&held;
int *through_void(void *p){int **q=p;return *q;}
int through_const_void(const volatile void *p){int *const volatile *q=p;return **q;}
int main(void){
    if (u < s) return 1;
    if (s+0U != 65534U) return 2;
    if (widen(u,s) != 65533L) return 3;
    if (-c != -255 || -(unsigned char)255 != -255) return 4;
    if (-(unsigned short)1 != 65535U) return 5;
    if (plain != 255 || -plain != -255 || sizeof plain != 1) return 6;
    if (literal("A") != 65) return 7;
    if (**qualified != 37 || through_pointer(&pointer) != 37) return 8;
    if (through_void(&pointer)!=&pointee) return 9;
    if (opaque != &held || through_const_void(opaque)!=37) return 10;
    outer=&far_elements[0];far_row=&far_elements;
    if (**outer != 37 || *read_far_row(far_row)!=37) return 11;
    return 0;
}
""", extra_objects=[obj, ROOT/'build/integers.o'])
    support.emulate(rom, labels, 0)
    print('PASS short identity, arithmetic diagnostics and separate-TU promotions')

if __name__=='__main__':main()
