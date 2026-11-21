/* Compile-only examples accompanying docs/optimizations.md */
#include <stdint.h>
#include <string.h>

uint16_t words[64], other[64], flags[8], output[16], quotient_value, remainder_value;
uint8_t bytes[400];
union Packet { uint8_t bytes[64]; uint16_t words[32]; } packet;
const uint8_t rom_bytes[8] = {1,2,3,4,5,6,7,8};
extern uint16_t consume(uint16_t a, uint16_t b, uint16_t c);
extern void send(const uint8_t * __far p, uint16_t destination, uint16_t size);

__noinline unsigned folded(void) { return (9 + 3) * 4; }
__noinline unsigned copied(unsigned x) { unsigned a=x,b=a; return b+3; }
__noinline unsigned computed(unsigned x) { unsigned t=x+3; return t^7; }
__noinline unsigned times_five(unsigned x) { return x*5; }
__noinline unsigned shifted(unsigned x) { return x<<8; }
__noinline unsigned masked(unsigned char x) { return ((x&255)+42)&63; }
__noinline unsigned byte_product(unsigned char a,unsigned char b) { return a*b; }
__noinline unsigned long mixed_product(unsigned a,unsigned long b) { return (unsigned long)a*b; }
__noinline unsigned long wide_add(unsigned long x) { return x+1UL; }
__noinline unsigned low_word(unsigned long x) { return (unsigned)x; }
__noinline unsigned high_word(unsigned long x) { return (unsigned)(x>>16); }
__noinline unsigned wide_equal(unsigned long x) { return x==0x12345678UL; }
__noinline void fixed_mmio(void) { *(volatile uint8_t * __far)0x004200UL=0x80; }
__noinline unsigned switch_cases(unsigned x) {
    switch(x) { case 1:return 7;case 2:return 9;default:return 0; }
}
__noinline unsigned indexed(unsigned i) { return words[i]+3; }
__noinline unsigned rom_indexed(unsigned i) { return rom_bytes[i]; }
__noinline void direct_update(void) { quotient_value++; }
__noinline void quotient_remainder(unsigned a,unsigned b) { quotient_value=a/b; remainder_value=a%b; }
__noinline void scalar_store(unsigned *p,unsigned value) { *p=value+3; }
__noinline void fixed_argument(void) { send(packet.bytes,0,64); }
__noinline void literal_copy(char *p) { strcpy(p,"OK"); }
__noinline int near_compare(char *a,char *b) { return strcmp(a,b); }

__noinline int bounded_min(int a,int b) {
    int x=(a&127)-64,y=(b&127)-32;
    return x<y?x:y;
}
__noinline void shared_selections(void) {
    uint8_t i;uint16_t x,y;
    for(i=0;i<8;i++) {
        x=flags[i]?91:199;y=flags[i]?17:37;
        if(output[i]>x)output[i]=x;
        if(output[i+8]>y)output[i+8]=y;
    }
}
__noinline void stride_loop(void) {
    uint8_t i;
    for(i=0;i<56;i++) { bytes[i*5+3]=0;bytes[i*5+4]=1; }
}
__noinline void nested_offsets(uint8_t start) {
    uint8_t i,j;
    for(i=start;i<4;i++)
        for(j=i+1;j<12;j++) {
            words[i]+=other[j]&3;words[j]+=other[i]&3;other[j]+=words[i]&1;
        }
}
__noinline uint16_t packed_scopes(uint16_t seed) {
    uint16_t result,live=seed^23130;
    { uint16_t a=seed+3,b=seed^52;result=consume(a,b,seed+7); }
    { uint16_t a=seed+11,b=seed^25;result+=consume(a,b,seed+13); }
    return result^live;
}
struct Item { int unused,value; };
__noinline int guarded(struct Item *p,int delta) {
    int next=p->value+delta;
    if(next<0)return 0;
    p->value=next;return 1;
}
struct Record { int quantity;unsigned long value; };
__noinline unsigned long reduction(struct Record *p,int count) {
    unsigned long total=0;int i;
    for(i=0;i<count;i++)total+=(unsigned long)p[i].quantity*p[i].value;
    return total;
}
static unsigned add_three(unsigned x) { return x+3; }
__noinline unsigned inlined(unsigned x) { return add_three(x); }
