struct Record { short quantity; unsigned long price; };
unsigned long reduce_far(const struct Record * __far p,int count);
struct Record ram_records[500];
unsigned scan_far(const char * __far p);
int equal_far(const char * __far a,const char * __far b);
int copy_far(char *d,const char * __far s);
void loop_interrupt_enable(void);
void loop_interrupt_disable(void);
unsigned nmis,irqs,irq_status;
unsigned long interrupt_mix;
char copied[12001];
__interrupt(nmi) void loop_nmi(void)
{
    ++nmis;
    interrupt_mix=(interrupt_mix<<(nmis&7))+0x10001UL;
}
__interrupt(irq) void loop_irq(void)
{
    unsigned before=nmis;
    irq_status=*(unsigned char * __far)0x4211UL;
    ++irqs;
    interrupt_mix=(interrupt_mix<<(irqs&7))+0x10001UL;
    if(irqs==1)while(nmis==before){}
}
int main(void)
{
    unsigned i;
    const char * __far p=(const char * __far)0x7e8000UL;
    for(i=0;i<500;++i){ram_records[i].quantity=1;ram_records[i].price=2UL;}
    loop_interrupt_enable();
    if(reduce_far(rom_records,500)!=1000UL||reduce_far(ram_records,500)!=1000UL)return 8;
    if(copy_far(copied,(const char * __far)0x7fa000UL)!=12000)return 1;
    if(copied[0]!=3||copied[11999]!=3||copied[12000]!=0)return 2;
    /* 65793 bytes force both a physical bank crossing and a full Y wrap */
    if(scan_far(p)!=257u)return 3;
    if(!equal_far(p,p)||equal_far(p,p+1))return 4;
    if(reduce_far((const struct Record * __far)p,11000)!=EXPECTED_SUM)return 7;
    loop_interrupt_disable();
    if(!nmis||!irqs)return 5;
    return 0;
}
