struct Record { short quantity; unsigned long price; };
int copy_far(char *d,const char * __far s)
{
    int n=0;
    while(*s){*d++=*s++;++n;}
    *d=0;
    return n;
}
int equal_far(const char * __far a,const char * __far b)
{
    while(*a&&*a==*b){++a;++b;}
    return (unsigned char)*a==(unsigned char)*b;
}
unsigned reverse_far(unsigned char * __far d,const unsigned char * __far s,unsigned n)
{
    unsigned done=4;
    while(n){*d--=*s--;--n;++done;}
    return done*3-8;
}
int affine_far(const char * __far p)
{
    int a=7,b=100;
    while(*p){++p;++a;--b;}
    return a*10+b;
}
void swap_far(char * __far a,char * __far b)
{
    char saved;
    while(*a&&*b){saved=*a;*a++=*b;*b++=saved;}
}
int signed_mixed(const signed char * __far a,const unsigned char * __far b)
{
    while(*a&&*a==*b){++a;++b;}
    return (unsigned char)*a==(unsigned char)*b;
}
unsigned fill_far(unsigned char * __far p,unsigned n)
{
    unsigned done=9;
    while(n){*p++=42;--n;++done;}
    return done;
}
unsigned long reduce_far(const struct Record * __far p,int count)
{
    unsigned long sum=0;
    int i;
    for(i=0;i<count;++i)sum+=(unsigned long)p[i].quantity*p[i].price;
    return sum;
}
unsigned long shared_far(const struct Record * __far p,int i)
{
    return (unsigned long)p[i].quantity*p[i].price;
}
unsigned scan_far(const char * __far p)
{
    unsigned n=0;
    while(*p){++p;++n;}
    return n;
}
unsigned bounded_copy(char * __far d,const char * __far s,unsigned n)
{
    unsigned done=0;
    while(n){*d++=*s++;--n;++done;}
    return done;
}
int reordered_copy(const char * __far s,char *d)
{
    int n=0;
    while(*s){*d++=*s++;++n;}
    *d=0;
    return n;
}
char *end_copy(char *d,const char * __far s)
{
    while(*s)*d++=*s++;
    *d=0;
    return d;
}
int copy_next(char *d,const char * __far s)
{
    int n=0;
    while(*s){++s;*d++=*s;++n;}
    return n;
}
void double_step(char *d,const char * __far s)
{
    while(*s){*d++=*s++;++s;}
    *d=0;
}
unsigned long pointer_value(char *p)
{
    return (unsigned long)(char * __far)p;
}
unsigned expand_far_words(unsigned *dest,const char * __far src,unsigned n)
{
    unsigned *start=dest;
    const char * __far begin=src;
    while(n&&*src){
        *dest++=(unsigned char)*src++|0x0400|0x2000;
        --n;
    }
    return (unsigned)(dest-start)*256+(unsigned)(src-begin)*16+n;
}

unsigned merge_far_rows(unsigned *dest,const unsigned * __far src)
{
    unsigned row;
    row=src[0];dest[64]|=(row>>1)&0x7f7f;dest[66]=(row&0x0101)<<7;
    row=src[1];dest[65]|=(row>>1)&0x7f7f;dest[67]=(row&0x0101)<<7;
    return row;
}

unsigned wrapper_words[4];

static unsigned write_wrapper_words(unsigned start,const char * __far src,unsigned count)
{
    unsigned *dest=wrapper_words+start;
    unsigned available=4-start;
    unsigned initial;
    if(count>available)count=available;
    initial=count;
    while(count&&*src){
        *dest++=(unsigned char)*src++|0x2000;
        --count;
    }
    return initial-count;
}

void draw_wrapper_words(unsigned x,unsigned y,const char * __far src)
{
    write_wrapper_words(y*2+x,src,4);
    return;
}

static const unsigned char fixed_font[6]={0x34,0x12,0x78,0x56,0xbc,0x9a};
unsigned fixed_tiles[8];

void merge_fixed_rows(unsigned font_offset,unsigned tile_offset,unsigned split)
{
    const unsigned * __far src=(const unsigned * __far)&fixed_font[font_offset];
    unsigned *dst=(unsigned *)((unsigned char *)fixed_tiles+tile_offset);
    if(split){
        unsigned row;
        row=src[0];dst[0]|=(row>>1)&0x7f7f;dst[2]=(row&0x0101)<<7;
        row=src[1];dst[1]|=(row>>1)&0x7f7f;dst[3]=(row&0x0101)<<7;
    }else{
        dst[0]|=src[0];
        dst[1]|=src[1];
    }
}

unsigned merge_fixed_switch(unsigned font_offset,unsigned tile_offset,unsigned shift,int enabled)
{
    unsigned row=0x4567;
    const unsigned * __far src=(const unsigned * __far)&fixed_font[font_offset];
    unsigned *dst=(unsigned *)((unsigned char *)fixed_tiles+tile_offset);
    if(enabled)switch(shift){
    case 0:
        row=src[0];dst[0]|=(row>>1)&0x7f7f;dst[2]=(row&0x0101)<<7;
        row=src[1];dst[1]|=(row>>1)&0x7f7f;dst[3]=(row&0x0101)<<7;
        break;
    case 1: {
        row=src[0];dst[0]|=(row>>2)&0x3f3f;dst[2]=(row&0x0303)<<6;
        row=src[1];dst[1]|=(row>>2)&0x3f3f;dst[3]=(row&0x0303)<<6;
        break;
    }
    default: {
        row=src[0];dst[2]=(row&0x0f0f)<<4;dst[0]|=(row>>4)&0x0f0f;
        row=src[1];dst[3]=(row&0x0f0f)<<4;dst[1]|=(row>>4)&0x0f0f;
    } break;
    case 2:
        row=src[0];dst[2]=(row&0x0707)<<5;dst[0]|=(row>>3)&0x1f1f;
        row=src[1];dst[3]=(row&0x0707)<<5;dst[1]|=(row>>3)&0x1f1f;
        break;
    case 3:
        row=src[1];dst[0]|=(row>>1)&0x7f7f;dst[2]=(row&0x0101)<<7;
        row=src[2];dst[1]|=(row>>1)&0x7f7f;dst[3]=(row&0x0101)<<7;
        break;
    }
    return row;
}

void merge_bounded_switch(unsigned font_offset,unsigned tile_offset,unsigned shift,int enabled)
{
    const unsigned * __far src=(const unsigned * __far)&fixed_font[font_offset];
    unsigned *dst=fixed_tiles+3+(tile_offset&3);
    if(enabled)switch(shift){
    case 1:
        dst[0]|=src[0]>>1;
        dst[1]|=src[1]>>1;
        break;
    case 2:
        dst[0]|=src[0]>>2;
        dst[1]|=src[1]>>2;
        break;
    }
}
