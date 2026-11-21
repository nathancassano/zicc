int words[2][80], global_value;
unsigned char bytes[2][80];
long wide[2][80];
float real[2][8];
unsigned char large[2][2304];
int column[80][5];
void reset(void)
{
    int i,j;
    for(i=0;i<2;i++) for(j=0;j<80;j++) {
        words[i][j]=-99;
        bytes[i][j]=19;
        wide[i][j]=0x11111111L;
    }
}
int fill(int m[][80],int n,int value)
{
    int j;
    for(j=0;j<n;j++) m[1][j]=value;
    return j;
}
int indices(int m[][80],int start,int end)
{
    int j;
    for(j=start;j<end;j++) m[1][j]=j;
    return j;
}
void byte_fill(unsigned char m[][80],int n,unsigned char value)
{
    int j;
    for(j=0;j<n;j++) m[1][j]=value;
}
void wide_fill(long m[][80],int n,long value)
{
    int j;
    for(j=0;j<n;j++) m[1][j]=value;
}
void real_fill(float m[][8],int n,float value)
{
    int j;
    for(j=0;j<n;j++) m[1][j]=value;
}
void large_fill(unsigned char m[][2304],int n,unsigned char value)
{
    int j;
    for(j=0;j<n;j++)m[1][j]=value;
}
int column_fill(int m[][5],int n,int value)
{
    int i;
    for(i=0;i<n;i++)m[i][2]=value;
    return i;
}
void five_reloads(int m[][80])
{
    int j;
    for(j=0;j<5;j++) m[1][j]=global_value;
}
int negative_start(int m[][80],int value)
{
    int j;
    for(j=-3;j<2;j++) m[1][j+3]=value;
    return j;
}
int affine_start(int m[][80],int row,int value)
{
    int j;
    for(j=-2;j<3;j++)m[row][2*j+5]=value;
    return j;
}
void dead_empty(int m[][80]){int j;for(j=5;j<3;j++)m[1][j]=77;}
void dynamic_offset(int m[][80],int offset){int j;for(j=0;j<5;j++)m[1][j+offset]=61;}
void cast_start(int m[][80]){int j;for(j=(int)(unsigned short)0;j<2;j++)m[j][1]=29;}
struct HomeGuard {char c;long wide;};
int guard_ok(struct HomeGuard *p){return p->c==7&&p->wide==0x12345678L;}
int retained_objects(int m[][80],int value)
{
    int j;struct HomeGuard guard;long extra;int array[3];
    guard.c=7;guard.wide=0x12345678L;extra=0x23456789L;
    array[0]=11;array[1]=23;array[2]=37;
    for(j=0;j<5;j++)m[1][j]=value;
    if(!guard_ok(&guard)||extra!=0x23456789L)return 0;
    return array[0]+array[1]+array[2]==71;
}
unsigned long wide_after(int m[][80],unsigned long value)
{int j;for(j=0;j<3;j++)m[1][j]=17;return value;}
int recursive_after(int m[][80],int n)
{int j;for(j=0;j<3;j++)m[1][j]=n;if(n)return recursive_after(m,n-1)+n;return 0;}
int short_zero(int m[][80]){int j;for(j=0;j<0;j++)m[1][j]=77;return j;}
int short_one(int m[][80]){int j;for(j=2;j<3;j++)m[1][j]=77;return j;}
int short_two(int m[][80]){int j;for(j=0;j<2;j++)m[1][j]=j;return j;}
int wrapped_start(int m[][80])
{
    unsigned short j;
    for(j=65530U;j<65535U;j++)m[1][(unsigned short)(j-65530U)]=(int)j;
    return j==65535U;
}
void fixed_32(int m[][80],int value)
{
    int j;
    for(j=0;j<32;j++) m[1][j]=value;
}
void fixed_33(int m[][80],int value)
{
    int j;
    for(j=0;j<33;j++) m[1][j]=value;
}
void reverse(int m[][80],int value)
{
    int j;
    for(j=0;j<8;j++) m[1][79-j]=value;
}
int main(void)
{
    int n,i,j;
    for(n=0;n<=65;n++) {
        reset();
        if(fill(words,n,123)!=n) return 1;
        byte_fill(bytes,n,211);
        wide_fill(wide,n,0x12345678L);
        for(i=0;i<2;i++) for(j=0;j<80;j++) {
            if(i==1 && j<n) {
                if(words[i][j]!=123 || bytes[i][j]!=211 || wide[i][j]!=0x12345678L) return 2;
            } else if(words[i][j]!=-99 || bytes[i][j]!=19 || wide[i][j]!=0x11111111L) return 3;
        }
        reset();
        if(indices(words,3,n+3)!=n+3) return 4;
        for(i=0;i<2;i++) for(j=0;j<80;j++) {
            if(i==1 && j>=3 && j<n+3) { if(words[i][j]!=j) return 5; }
            else if(words[i][j]!=-99) return 6;
        }
    }
    if(indices(words,5,-1)!=5) return 7;
    for(n=0;n<=8;n++) {
        for(i=0;i<2;i++) for(j=0;j<8;j++) real[i][j]=0.0;
        real_fill(real,n,-2.5);
        for(i=0;i<2;i++) for(j=0;j<8;j++) {
            if(i==1 && j<n) { if(real[i][j]!=-2.5) return 8; }
            else if(real[i][j]!=0.0) return 9;
        }
    }
    reset();global_value=31;five_reloads(words);
    for(j=0;j<80;j++) if(words[1][j]!=(j<5?31:-99)) return 10;
    reset();if(negative_start(words,71)!=2) return 11;
    for(j=0;j<80;j++) if(words[1][j]!=(j<5?71:-99)) return 12;
    reset();if(short_zero(words)!=0||words[1][0]!=-99) return 16;
    if(short_one(words)!=3||words[1][2]!=77||words[1][1]!=-99) return 17;
    reset();if(short_two(words)!=2||words[1][0]!=0||words[1][1]!=1||words[1][2]!=-99) return 18;
    reset();if(!wrapped_start(words)) return 19;
    for(j=0;j<5;j++)if((unsigned short)words[1][j]!=65530U+j) return 20;
    if(words[1][5]!=-99) return 21;
    reset();if(affine_start(words,1,53)!=3)return 27;
    for(i=0;i<2;i++)for(j=0;j<80;j++)
        if(words[i][j]!=(i==1&&j<10&&(j&1)?53:-99))return 28;
    reset();dead_empty(words);if(words[1][5]!=-99)return 29;
    dynamic_offset(words,3);
    for(j=0;j<80;j++)if(words[1][j]!=(j>=3&&j<8?61:-99))return 30;
    reset();cast_start(words);
    if(words[0][1]!=29||words[1][1]!=29)return 31;
    reset();if(!retained_objects(words,43)||words[1][4]!=43)return 32;
    if(wide_after(words,0x89abcdefUL)!=0x89abcdefUL||words[1][2]!=17)return 33;
    if(recursive_after(words,4)!=10||words[1][2]!=0)return 34;
    reset();fixed_32(words,17);
    for(j=0;j<80;j++) if(words[1][j]!=(j<32?17:-99)) return 13;
    reset();fixed_33(words,21);
    for(j=0;j<80;j++) if(words[1][j]!=(j<33?21:-99)) return 14;
    reset();reverse(words,41);
    for(j=0;j<80;j++) if(words[1][j]!=(j>=72?41:-99)) return 15;
    for(n=2303;n<=2304;n++){
        for(i=0;i<2;i++)for(j=0;j<2304;j++)large[i][j]=0;
        large_fill(large,n,211);
        for(i=0;i<2;i++)for(j=0;j<2304;j++){
            if(i==1&&j<n){if(large[i][j]!=211)return 22;}
            else if(large[i][j]!=0)return 23;
        }
    }
    for(n=0;n<=80;n++){
        for(i=0;i<80;i++)for(j=0;j<5;j++)column[i][j]=-99;
        if(column_fill(column,n,43)!=n)return 24;
        for(i=0;i<80;i++)for(j=0;j<5;j++){
            if(i<n&&j==2){if(column[i][j]!=43)return 25;}
            else if(column[i][j]!=-99)return 26;
        }
    }
    return 0;
}
