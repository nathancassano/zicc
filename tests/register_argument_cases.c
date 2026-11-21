int hits;
int buffer[2];
int matrix[3][5];
int bump(int value){hits++;return value+1;}
int read_address(int *p){hits++;return *p;}
void unused_both(int first,int second){hits++;}
int unused_x(int discarded,int live){int saved=live;return bump(live)+saved;}
int unused_a(int live,int discarded){int saved=live;return bump(live)+saved;}
int unused_with_stack(int first,int second,long value){hits++;return (int)value;}
unsigned long unused_wide_return(int discarded,int live,unsigned long value)
{value+=(unsigned long)live;return value;}
int overwrite_both(int x,int a,int seed)
{
    int values[4];x=seed+2;a=bump(seed);
    values[0]=x;values[1]=a;values[2]=seed;values[3]=17;
    return values[0]+values[1]+values[2]+values[3];
}
int overwrite_x(int x,int a,int seed)
{
    int values[4];x=bump(seed);
    values[0]=x;values[1]=a;values[2]=seed;values[3]=17;
    return values[0]+values[1]+values[2]+values[3];
}
int overwrite_a(int x,int a,int seed)
{
    int values[4];a=bump(seed);
    values[0]=x;values[1]=a;values[2]=seed;values[3]=17;
    return values[0]+values[1]+values[2]+values[3];
}
int call_before_write(int x,int a,int seed)
{
    int values[4];bump(99);a=seed;
    values[0]=x;values[1]=a;values[2]=seed;values[3]=17;
    return values[0]+values[1]+values[2]+values[3];
}
int escaped_then_write(int x,int a)
{int saved;saved=read_address(&a);a=7;return saved+x+a;}
int escape_after_write(int x,int a)
{a=7;return read_address(&a)+x;}
int branch_write(int x,int a,int flag){if(flag)a=4;return x+a;}
int rhs_read(int x,int a,int seed){a=a+seed;return x+a;}
signed char overwrite_byte(signed char x,int discarded){x=-5;hits++;return x;}
int overwrite_pointer(int *p,int a,int seed)
{int values[4];p=buffer;p[0]=a;p[1]=seed;values[0]=a;values[1]=seed;values[2]=3;values[3]=4;return values[0]+values[1]+values[2]+values[3];}
void cursor_setup(int m[][5],int row,int value)
{int j;row=0;for(j=0;j<3;j++)m[row][j]=value;}

int branch_both(int x,int a,int flag)
{int pad[2];pad[0]=x;pad[1]=flag;hits++;if(flag)a=7;else a=11;return pad[0]+a;}
int branch_return(int x,int a,int flag){hits++;if(flag)return x;a=13;return x+a;}
int for_initializer(int x,int a,int n)
{int sum=0;hits++;for(a=0;a<n;a++)sum+=a;return x+a+sum;}
int do_write(int x,int a,int n){hits++;do{a=17;n--;}while(n>0);return x+a;}
int while_write(int x,int a,int n){hits++;while(n>0){a=19;n--;}return x+a;}
int do_break(int x,int a,int flag){hits++;do{if(flag)break;a=23;}while(0);return x+a;}
int do_continue(int x,int a,int flag)
{int n=2;hits++;do{n--;if(flag)continue;a=29;}while(n);return x+a;}
int branch_escape(int x,int a,int flag)
{int pad[2];pad[0]=x;pad[1]=flag;hits++;if(flag)a=31;else a=37;return read_address(&a)+pad[0];}
int branch_escape_early(int x,int a,int flag)
{int saved=0;hits++;if(flag)saved=read_address(&a);a=41;return saved+x+a;}
int do_escape(int x,int a,int n){hits++;do{a=43;n--;}while(n>0);return read_address(&a)+x;}
int for_escape(int x,int a,int n){hits++;for(a=0;a<n;a++)hits++;return read_address(&a)+x;}
int condition_read(int x,int a){hits++;if(a)a=53;else a=59;return x+a;}

void cursor_late(int m[][5],int row,int value)
{int j;hits++;if(value>0)row=0;else row=1;for(j=0;j<3;j++)m[row][j]+=value;}
int main(void)
{
    int i,j,before;
    for(i=0;i<16;i++){
        before=hits;unused_both(bump(2),bump(3));if(hits!=before+3)return 1;
        before=hits;if(unused_x(bump(1),7)!=15||hits!=before+2)return 2;
        if(unused_a(9,123)!=19)return 3;
        if(unused_with_stack(111,222,1234L)!=1234)return 4;
        if(unused_wide_return(999,7,0x89abcdefUL)!=0x89abcdf6UL)return 5;
        if(overwrite_both(101,202,5)!=35)return 6;
        if(overwrite_x(101,13,5)!=41)return 7;
        if(overwrite_a(7,202,5)!=35)return 8;
        if(call_before_write(7,202,3)!=30)return 9;
        if(escaped_then_write(3,29)!=39||escape_after_write(3,29)!=10)return 10;
        if(branch_write(3,9,0)!=12||branch_write(3,9,1)!=7)return 11;
        if(rhs_read(3,9,5)!=17)return 12;
        if(overwrite_byte(127,123)!=-5)return 13;
        if(overwrite_pointer(0,11,13)!=31||buffer[0]!=11||buffer[1]!=13)return 14;
        cursor_setup(matrix,2,73);
        for(j=0;j<5;j++)if(matrix[0][j]!=(j<3?73:0)||matrix[1][j]||matrix[2][j])return 15;
        for(j=0;j<2;j++){
            if(branch_both(3,100,j)!=(j?10:14)||branch_return(3,100,j)!=(j?3:16))return 16;
            if(do_break(3,100,j)!=(j?103:26)||do_continue(3,100,j)!=(j?103:32))return 17;
            if(branch_escape(3,100,j)!=(j?34:40)||branch_escape_early(3,100,j)!=(j?144:44))return 18;
        }
        for(j=0;j<5;j++){
            if(for_initializer(3,100,j)!=3+j+j*(j-1)/2||for_escape(3,100,j)!=3+j)return 19;
            if(do_write(3,100,j)!=20||do_escape(3,100,j)!=46)return 20;
            if(while_write(3,100,j)!=(j?22:103))return 21;
        }
        cursor_late(matrix,32767,5);cursor_late(matrix,-32768,-2);
        for(j=0;j<5;j++)if(matrix[0][j]!=(j<3?78:0)||matrix[1][j]!=(j<3?-2:0))return 23;
        for(j=0;j<5;j++){matrix[0][j]=0;matrix[1][j]=0;}
        if(condition_read(3,100)!=56||condition_read(3,0)!=62)return 22;
    }
    return 0;
}
