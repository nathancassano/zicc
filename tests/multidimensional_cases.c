typedef int Row[5];
typedef Row Matrix[3];
Matrix a;
int cube[2][3][5];
char bytes[3][5];
long wide[3][5];
struct Cell { int x; char y; };
struct Cell cells[3][5];
struct Holder { char before; Matrix data; int after; } holder;
const int image[2][3]={{1,2,3},{4,5}};
int *pointers[2][3];
typedef int (*RowPointer)[5];
int calls_i, calls_j;
int next_i(void) { calls_i++; return 1; }
int next_j(void) { calls_j++; return 2; }
int parameter(int m[99][5], int i, int j);
int alias_parameter(int (*m)[5], int i, int j);
int parameter(int m[][5], int i, int j) { return m[i][j]; }
int parameter_size(int m[][5]) { return sizeof(m)==sizeof(int (*)[5]); }
int explicit_parameter(int m[3][5], int i, int j) { return m[i][j]; }
int alias_parameter(Matrix m, int i, int j) { return m[i][j]; }
int row_parameter(Row m) { return m[2]; }
int const_parameter(const int m[][5]) { return m[1][2]; }
int pointer_parameter(int (*m)[5], int i, int j) { return m[i][j]; }
void across_row(int m[][5], int row, int value)
{
    int j;
    for(j=0;j<5;j++) m[row][j]=value;
}
void down_column(int m[][5], int col, int value)
{
    int i;
    for(i=0;i<3;i++) m[i][col]=value;
}
void nested_rows(int m[][5], int value)
{
    int i,j;
    for(i=0;i<3;i++) for(j=0;j<5;j++) m[i][j]=value;
}
void nested_columns(int m[][5], int value)
{
    int i,j;
    for(j=0;j<5;j++) for(i=0;i<3;i++) m[i][j]=value;
}
int main(void)
{
    typedef int LocalMatrix[3][5];
    LocalMatrix local;
    RowPointer alias_row;
    Row *row;
    int (*matrix)[3][5];
    int *element;
    int i,j,k;
    for(i=0;i<3;i++) for(j=0;j<5;j++) {
        a[i][j]=i*10+j;
        local[i][j]=100+i*10+j;
        bytes[i][j]=i*10+j;
        wide[i][j]=100000L+i*10+j;
        cells[i][j].x=i*10+j;
        cells[i][j].y=j;
        holder.data[i][j]=i*10+j;
    }
    i=1;j=2;
    if(a[1][2]!=12 || a[i][2]!=12 || a[1][j]!=12 || a[i][j]!=12) return 1;
    if(local[i][j]!=112 || bytes[i][j]!=12 || wide[i][j]!=100012L) return 2;
    if((*(&holder.data))[1][2]!=12) return 20;
    if(cells[i][j].x!=12 || cells[i][j].y!=2 || holder.data[i][j]!=12) return 3;
    if(!parameter_size(a)) return 23;
    if(parameter(a,i,j)!=12 || explicit_parameter(a,i,j)!=12 || alias_parameter(a,i,j)!=12) return 4;
    if(const_parameter(a)!=12) return 19;
    if(row_parameter(a[i])!=12 || pointer_parameter(a,i,j)!=12) return 5;
    row=&a[0]; row++;
    if(row-&a[0]!=1 || &a[0]-row!=-1) return 18;
    if((*row)[2]!=12 || row[1][4]!=24 || row!=&a[1]) return 6;
    alias_row=a;
    if(alias_row[2][4]!=24) return 21;
    pointers[1][2]=&a[1][2];
    if(*pointers[1][2]!=12) return 22;
    matrix=&a; element=(*matrix)[1];
    if(element[2]!=12 || &a[1][2]!=&row[0][2]) return 7;
    a[next_i()][next_j()] += 7;
    if(calls_i!=1 || calls_j!=1 || a[1][2]!=19) return 8;
    a[i++][j++]++;
    if(i!=2 || j!=3 || a[1][2]!=20) return 9;
    for(i=0;i<2;i++) for(j=0;j<3;j++) for(k=0;k<5;k++) cube[i][j][k]=i*100+j*10+k;
    i=1;j=2;k=4;
    if(cube[i][j][k]!=124 || cube[1][2][4]!=124) return 10;
    if(image[0][2]!=3 || image[1][1]!=5 || image[1][2]!=0) return 11;
    if(sizeof(a)!=15*sizeof(int) || sizeof(a[1])!=5*sizeof(int) || sizeof(a[1][2])!=sizeof(int)) return 12;
    if(sizeof(int[3][5])!=sizeof(a) || sizeof(int (*)[5])!=sizeof(row)) return 13;
    nested_rows(a,7);
    across_row(a,1,8);
    down_column(a,2,9);
    for(i=0;i<3;i++) for(j=0;j<5;j++) {
        if(j==2) { if(a[i][j]!=9) return 14; }
        else if(i==1) { if(a[i][j]!=8) return 15; }
        else if(a[i][j]!=7) return 16;
    }
    nested_columns(a,11);
    for(i=0;i<3;i++) for(j=0;j<5;j++) if(a[i][j]!=11) return 17;
    return 0;
}
