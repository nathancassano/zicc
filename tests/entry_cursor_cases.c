int matrix[4][16],small[4][3],global_value,hits;
unsigned short words[2][16];
unsigned char bytes[2][16];
long wide[2][4];
void reset(void){int i,j;for(i=0;i<4;i++)for(j=0;j<16;j++)matrix[i][j]=0;}
int expect(int row,int first,int last,int value)
{int i,j;for(i=0;i<4;i++)for(j=0;j<16;j++)if(matrix[i][j]!=(i==row&&j>=first&&j<last?value:0))return 0;return 1;}
void row_fill(int m[][16],int row,int value){int j;for(j=0;j<5;j++)m[row][j]=value;}
void column_fill(int m[][16],int col,int value){int i;for(i=0;i<3;i++)m[i][col]=value;}
void nonzero_start(int m[][16],int row,int value){int j;for(j=2;j<5;j++)m[row][j]=value;}
void negative_start_leaf(int m[][16],int row,int value){int j;for(j=-2;j<3;j++)m[row][2*j+5]=value;}
void negative_coefficient(int m[][16],int offset,int value){int j;for(j=0;j<3;j++)m[1][j-offset+4]=value;}
void doubled_row(int m[][16],int row,int value){int j;for(j=0;j<3;j++)m[row+row][j]=value;}
void small_stride(int m[][3],int row,int value){int j;for(j=0;j<3;j++)m[row][j]=value;}
void literal_value(int m[][16],int row){int j;for(j=0;j<3;j++)m[row][j]=0x1234;return;}
void stack_offset(int m[][16],int row,long ignored,int value){int j;for(j=0;j<3;j++)m[row][j]=value;}
void unsigned_value(unsigned short m[][16],int row,unsigned short value){int j;for(j=0;j<3;j++)m[row][j]=value;}
void empty_leaf(int m[][16],int row,int value){int j;for(j=5;j<3;j++)m[row][j]=value;}
void unsigned_start_leaf(int m[][16],int row,int value)
{unsigned short j;for(j=65530U;j<65535U;j++)m[row][(unsigned short)(j-65530U)]=value;}
void constant_address(int m[][16],int unused,int value){int j;for(j=2;j<5;j++)m[1][j]=value;}
void base_address(int m[][16],int unused,int value){int j;for(j=0;j<3;j++)m[0][j]=value;}
void costly_scale(int m[][16],int row,int value){int j;for(j=0;j<2;j++)m[row*2731][j]=value;}
void narrow_row(int m[][16],unsigned short row,int value){int j;for(j=0;j<3;j++)m[(unsigned char)row][j]=value;}
void global_reload(int m[][16],int row){int j;for(j=0;j<3;j++)m[row][j]=global_value;}
void extra_statement(int m[][16],int row,int value){int j;hits++;for(j=0;j<3;j++)m[row][j]=value;}
int visible_index(int m[][16],int row,int value){int j;for(j=0;j<3;j++)m[row][j]=value;return j;}
void byte_copy(unsigned char m[][16],int row,unsigned char value){int j;for(j=0;j<3;j++)m[row][j]=value;}
void wide_copy(long m[][4],int row,long value){int j;for(j=0;j<3;j++)m[row][j]=value;}

int visible_empty(int m[][16],int row,int value){int j;for(j=5;j<3;j++)m[row][j]=value;return j;}
unsigned short visible_unsigned(int m[][16],int row,int value){unsigned short j;for(j=65532U;j<65535U;j++)m[row][(unsigned short)(j-65532U)]=value;return j;}
int visible_negative(int m[][16],int row,int value){int j;for(j=-2;j<1;j++)m[row][j+2]=value;return j;}
void register_value(int m[][16],int row){int j;for(j=0;j<3;j++)m[row][j]=row;}
void byte_register(unsigned char m[][16],int row){int j;for(j=0;j<3;j++)m[row][j]=row;}
void wide_literal(long m[][4],int row){int j;for(j=0;j<3;j++)m[row][j]=0x89abcdefUL;}
void nested_byte(unsigned char m[][16],int value){int i,j;for(i=0;i<2;i++)for(j=0;j<3;j++)m[i][j]=value;}
void nested_wide(long m[][4],long value){int i,j;for(i=0;i<2;i++)for(j=0;j<2;j++)m[i][j]=value;}
void nested_negative(int m[][16],int value){int i,j;for(i=-1;i<1;i++)for(j=-2;j<1;j++)m[i+1][j+2]=value;}
void nested_empty(int m[][16],int value){int i,j;for(i=1;i<0;i++)for(j=0;j<3;j++)m[i][j]=value;}
void nested_large(int m[][16],int value){int i,j;for(i=0;i<4;i++)for(j=0;j<16;j++)m[i][j]=value;}
void staged_row(int m[][16],int row,int value){int j;hits++;for(j=0;j<3;j++)m[row][j]=value;}
void reused_row(int m[][16],int row,int value){int j;hits++;for(j=0;j<3;j++)m[row][j]=value;for(j=4;j<7;j++)m[row][j]=value+1;}
int *staged_add(int *p,int n){hits++;return p+n;}
int *staged_subtract(int *p,int n){hits++;return p-n;}
struct Six{int a,b,c;};struct Six structures[4];
struct Six *staged_scale(struct Six *p,int n){hits++;return p+n;}
int address_offset(int n){hits+=n;return 1;}
int *staged_call(int *p,int n){hits++;return p+address_offset(n);}
int main(void)
{
    int i,j;
    reset();row_fill(matrix,2,73);if(!expect(2,0,5,73))return 1;
    reset();row_fill(matrix+1,-1,61);if(!expect(0,0,5,61))return 2;
    reset();column_fill(matrix,2,47);
    for(i=0;i<4;i++)for(j=0;j<16;j++)if(matrix[i][j]!=(i<3&&j==2?47:0))return 3;
    reset();nonzero_start(matrix,1,51);if(!expect(1,2,5,51))return 4;
    reset();negative_start_leaf(matrix,2,53);
    for(i=0;i<4;i++)for(j=0;j<16;j++)if(matrix[i][j]!=(i==2&&j<10&&(j&1)?53:0))return 5;
    reset();negative_coefficient(matrix,3,59);if(!expect(1,1,4,59))return 6;
    reset();doubled_row(matrix,1,67);if(!expect(2,0,3,67))return 7;
    small_stride(small,2,71);
    for(i=0;i<4;i++)for(j=0;j<3;j++)if(small[i][j]!=(i==2?71:0))return 8;
    reset();literal_value(matrix,3);if(!expect(3,0,3,0x1234))return 9;
    reset();stack_offset(matrix,1,0x12345678L,83);if(!expect(1,0,3,83))return 10;
    unsigned_value(words,1,0xbeefU);
    for(i=0;i<2;i++)for(j=0;j<16;j++)if(words[i][j]!=(i==1&&j<3?0xbeefU:0))return 11;
    reset();empty_leaf((int (*)[16])0,32767,97);if(!expect(0,0,0,0))return 12;
    reset();unsigned_start_leaf(matrix,3,79);if(!expect(3,0,5,79))return 20;
    reset();constant_address(matrix,123,89);if(!expect(1,2,5,89))return 21;
    reset();base_address(matrix,123,97);if(!expect(0,0,3,97))return 22;
    reset();costly_scale(matrix,0,101);if(!expect(0,0,2,101))return 13;
    reset();narrow_row(matrix,257,103);if(!expect(1,0,3,103))return 14;
    reset();global_value=107;global_reload(matrix,1);if(!expect(1,0,3,107))return 15;
    reset();extra_statement(matrix,2,109);if(hits!=1||!expect(2,0,3,109))return 16;
    reset();if(visible_index(matrix,1,113)!=3||!expect(1,0,3,113))return 17;
    byte_copy(bytes,1,211);wide_copy(wide,1,0x12345678L);
    for(i=0;i<2;i++)for(j=0;j<16;j++)if(bytes[i][j]!=(i==1&&j<3?211:0))return 18;
    for(i=0;i<2;i++)for(j=0;j<4;j++)if(wide[i][j]!=(i==1&&j<3?0x12345678L:0))return 19;
    reset();if(visible_empty((int (*)[16])0,32767,3)!=5)return 26;
    if(visible_unsigned(matrix,1,127)!=65535U||!expect(1,0,3,127))return 27;
    reset();if(visible_negative(matrix,2,131)!=1||!expect(2,0,3,131))return 28;
    reset();register_value(matrix,2);if(!expect(2,0,3,2))return 23;
    byte_register(bytes,0);for(j=0;j<3;j++)if(bytes[0][j])return 24;
    wide_literal(wide,0);for(j=0;j<3;j++)if((unsigned long)wide[0][j]!=0x89abcdefUL)return 25;
    nested_byte(bytes,231);for(i=0;i<2;i++)for(j=0;j<3;j++)if(bytes[i][j]!=231)return 29;
    nested_wide(wide,0x76543210L);for(i=0;i<2;i++)for(j=0;j<2;j++)if(wide[i][j]!=0x76543210L)return 30;
    reset();nested_negative(matrix,137);for(i=0;i<4;i++)for(j=0;j<16;j++)if(matrix[i][j]!=(i<2&&j<3?137:0))return 31;
    nested_empty((int (*)[16])0,9);
    nested_large(matrix,139);for(i=0;i<4;i++)for(j=0;j<16;j++)if(matrix[i][j]!=139)return 32;
    reset();staged_row(matrix,2,149);if(!expect(2,0,3,149))return 33;
    reset();reused_row(matrix,1,151);for(i=0;i<4;i++)for(j=0;j<16;j++)if(matrix[i][j]!=(i==1&&j<3?151:i==1&&j>=4&&j<7?152:0))return 34;
    if(staged_add(matrix[0],3)!=&matrix[0][3]||staged_subtract(&matrix[0][5],2)!=&matrix[0][3])return 35;
    if(staged_add(&matrix[0][5],-2)!=&matrix[0][3]||staged_subtract(matrix[0],-3)!=&matrix[0][3])return 36;
    if(staged_scale(structures,3)!=&structures[3]||staged_scale(&structures[3],-2)!=&structures[1])return 37;
    if(staged_call(matrix[0],7)!=&matrix[0][1])return 38;
    return 0;
}
