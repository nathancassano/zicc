unsigned char observed;
unsigned nmis,irqs,traps,irq_status;
unsigned long interrupt_mix;
void loop_interrupt_enable(void);
void loop_interrupt_disable(void);
__interrupt(nmi) void scalar_nmi(void){++nmis;interrupt_mix=(interrupt_mix<<(nmis&7))+1UL;}
__interrupt(irq) void scalar_irq(void){irq_status=*(unsigned char * __far)0x4211UL;++irqs;interrupt_mix=(interrupt_mix<<(irqs&7))+1UL;}
__interrupt(brk) void scalar_brk(void){++traps;interrupt_mix=(interrupt_mix<<1)+1UL;}
__interrupt(cop) void scalar_cop(void){++traps;interrupt_mix=(interrupt_mix<<1)+1UL;}

int probe(a,b)
unsigned char a,b;
{
    unsigned char first,second;
    first=a;second=first;
    if(second!=b)return 0;
    observed=first;return 1;
}
int signed_probe(a,b)
signed char a,b;
{
    signed char first=a;
    signed char second=first;
    if(second==b)return (int)first;
    return 300;
}
int mixed(unsigned char a,signed char b){return a==b;}
int narrowing(int x){unsigned char a=(unsigned char)x;signed char b=(signed char)a;return b;}
int arithmetic(int a,int b){int x=a;int y=x;if((y+b)<0)return y-b;return y+b;}
int boolean(int a,int b){int x=a;if(x&&b)return x?b:a;return x||b;}
int mutate(int x){int a=x;x=7;return a+x;}
void change(int *p){*p=9;}
int escape(int x){int a=x;change(&x);return a+x;}
int recursive(int x){int a=x;if(x)return a+recursive(x-1);return 0;}
int branches(int x){int a;if(x)a=3;else a=4;return a;}
int iterations(int x){int a=x;while(x<5)++x;return a+x;}
int stack_argument(int a,int b,int c){int x=c;return a+b+x;}
long widen(int x){signed char a=(signed char)x;return (long)a;}
unsigned volatile_source;
int volatile_copy(void){unsigned a=*(volatile unsigned *)&volatile_source;volatile_source=9;return a;}

int store_probe(int a,int b,int *p){int t=a+2;*p=b+t;return 0;}
void pointer_first(int *p,int a,int b){int t=a^3;*p=t+b;}
void pointer_second(int a,int *p,int b){int t=a-2;*p=t^b;}
void pointer_last(int a,int b,int c,int d,int e,int f,int g,int *p)
{int t=(a+b)^(c-d);*p=t+e+f+g;}
int conditional_store(int a,int b,int *p){if(a<0)*p=b+(a&7);else *p=a-b;return b;}
int alias_store(int a,int b,int *p){*p=(*p+a)^b;return *p;}
int effects;
void effect(int a){effects=a;}
void framed_store(int *p,int a,int b){effect(a);*p=a+(b^3);}
void narrow_store(int a,int b,int *p){signed char t=(signed char)(a+2);*p=b+t;}
int multiple_use(int a,int b,int *p){int t=a+2;*p=t+b;return t;}
int changed_source(int a,int b,int *p){int t=a+2;a=7;*p=b+t;return a;}
void intervening_call(int a,int b,int *p){int t=a+2;effect(a);*p=b+t;}
int repeated_use(int a){int t=a+2;int i,s=0;for(i=0;i<3;++i)s+=t;return s;}
int global_snapshot(int a){int t=effects+2;effects=a;return t;}
struct Fields {int value;signed char tag;int *pointer;long wide;};
void schedule_probe(struct Fields *d,struct Fields *s)
{
    d->value=s->value;
    d->tag=s->tag;
    d->pointer=s->pointer;
    d->value=(int)s->wide;
}
struct Fields *store_destination;
struct Fields alternate;
int change_destination(void){store_destination=&alternate;return 91;}
void destination_snapshot(void){store_destination->value=change_destination();}
void narrowed_destination(unsigned bits,struct Fields *s)
{((struct Fields *)(unsigned char)bits)->value=s->value;}

int main(void)
{
    unsigned a,b,i;int out;struct Fields source,destination;
    for(a=0;a<512;++a){
      if(!probe(a,a)||!probe(a,a+256))return 1;
      for(b=0;b<512;b+=127){
        observed=77;
        if(probe(a,b)!=((a&255)==(b&255)))return 1;
        if(observed!=((a&255)==(b&255)?(a&255):77))return 2;
      }
    }
    if(!probe(65535U,255)||probe(65535U,0))return 3;
    if(signed_probe(255,65535U)!=-1||signed_probe(128,128)!=-128||signed_probe(128,0)!=300)return 4;
    if(mixed(255,-1)||!mixed(127,127))return 5;
    if(narrowing(0x1280)!=-128||narrowing(0x12ff)!=-1||widen(0x12ff)!=-1L)return 6;
    if(arithmetic(-7,2)!=-9||arithmetic(7,2)!=9||arithmetic(-32768,0)!=-32768)return 7;
    if(boolean(0,7)!=1||boolean(5,7)!=7||boolean(0,0))return 8;
    if(mutate(3)!=10||escape(3)!=12||recursive(10)!=55)return 9;
    if(branches(0)!=4||branches(1)!=3||iterations(2)!=7||stack_argument(3,4,5)!=12)return 10;
    volatile_source=3;if(volatile_copy()!=3||volatile_source!=9)return 11;
    for(a=0;a<512;++a){
        if(store_probe(a,7,&out)||out!=(int)(a+9))return 15;
        pointer_first(&out,a,11);if(out!=(int)((a^3)+11))return 16;
        pointer_second(a,&out,13);if(out!=(int)((a-2)^13))return 17;
        pointer_last(a,2,3,4,5,6,7,&out);if(out!=(int)(((a+2)^(3-4))+18))return 18;
        if(conditional_store(-(int)a,7,&out)!=7||out!=(a?7+((-(int)a)&7):-7))return 19;
        if(conditional_store(a,7,&out)!=7||out!=(int)(a-7))return 20;
        out=19;if(alias_store(a,11,&out)!=(int)((19+a)^11)||out!=(int)((19+a)^11))return 21;
        framed_store(&out,a,17);if(out!=(int)(a+(17^3))||effects!=a)return 22;
        narrow_store(a,19,&out);if(out!=19+(signed char)(a+2))return 23;
        if(multiple_use(a,7,&out)!=(int)(a+2)||out!=(int)(a+9))return 24;
        if(changed_source(a,7,&out)!=7||out!=(int)(a+9))return 25;
        intervening_call(a,7,&out);if(out!=(int)(a+9)||effects!=a)return 26;
        if(repeated_use(a)!=(int)((a+2)*3))return 27;
        effects=31;if(global_snapshot(a)!=33||effects!=a)return 28;
    }
    store_probe(32767,-32768,&out);if(out!=1)return 29;
    store_probe(-32768,-1,&out);if(out!=-32767)return 30;
    source.value=17;source.tag=-7;source.pointer=&out;source.wide=0x123480ffL;
    schedule_probe(&destination,&source);
    if(destination.value!=(int)0x80ff||destination.tag!=-7||destination.pointer!=&out)return 32;
    schedule_probe(&source,&source);
    if(source.value!=(int)0x80ff||source.tag!=-7||source.pointer!=&out)return 33;
    store_destination=&destination;alternate.value=0;destination_snapshot();
    if(destination.value!=91||alternate.value||store_destination!=&alternate)return 34;
    narrowed_destination(0x180,&source);if(*(int *)0x80!=(int)0x80ff)return 36;
    loop_interrupt_enable();
    for(i=0;i<12000;++i){
        if(probe(i,i)!=1||probe(i,i+1)!=0)return 12;
        if(arithmetic(-7,2)!=-9)return 13;
        if(store_probe(i,7,&out)||out!=(int)(i+9))return 31;
    }
    for(i=0;i<12000;++i){
        schedule_probe(&destination,&source);
        if(destination.value!=(int)0x80ff||destination.tag!=-7||destination.pointer!=&out)return 35;
    }
    loop_interrupt_disable();
    if(!nmis||!irqs)return 14;
    return 0;
}
