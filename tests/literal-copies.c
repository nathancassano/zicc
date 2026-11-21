char *strcpy(char *d,const char * __far s);
char buffer[96],other[96];
unsigned selections,offset,nmis,irqs,irq_status;
unsigned long interrupt_mix;
void loop_interrupt_enable(void);
void loop_interrupt_disable(void);
__interrupt(nmi) void literal_nmi(void){++nmis;interrupt_mix=(interrupt_mix<<(nmis&7))+1UL;}
__interrupt(irq) void literal_irq(void){irq_status=*(unsigned char * __far)0x4211UL;++irqs;interrupt_mix=(interrupt_mix<<(irqs&7))+1UL;}
__interrupt(brk) void literal_brk(void){interrupt_mix=(interrupt_mix<<1)+1UL;}
__interrupt(cop) void literal_cop(void){interrupt_mix=(interrupt_mix<<1)+1UL;}
/* The interrupt observer hooks these leaf entry and return addresses */
__noinline char *literal_copy(char *d){return strcpy(d,"DIRECT ROM COPY, CHECK PADDING");}
__noinline char *tiny_copy(char *d){return strcpy(d,"xy");}
char *dynamic_copy(char *d,const char * __far s){return strcpy(d,s);}
char *select_destination(void){++selections;return buffer+1;}
int main(void)
{
    unsigned i;char *p;char * __far edge=(char * __far)0x7efffeUL;
    for(i=0;i<96;++i){buffer[i]=85;other[i]=85;}
    if(strcpy(buffer+1,"")!=buffer+1||buffer[1]||buffer[0]!=85||buffer[2]!=85)return 1;
    strcpy(buffer+1,"A\0ignored");if(buffer[1]!='A'||buffer[2]||buffer[3]!=85)return 2;
    strcpy(buffer+1,"\200\377");if(buffer[1]!=128||buffer[2]!=255||buffer[3]||buffer[4]!=85)return 3;
    strcpy(buffer+1,"abc");if(buffer[3]!='c'||buffer[4]||buffer[5]!=85)return 4;
    strcpy(buffer+1,"abcd");if(buffer[4]!='d'||buffer[5]||buffer[6]!=85)return 5;
    selections=0;p=strcpy(select_destination(),"0123456789abcde");
    if(selections!=1||p!=buffer+1||buffer[15]!='e'||buffer[16]||buffer[17]!=85)return 6;
    offset=1;p=strcpy(buffer+offset++,"12345678");if(offset!=2||p!=buffer+1||buffer[8]!='8'||buffer[9])return 7;
    if(strcpy(strcpy(buffer+1,"inner"),"outer")!=buffer+1||buffer[1]!='o'||buffer[5]!='r'||buffer[6])return 8;
    if(strcpy(buffer+1,(const char * __far)(const void * __far)"cast")!=buffer+1||buffer[4]!='t'||buffer[5])return 9;
    other[0]='r';other[1]='a';other[2]='m';other[3]=0;
    if(dynamic_copy(buffer+1,other)!=buffer+1||buffer[3]!='m'||buffer[4])return 10;
#ifndef BANKED_LITERAL_TEST
    edge[0]='X';edge[1]=(char)128;edge[2]='Y';edge[3]=0;
    if(dynamic_copy(buffer+1,edge)!=buffer+1||buffer[1]!='X'||buffer[2]!=128||buffer[3]!='Y'||buffer[4])return 11;
    /* The ordinary near destination cursor wraps within bank $7E */
    p=(char *)65535U;
    if(strcpy(p,"Q")!=p||*p!='Q'||*(char *)0!=0)return 12;
    /* The last two bytes land at $0000-$0001, before direct-page scratch */
    if(dynamic_copy(p,"xy")!=p||*p!='x'||*(char *)0!='y'||*(char *)1!=0)return 13;
#endif
    loop_interrupt_enable();
    for(i=0;i<4000;++i){
        if(literal_copy(buffer+1)!=buffer+1||buffer[1]!='D'||buffer[30]!='G'||buffer[31])return 14;
        if(tiny_copy(buffer+1)!=buffer+1||buffer[1]!='x'||buffer[2]!='y'||buffer[3])return 15;
    }
    loop_interrupt_disable();
    if(!nmis||!irqs||buffer[0]!=85||buffer[32]!=85)return 16;
    return 0;
}
