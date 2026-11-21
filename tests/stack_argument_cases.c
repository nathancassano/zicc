int stored;
void bump_word(int *p){*p+=1;}
void bump_long(long *p){*p+=1L;}
void bump_byte(signed char *p){*p+=1;}
void touch_float(float *p){*p=3.25f;}

long stack_only(long a,long b){bump_long(&a);return a+b;}
int stack_only_word(long a,long b){bump_long(&a);return (int)(a^b);}
void stack_only_void(long a){bump_long(&a);stored=(int)a;}
float stack_only_float(float a,float b){touch_float(&a);return b;}
unsigned long wide_then_word(unsigned long a,int b){b+=1;a+=(unsigned long)b;return a;}
unsigned long word_then_wide(int a,unsigned long b){b+=(unsigned long)a;return b;}
unsigned long wide_word_local(unsigned long a,int b)
{int temporary;temporary=b+3;bump_word(&temporary);return a+(unsigned long)temporary;}
unsigned long word_wide_local(int a,unsigned long b)
{int temporary;temporary=a+3;bump_word(&temporary);return b+(unsigned long)temporary;}
int two_words(int a,int b,int c,int d){c+=d;bump_word(&c);return a+b+c+d;}
int mixed_eight(int a,int b,signed char c,unsigned short d,long e,float f,int *out,unsigned char last)
{
    bump_byte(&c);d+=2;e+=3;f=3.25f;
    *out=a+b+c+(int)d+(int)e+last;
    return f==3.25f&&c==-2&&d==1236&&e==2003L;
}
long recursive_stack(long value,int depth,int extra)
{if(!depth)return value;value+=extra;return recursive_stack(value,depth-1,extra)+1L;}
int cached_stack(int a,int b,int n,int d)
{int quotient,remainder;quotient=n/d;remainder=n%d;return quotient+remainder+a+b;}
struct StackGuard {unsigned char tag;long bits;};
int check_guard(struct StackGuard *p){return p->tag==7&&p->bits==0x12345678L;}
int shifted_objects(long first,int second,int third)
{
    struct StackGuard guard;int values[3];int k;
    guard.tag=7;guard.bits=0x12345678L;
    for(k=0;k<3;k++)values[k]=second+k;
    bump_long(&first);bump_word(&third);
    return check_guard(&guard)&&first==11L&&second==20&&third==31&&
           values[0]==20&&values[1]==21&&values[2]==22;
}

int main(void)
{
    int i,out;
    for(i=0;i<16;i++){
        if(stack_only(0x1234ffffL,2L)!=0x12350002L)return 1;
        if(stack_only_word(20L,7L)!=18)return 2;
        stack_only_void(99L);if(stored!=100)return 3;
        if(stack_only_float(1.5f,2.25f)!=2.25f)return 4;
        if(wide_then_word(0x89abcdefUL,7)!=0x89abcdf7UL)return 5;
        if(word_then_wide(9,0x89abcdefUL)!=0x89abcdf8UL)return 6;
        if(wide_word_local(0x89abcdefUL,7)!=0x89abcdfaUL)return 7;
        if(word_wide_local(9,0x89abcdefUL)!=0x89abcdfcUL)return 8;
        if(two_words(2,3,5,7)!=25)return 9;
        out=0;if(!mixed_eight(2,3,-3,1234,2000L,1.5f,&out,7)||out!=3249)return 10;
        if(recursive_stack(100L,4,3)!=116L)return 11;
        if(!shifted_objects(10L,20,30))return 12;
        if(cached_stack(2,3,42,5)!=15||cached_stack(2,3,-42,5)!=-5)return 13;
    }
    return 0;
}
