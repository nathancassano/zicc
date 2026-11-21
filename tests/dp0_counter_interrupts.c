unsigned int counts[4], irq_status, tally;
int probe(void);
int check_live(void);
int test_driver(void);
int leaf(void)
{
    int i;
    for(i=0;i<3;i++) tally++;
    return i;
}
int nested(int depth)
{
    int i,total=0;
    for(i=0;i<3;i++) {
        check_live();
        if(depth) total+=nested(depth-1);
        else total++;
    }
    return total;
}
int count(int n)
{
    int i;
    for(i=0;i<n;i++) tally++;
    return i;
}
int interrupt_run(void)
{
    int i;
    for(i=0;i<2;i++) test_driver();
    return i;
}
__interrupt(nmi) void vblank(void)
{
    int i;
    for(i=0;i<3;i++) counts[0]++;
}
__interrupt(irq) void raster(void)
{
    int i;
    irq_status=*(unsigned char * __far)0x4211UL;
    for(i=0;i<3;i++) {
        counts[1]++;
#ifdef DP_NESTED_INTERRUPT
        if(counts[1]==1) {
            irq_status=*(unsigned char * __far)0x4210UL;
            *(unsigned char * __far)0x4200UL=128;
            while(counts[0]==0) {}
            *(unsigned char * __far)0x4200UL=0;
        }
#endif
    }
}
__interrupt(brk) void software_break(void)
{
    int i;
    for(i=0;i<3;i++) counts[2]++;
}
__interrupt(cop) void supervisor(void)
{
    int i;
    for(i=0;i<3;i++) counts[3]++;
}
int main(void)
{
    if(probe()) return 1;
    if(tally!=117) return 2;
#ifdef DP_NESTED_INTERRUPT
    if(counts[0]!=27) return 3;
#else
    if(counts[0]!=24) return 3;
#endif
    if(counts[1]!=24 || counts[2]!=24 || counts[3]!=24) return 3;
    return 0;
}
