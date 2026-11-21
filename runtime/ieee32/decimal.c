// Reference implementation for host and differential tests; ROM builds use assembly
// Exact midpoint parsing and precision-controlled formatting
#include <ctype.h>
#include <errno.h>
#ifdef ZICC_ALL_C_REFERENCE
#define ZICC_C_MATCH_REFERENCE 1
#define ZICC_C_RENDER_REFERENCE 1
#define ZICC_C_ROUNDED_REFERENCE 1
#define ZICC_C_HEXVAL_REFERENCE 1
#define ZICC_C_DEC_COPY_REFERENCE 1
#define ZICC_C_EXPONENT_REFERENCE 1
#define ZICC_C_DEC_FORMAT_RAW_REFERENCE 1
#define ZICC_C_DEC_FORMAT_REFERENCE 1
#define ZICC_C_IEEE_DECIMAL_REFERENCE 1
#define ZICC_C_IEEE_DECIMAL_COMPARE_REFERENCE 1
#define ZICC_C_HEXPARSE_REFERENCE 1
#define ZICC_C_IEEE_PARSE_REFERENCE 1
#define ZICC_C_DEC_FORMAT_SPEC_REFERENCE 1
#endif
typedef unsigned long U32;
extern const U32 decade_floor[88];
static char dec_digits[200];
static int dec_n,dec_scale;
static char dec_output[80];
#if !defined(__ZICC__) || defined(ZICC_C_DEC_COPY_REFERENCE)
static void dec_copy(char *to,const char * __far from)
{
    while(*from){*to=*from;to++;from++;}
    *to=0;
}
#else
void decimal__dec_copy(char *to,const char * __far from);
#define dec_copy decimal__dec_copy
#endif
#if !defined(__ZICC__) || defined(ZICC_C_IEEE_DECIMAL_REFERENCE)
void __ieee_decimal(U32 m,int e)
{
    int i,carry,t,count;U32 q;
    if(!m){dec_n=1;dec_scale=0;dec_digits[0]=0;return;}
    /* Cancel dyadic factors before the expensive decimal expansion. Odd
     * parse midpoints bypass this path; consumers pad absent decimal zeros. */
    if(!(m&1)){
        while(e<=-8&&!(m&255)){m>>=8;e+=8;}
        while(e<0&&!(m&1)){m>>=1;++e;}
    }
    dec_n=0;dec_scale=e<0?-e:0;
    /* m-10*q is 0..9. Its low word is exact even when 10*q
     * exceeds 16 bits, so the constant multiply needs no U32 helper. */
    do{q=m/10;dec_digits[dec_n++]=(unsigned char)((unsigned)m-(unsigned)q*10U);m=q;}while(m);
    if(e<0){
        count=-e;
        while(count--){
            carry=0;
            for(i=0;i<dec_n;i++){
                t=dec_digits[i];
                dec_digits[i]=(unsigned char)((t&1?5:0)+carry);carry=t>>1;
            }
            if(carry)dec_digits[dec_n++]=(unsigned char)carry;
        }
    }else{
        count=e;
        while(count--){
            carry=0;
            for(i=0;i<dec_n;i++){
                t=dec_digits[i]*2+carry;carry=t>=10;if(carry)t-=10;dec_digits[i]=(unsigned char)t;
            }
            if(carry)dec_digits[dec_n++]=(unsigned char)carry;
        }
    }
}
#else
void __ieee_decimal(U32 m,int e);
#endif

#if !defined(__ZICC__) || defined(ZICC_C_MATCH_REFERENCE)
static int match(const char * __far s,const char * __far word)
{
    int n=0;while(word[n]){if(tolower((unsigned char)s[n])!=word[n])return 0;++n;}return n;
}
#else
int decimal__match(const char * __far s,const char * __far word);
#define match decimal__match
#endif

#if !defined(__ZICC__) || defined(ZICC_C_IEEE_DECIMAL_COMPARE_REFERENCE)
int __ieee_decimal_compare(const char * __far p,const char * __far end,long exponent)
{
    int q=dec_n-dec_scale,i,a,b;
    if(exponent!=q)return exponent<q?-1:1;
    for(i=0;p<end||i<dec_n;){
        while(p<end&&*p=='.')++p;
        a=p<end?*p++-'0':0;b=i<dec_n?dec_digits[dec_n-1-i]:0;
        if(a!=b)return a<b?-1:1;
        if(i<dec_n)++i;
    }
    return 0;
}
#else
int __ieee_decimal_compare(const char * __far p,const char * __far end,long exponent);
#endif

#if !defined(__ZICC__) || defined(ZICC_C_HEXVAL_REFERENCE)
static int hexval(int c)
{
    if(c>='0'&&c<='9')return c-'0';
    c=tolower(c);return c>='a'&&c<='f'?c-'a'+10:-1;
}
#else
int decimal__hexval(int c);
#define hexval decimal__hexval
#endif

#if !defined(__ZICC__) || defined(ZICC_C_HEXPARSE_REFERENCE)
static U32 hexparse(const char * __far p,char * __far *endptr,int sign)
{
    const char * __far start=p,* __far ep;U32 m=0,tail,half;long exponent=0,frac=0,rest=0,step;
    int n=0,dot=0,seen=0,sticky=0,k,es=1,nbits=0,shift;U32 t;
    p+=2;
    for(;;){
        if(*p=='.'&&!dot){dot=1;++p;continue;}
        k=hexval((unsigned char)*p);if(k<0)break;
        seen=1;if(dot)++frac;
        if(m||k||n){if(n<8){m=(m<<4)|(unsigned)k;++n;}else{++rest;sticky|=k;}}
        ++p;
    }
    if(!seen){if(endptr)*endptr=(char * __far )(start+1);return sign?0x80000000UL:0;}
    if(*p=='p'||*p=='P'){
        ep=p++;if(*p=='+'||*p=='-'){es=*p=='-'?-1:1;++p;}
        if(!isdigit((unsigned char)*p))p=ep;
        else {while(isdigit((unsigned char)*p)){if(exponent<10000)exponent=exponent*10+*p-'0';++p;}exponent*=es;}
    }
    if(endptr)*endptr=(char * __far )p;
    if(!m)return sign?0x80000000UL:0;
    exponent+=4*(rest-frac);t=m;while(t){++nbits;t>>=1;}
    if(exponent+nbits>129){errno=ERANGE;return (sign?0x80000000UL:0)|0x7f800000UL;}
    step=exponent+nbits-24;if(step< -149)step=-149;
    if(step-exponent>32){errno=ERANGE;return sign?0x80000000UL:0;}
    shift=(int)(step-exponent);
    if(shift>0){
        half=1UL<<(shift-1);tail=shift==32?m:m&((1UL<<shift)-1);m=shift==32?0:m>>shift;
        if(tail>half||(tail==half&&(sticky||(m&1))))++m;
    }else if(shift<0)m<<=-shift;
    if(m==0x1000000UL){m>>=1;++step;}
    if(step>104){errno=ERANGE;return (sign?0x80000000UL:0)|0x7f800000UL;}
    return (sign?0x80000000UL:0)|(m<0x800000UL?m:((U32)(step+150)<<23)|(m&0x7fffffUL));
}
#else
U32 decimal__hexparse(const char * __far p,char * __far *endptr,int sign);
#define hexparse decimal__hexparse
#endif

#if !defined(__ZICC__) || defined(ZICC_C_IEEE_PARSE_REFERENCE)
U32 __ieee_parse(const char * __far text,char * __far *endptr)
{
    const char * __far p=text,* __far first=0,* __far end,* __far ep;int sign=0,dot=0,seen=0,es=1,c,k;
    long frac=0,count=0,ex=0;
    U32 lo=0,hi=0x7f800000UL,mid,m;
    while(isspace((unsigned char)*p))++p;
    if(*p=='+'||*p=='-'){sign=*p=='-';++p;}
    if(p[0]=='0'&&(p[1]=='x'||p[1]=='X'))return hexparse(p,endptr,sign);
    if((k=match(p,"inf"))!=0){p+=k;if(match(p,"inity"))p+=5;if(endptr)*endptr=(char * __far )p;return (sign?0x80000000UL:0)|0x7f800000UL;}
    if((k=match(p,"nan"))!=0){
        p+=k;if(*p=='('){ep=p+1;while(isalnum((unsigned char)*ep)||*ep=='_')++ep;if(*ep==')')p=ep+1;}
        if(endptr)*endptr=(char * __far )p;return 0x7fc00000UL;
    }
    while(*p){
        c=(unsigned char)*p;
        if(c=='.'&&!dot){dot=1;++p;continue;}
        if(c<'0'||c>'9')break;
        seen=1;if(dot)++frac;
        if(c!='0'||first){if(!first)first=p;++count;}
        ++p;
    }
    end=p;
    if(!seen){if(endptr)*endptr=(char * __far )text;return 0;}
    if(*p=='e'||*p=='E'){
        ep=p++;if(*p=='+'||*p=='-'){es=*p=='-'?-1:1;++p;}
        if(!isdigit((unsigned char)*p))p=ep;
        else{while(isdigit((unsigned char)*p)){if(ex<100000L)ex=ex*10+*p-'0';++p;}ex*=es;}
    }
    if(endptr)*endptr=(char * __far )p;
    if(!first)return sign?0x80000000UL:0;
    /* Every integer through 2^24 is exactly representable. Avoid midpoint
     * search for this common case; larger and fractional inputs retain the
     * exact original path. Accumulate with shifts, without multiply calls. */
    if(!dot&&!frac&&!ex&&count<=8){
        const char * __far q=first;U32 v=0;int e=150;
        while(q<end){v=(v<<3)+(v<<1)+(unsigned)(*q-'0');++q;}
        if(v&&v<=0x1000000UL){
            while(v<0x800000UL){v<<=1;--e;}
            if(v==0x1000000UL){v>>=1;++e;}
            return ((U32)e<<23)|(v&0x7fffffUL)|(sign?0x80000000UL:0);
        }
    }
    ex+=count-frac;
    if(ex>40){errno=ERANGE;return (sign?0x80000000UL:0)|0x7f800000UL;}
    if(ex< -46){errno=ERANGE;return sign?0x80000000UL:0;}
    lo=decade_floor[(int)ex+46];hi=decade_floor[(int)ex+47]+1;
    while(lo<hi){
        int e,r;
        mid=lo+((hi-lo)>>1);e=(int)(mid>>23);
        m=mid&0x7fffffUL;if(e)m|=0x800000UL;else e=1;
        __ieee_decimal(m*2+1,e-151);
        r=__ieee_decimal_compare(first,end,ex);
        if(r>0||(r==0&&(mid&1)))lo=mid+1;else hi=mid;
    }
    if(lo==0x7f800000UL||lo<0x800000UL)errno=ERANGE;
    return lo|(sign?0x80000000UL:0);
}
#else
U32 __ieee_parse(const char * __far text,char * __far *endptr);
#endif

#if !defined(__ZICC__) || defined(ZICC_C_ROUNDED_REFERENCE)
static void rounded(int keep,char *digits,int *length,int *exp)
{
    int i,n=dec_n,round=0,sticky=0,index=n-keep-1;
    *exp=n-dec_scale-1;
    if(keep<0){digits[0]='0';*length=1;return;}
    if(keep<n){
        int next=index>=0?dec_digits[index]:0;
        for(i=0;i<index;i++)sticky|=dec_digits[i];
        round=next>5||(next==5&&(sticky||(keep>0&&(dec_digits[n-keep]&1))));
    }
    if(keep==0){digits[0]=round?'1':'0';*length=1;if(round)++*exp;return;}
    *length=keep;
    for(i=0;i<keep;i++)digits[i]=i<n?(char)('0'+dec_digits[n-1-i]):'0';
    if(round){
        for(i=keep-1;i>=0&&digits[i]=='9';i--)digits[i]='0';
        if(i>=0)++digits[i];else{digits[0]='1';++*exp;}
    }
}
#else
void decimal__rounded(int keep,char *digits,int *length,int *exp);
#define rounded decimal__rounded
#endif

#if !defined(__ZICC__) || defined(ZICC_C_EXPONENT_REFERENCE)
static char *exponent(char *p,int e,int upper)
{
    char rev[6];int n=0;
    *p++=upper?'E':'e';*p++=e<0?'-':'+';if(e<0)e=-e;
    do{rev[n++]=(char)('0'+e%10);e/=10;}while(e);
    while(n<2)rev[n++]='0';while(n)*p++=rev[--n];return p;
}
#else
char *decimal__exponent(char *p,int e,int upper);
#define exponent decimal__exponent
#endif

#if !defined(__ZICC__) || defined(ZICC_C_RENDER_REFERENCE)
static char *render(char *p,const char * __far digits,int n,int e,int spec,int precision,int alt)
{
    int i,after,upper=spec>='A'&&spec<='Z';spec=tolower(spec);
    if(spec=='g'){
        if(!alt)while(n>1&&digits[n-1]=='0')--n;
        if(e< -4||e>=precision){spec='e';precision=(alt?precision:n)-1;}else{spec='f';precision=(alt?precision:n)-e-1;if(precision<0)precision=0;}
    }
    if(spec=='e'){
        *p++=digits[0];if(precision||alt)*p++='.';
        for(i=0;i<precision;i++)*p++=i+1<n?digits[i+1]:'0';
        return exponent(p,e,upper);
    }
    if(e<0)*p++='0';else for(i=0;i<=e;i++)*p++=i<n?digits[i]:'0';
    after=precision;if(after||alt)*p++='.';
    for(i=1;i<=after;i++){int k=e+i;*p++=k>=0&&k<n?digits[k]:'0';}
    return p;
}
#else
char *decimal__render(char *p,const char * __far digits,int n,int e,int spec,int precision,int alt);
#define render decimal__render
#endif

#if !defined(__ZICC__) || defined(ZICC_C_DEC_FORMAT_RAW_REFERENCE)
static int dec_format_raw_spec(char *text,U32 x,int spec,int precision)
{
    char digits[80],*p=text;int e,n,keep,alt=0,upper=0;
    U32 a=x&0x7fffffffUL,m=a&0x7fffffUL;int b=(int)(a>>23);
    if(x>>31)*p++='-';
    if(a>=0x7f800000UL){dec_copy(p,a>0x7f800000UL?(upper?"NAN":"nan"):(upper?"INF":"inf"));return (int)(p-text)+3;}
    if(b)m|=0x800000UL;else b=1;
    __ieee_decimal(m,b-150);
    if(!a){dec_n=1;dec_scale=0;dec_digits[0]=0;}
    e=dec_n-dec_scale-1;
    if(tolower(spec)=='g'&&!precision)precision=1;
    keep=tolower(spec)=='f'?dec_n-dec_scale+precision:tolower(spec)=='e'?precision+1:precision;
    rounded(keep,digits,&n,&e);
    p=render(p,digits,n,e,spec,precision,alt);*p=0;
    return (int)(p-text);
}
#else
int decimal__dec_format_raw_spec(char *text,U32 x,int spec,int precision);
#define dec_format_raw_spec decimal__dec_format_raw_spec
#endif

#if !defined(__ZICC__) || defined(ZICC_C_DEC_FORMAT_REFERENCE)
char * __far dec_format(U32 bits)
{
    char local[80];int i;
    dec_format_raw_spec(local,bits,'g',6);
    for(i=0;;i++){dec_output[i]=local[i];if(!local[i])break;}
    return dec_output;
}
#else
char * __far dec_format(U32 bits);
#endif

/* The console bounds precision to 0..32 before entering this routine */
#if !defined(__ZICC__) || defined(ZICC_C_DEC_FORMAT_SPEC_REFERENCE)
char * __far dec_format_spec(U32 bits,int spec,int precision)
{
    char local[80];int i;
    dec_format_raw_spec(local,bits,spec,precision);
    for(i=0;;i++){dec_output[i]=local[i];if(!local[i])break;}
    return dec_output;
}
#else
char * __far dec_format_spec(U32 bits,int spec,int precision);
#endif
