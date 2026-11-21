struct Record { short quantity; unsigned long price; };
int copy_far(char *d,const char * __far s);
int equal_far(const char * __far a,const char * __far b);
unsigned reverse_far(unsigned char * __far d,const unsigned char * __far s,unsigned n);
int affine_far(const char * __far p);
void swap_far(char * __far a,char * __far b);
int signed_mixed(const signed char * __far a,const unsigned char * __far b);
unsigned fill_far(unsigned char * __far p,unsigned n);
unsigned long reduce_far(const struct Record * __far p,int n);
unsigned long shared_far(const struct Record * __far p,int i);
unsigned scan_far(const char * __far p);
unsigned bounded_copy(char * __far d,const char * __far s,unsigned n);
int reordered_copy(const char * __far s,char *d);
char *end_copy(char *d,const char * __far s);
int copy_next(char *d,const char * __far s);
void double_step(char *d,const char * __far s);
unsigned long pointer_value(char *p);
unsigned expand_far_words(unsigned *dest,const char * __far src,unsigned n);
unsigned merge_far_rows(unsigned *dest,const unsigned * __far src);
void draw_wrapper_words(unsigned x,unsigned y,const char * __far src);
extern unsigned wrapper_words[4];
void merge_fixed_rows(unsigned font_offset,unsigned tile_offset,unsigned split);
unsigned merge_fixed_switch(unsigned font_offset,unsigned tile_offset,unsigned shift,int enabled);
void merge_bounded_switch(unsigned font_offset,unsigned tile_offset,unsigned shift,int enabled);
extern unsigned fixed_tiles[8];
char source[600],destination[600],other[600];
unsigned words[4];
int main(void)
{
    unsigned i;
    char * __far edge=(char * __far)0x7efffeUL;
    unsigned char * __far back=(unsigned char * __far)0x7f1002UL;
    struct Record * __far records=(struct Record * __far)0x7efffdUL;
    if(copy_far(destination,"")||!equal_far(destination,""))return 1;
    for(i=0;i<599;++i)source[i]=(char)((i%255)+1);
    source[599]=0;
    if(copy_far(destination,source)!=599||!equal_far(destination,source))return 2;
    if(affine_far(source)!=5561)return 3;
    if(copy_far(destination,destination)!=599||copy_far(destination,destination+1)!=598)return 4;
    edge[0]=1;edge[1]=(char)128;edge[2]=(char)255;edge[3]=0;
    if(copy_far(destination,edge)!=3||!equal_far(destination,edge)||affine_far(edge)!=197)return 5;
    if(reverse_far(back,(unsigned char * __far)(edge+2),0)!=4)return 6;
    if(reverse_far(back,(unsigned char * __far)(edge+2),3)!=13||back[0]!=255||back[-1]!=128||back[-2]!=1)return 7;
    source[0]='a';source[1]='b';source[2]=0;other[0]='x';other[1]='y';other[2]=0;
    swap_far(source,other);if(source[0]!='x'||source[1]!='y'||other[0]!='a'||other[1]!='b')return 8;
    swap_far(source,source);if(source[0]!='x'||source[1]!='y')return 9;
    source[0]=(char)255;source[1]='a';other[0]=(char)255;other[1]='b';
    if(!signed_mixed((signed char *)source,(unsigned char *)other))return 10;
    if(fill_far((unsigned char * __far)edge,0)!=9||fill_far((unsigned char * __far)edge,3)!=12)return 11;
    if(edge[0]!=42||edge[1]!=42||edge[2]!=42||edge[3]!=0)return 12;
    records[0].quantity=-3;records[0].price=10UL;records[1].quantity=4;records[1].price=20UL;
    if(reduce_far(records,-1)!=0UL||reduce_far(records,0)!=0UL||reduce_far(records,2)!=50UL)return 13;
    if(shared_far(records,1)!=80UL||shared_far(records+1,-1)!=4294967266UL)return 14;
    edge[0]=1;edge[1]=(char)128;edge[2]=(char)255;edge[3]=0;
    if(scan_far(edge)!=3||reordered_copy(edge,destination)!=3||end_copy(destination,edge)!=destination+3)return 15;
    if(copy_next(destination,edge)!=3||(unsigned char)destination[0]!=128||(unsigned char)destination[1]!=255||destination[2]!=0)return 16;
    source[0]='A';source[1]='a';source[2]='B';source[3]='b';source[4]=0;
    double_step(destination,source);if(destination[0]!='A'||destination[1]!='B'||destination[2]!=0)return 17;
    if(bounded_copy(source+1,source,4)!=4)return 18;
    for(i=0;i<5;++i)if(source[i]!='A')return 19;
    if(bounded_copy(source,source+1,0)!=0||bounded_copy(source,source,4)!=4)return 20;
    if(pointer_value((char *)0)!=0UL||pointer_value(source)!=(unsigned long)(char * __far)source)return 21;
    words[0]=words[3]=0x1234;
    if(expand_far_words(words,edge,0)||words[0]!=0x1234)return 22;
    if(expand_far_words(words,edge,2)!=0x220||words[0]!=0x2401||words[1]!=0x2480)return 23;
    if(expand_far_words(words,edge,4)!=0x331||words[2]!=0x24ff||words[3]!=0x1234)return 24;
    if(expand_far_words(words,edge+3,4)!=4||words[0]!=0x2401)return 25;
    {
        unsigned * __far src=(unsigned * __far)0x7efffeUL;
        unsigned * __far wrapped=(unsigned * __far)0x7e007eUL;
        unsigned * __far other_bank=(unsigned * __far)0x7f007eUL;
        unsigned tile[68];
        src[0]=0x0381;src[1]=0x81ff;
        tile[64]=1;tile[65]=2;
        if(merge_far_rows(tile,src)!=0x81ff||tile[64]!=0x0141||
           tile[65]!=0x407f||tile[66]!=0x8080||tile[67]!=0x8080)return 26;
        wrapped[0]=1;wrapped[1]=2;other_bank[0]=0x4567;
        if(merge_far_rows((unsigned *)0xfffe,src)!=0x81ff||
           wrapped[0]!=0x0141||wrapped[1]!=0x407f||
           wrapped[2]!=0x8080||wrapped[3]!=0x8080||other_bank[0]!=0x4567)return 27;
    }
    edge[0]=1;edge[1]=(char)128;edge[2]=(char)255;edge[3]=0;
    wrapper_words[0]=0x4567;
    draw_wrapper_words(0,2,edge);
    if(wrapper_words[0]!=0x4567||wrapper_words[3])return 28;
    draw_wrapper_words(0,0,edge+3);
    if(wrapper_words[0]!=0x4567)return 29;
    draw_wrapper_words(1,0,edge);
    if(wrapper_words[0]!=0x4567||wrapper_words[1]!=0x2001||
       wrapper_words[2]!=0x2080||wrapper_words[3]!=0x20ff)return 30;
    merge_fixed_rows(2,2,0);
    if(fixed_tiles[0]||fixed_tiles[1]!=0x5678||fixed_tiles[2]!=0x9abc||fixed_tiles[3])return 31;
    {
        /* Adding the offset to the fixed base wraps to $0080 in DBR */
        unsigned * __far spill=(unsigned * __far)0x7e0080UL;
        unsigned * __far spill_other=(unsigned * __far)0x7f0080UL;
        spill[0]=1;spill[1]=2;spill[2]=3;spill[3]=4;spill_other[0]=0x4567;
        merge_fixed_rows(0,0x0080-(unsigned)fixed_tiles,1);
        if(spill[0]!=0x091b||spill[1]!=0x2b3e||spill[2]||spill[3]||
           spill_other[0]!=0x4567)return 32;
        for(i=0;i<5;++i){
            unsigned shift=i<3?i:i==3?65535:3;
            unsigned bits=i==4?1:i+1;
            unsigned first=i==4?0x5678:0x1234,last=i==4?0x9abc:0x5678;
            unsigned merged_mask=(0xffu>>bits)*257;
            unsigned spill_mask=(0xffu>>(8-bits))*257;
            fixed_tiles[0]=spill[0]=1;fixed_tiles[1]=spill[1]=2;
            fixed_tiles[2]=spill[2]=3;fixed_tiles[3]=spill[3]=4;
            if(merge_fixed_switch(0,0,shift,1)!=last||
               merge_fixed_switch(0,0x0080-(unsigned)fixed_tiles,shift,1)!=last)return 33;
            if(spill[0]!=(((first>>bits)&merged_mask)|1)||
               spill[1]!=(((last>>bits)&merged_mask)|2)||
               spill[2]!=(unsigned)((first&spill_mask)<<(8-bits))||
               spill[3]!=(unsigned)((last&spill_mask)<<(8-bits))||
               spill_other[0]!=0x4567)return 34;
            if(fixed_tiles[0]!=spill[0]||fixed_tiles[1]!=spill[1]||
               fixed_tiles[2]!=spill[2]||fixed_tiles[3]!=spill[3])return 35;
        }
        if(merge_fixed_switch(0,0x0080-(unsigned)fixed_tiles,3,0)!=0x4567||
           spill[0]!=0x2b3d||spill[1]!=0x4d5e||spill[2]||spill[3])return 36;
    }
    fixed_tiles[5]=0x4567;fixed_tiles[6]=fixed_tiles[7]=0;
    merge_bounded_switch(2,65535,0,1);
    merge_bounded_switch(2,65535,1,0);
    if(fixed_tiles[6]||fixed_tiles[7])return 37;
    merge_bounded_switch(2,65535,1,1);
    if(fixed_tiles[5]!=0x4567||fixed_tiles[6]!=0x2b3c||fixed_tiles[7]!=0x4d5e)return 38;
    return 0;
}
