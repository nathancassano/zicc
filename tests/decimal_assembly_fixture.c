/* Inputs are supplied at execution time; kernels are linked as separate units */
typedef unsigned long U32;
int decimal__hexval(int);
void decimal__dec_copy(char *,const char * __far);
char *decimal__exponent(char *,int,int);
char * __far dec_format(U32);
char * __far dec_format_spec(U32,int,int);
char * __far fixture_dec_format_call(U32);
int decimal__dec_format_raw(char *,U32);
int fixture_dec_format_raw_call(char *,U32);
void __ieee_decimal(U32,int);
void fixture_decimal_call(U32,int);
int __ieee_decimal_compare(const char * __far,const char * __far,long);
U32 decimal__hexparse(const char * __far,char * __far *,int);
U32 __ieee_parse(const char * __far,char * __far *);

unsigned running=1,operation,input_word,flag,result_word;
U32 input_long,result_long;
char *output;
const char * __far source,* __far limit;
char * __far *endptr;
void fixture_before(void);
void fixture_after(void);

int main(void)
{
    while(running){
        fixture_before();
        result_word=0;result_long=0;
        switch(operation){
        case 0:result_word=decimal__hexval((int)input_word);break;
        case 1:decimal__dec_copy(output,source);break;
        case 2:result_word=(unsigned)decimal__exponent(output,(int)input_word,flag);break;
        case 3:result_long=(unsigned long)fixture_dec_format_call(input_long);result_word=(unsigned)result_long;break;
        case 4:result_word=fixture_dec_format_raw_call(output,input_long);break;
        case 5:fixture_decimal_call(input_long,(int)input_word);break;
        case 6:result_word=__ieee_decimal_compare(source,limit,(long)input_long);break;
        case 7:result_long=decimal__hexparse(source,endptr,flag);break;
        case 8:result_long=__ieee_parse(source,endptr);break;
        case 9:result_long=(unsigned long)dec_format_spec(input_long,(int)input_word,(int)flag);result_word=(unsigned)result_long;break;
        }
        fixture_after();
    }
    return 0;
}
