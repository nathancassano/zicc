/* Check the multiplier recipes as linear maps modulo 2^16 */
#define main compiler_entry
#include "../src/main.c"
#undef main
typedef struct { unsigned base,value; } ScaleCheck;
static void check_scale_step(void *context,int step)
{
    ScaleCheck *s=context;
    if(step==SCALE_SHIFT)s->value*=2;
    else if(step==SCALE_BYTE_SHIFT)s->value=(s->value<<8)&65535u;
    else if(step==SCALE_ADD)s->value+=s->base;
    else if(step==SCALE_SUBTRACT)s->value-=s->base;
    else if(step==SCALE_NEGATE)s->value=0u-s->value;
    else s->value=0;
    s->value&=65535;
}
int main(void)
{
    static const unsigned inputs[]={0,1,2,127,128,255,32767,32768,65534,65535};
    unsigned factor,save,i,plans=0,checks=0;WordScale p;
    for(factor=0;factor<65536;++factor)for(save=0;save<2;++save){
        if(!word_scale_plan(factor,(int)save,&p))continue;
        ++plans;
        for(i=0;i<sizeof inputs/sizeof inputs[0];++i){
            ScaleCheck s={inputs[i],inputs[i]};
            word_scale_steps(&p,check_scale_step,&s);
            if(s.value!=((inputs[i]*factor)&65535))return 1;
            ++checks;
        }
    }
    if(!word_scale_plan(3,1,&p)||!word_scale_plan(7,1,&p)||
       !word_scale_plan(255,1,&p)||word_scale_plan(12345,1,&p))return 2;
    printf("PASS %u selected plans, %u input checks; 131072 multiplier/save candidates\n",plans,checks);
    return 0;
}
