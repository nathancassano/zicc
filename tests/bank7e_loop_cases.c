#ifdef _MSC_VER
#define __far
#endif
unsigned short padding[12456];
int high[4][16],hits;
unsigned char byte_data[2][16];
long wide_data[2][4];
struct Triple {int a,b,c;};
const struct Triple rom[3]={{11,13,17},{19,23,29},{31,37,41}};
struct Pack {int a[3];long z;};struct Pack source_pack,destination_pack;
void clear_high(void){int i,j;for(i=0;i<4;i++)for(j=0;j<16;j++)high[i][j]=0;}
void bank7e_row(int m[][16],int row,int value){int j;for(j=0;j<5;j++)m[row][j]=value;}
void bank7e_nested(int m[][16],int value){int i,j;for(i=0;i<4;i++)for(j=0;j<3;j++)m[i][j]=value;}
int bank7e_runtime(int m[][16],int n,int value){int j;for(j=0;j<n;j++)m[1][j]=value;return j;}
void bank7e_byte(unsigned char m[][16],int row,int value){int j;for(j=0;j<3;j++)m[row][j]=value;}
void bank7e_wide(long m[][4],int row,long value){int j;for(j=0;j<3;j++)m[row][j]=value;}
void far_matrix(int (* __far m)[16],int row,int value){int j;for(j=0;j<3;j++)m[row][j]=value;}
int far_word_home(int * __far p,int a,int seed){int local[2];a=seed;local[0]=a;local[1]=*p;return local[0]+local[1];}
long mixed_bank(int discarded,int live,int * __far p,long extra)
{int local[2];local[0]=live;local[1]=*p;return (long)local[0]+local[1]+extra;}
int fetch_index(int i){hits++;return i;}
int named_far_scaled(int i){hits++;return rom[fetch_index(i)].b;}
void switch_loops(int m[][16],int row,int value,int flag)
{int j;switch(flag){case 1:for(j=0;j<3;j++)m[row][j]=value;break;default:for(j=2;j<5;j++)m[row][j]=value;break;}}
int copy_mix(int m[][16],int row,int value)
{int j;for(j=0;j<3;j++)m[row][j]=value;destination_pack=source_pack;return (destination_pack=source_pack).a[1]+m[row][2];}
int main(void)
{
 int i,j,n,before; padding[8999]=0x5a;
#ifndef _MSC_VER
 if((unsigned long)(int * __far)high<0x7e6000UL)return 1;
#endif
 clear_high();bank7e_row(high,3,73);
 for(i=0;i<4;i++)for(j=0;j<16;j++)if(high[i][j]!=(i==3&&j<5?73:0))return 2;
 bank7e_nested(high,79);
 for(i=0;i<4;i++)for(j=0;j<16;j++)if(high[i][j]!=(j<3?79:i==3&&j<5?73:0))return 3;
 for(n=0;n<=16;n++){
  clear_high();if(bank7e_runtime(high,n,83)!=n)return 4;
  for(i=0;i<4;i++)for(j=0;j<16;j++)if(high[i][j]!=(i==1&&j<n?83:0))return 5;
 }
 bank7e_byte(byte_data,1,231);bank7e_wide(wide_data,1,0x76543210L);
 for(i=0;i<2;i++)for(j=0;j<16;j++)if(byte_data[i][j]!=(i==1&&j<3?231:0))return 6;
 for(i=0;i<2;i++)for(j=0;j<4;j++)if(wide_data[i][j]!=(i==1&&j<3?0x76543210L:0))return 7;
 clear_high();far_matrix(high,2,89);
 for(i=0;i<4;i++)for(j=0;j<16;j++)if(high[i][j]!=(i==2&&j<3?89:0))return 8;
 if(far_word_home(&high[2][0],123,7)!=96||mixed_bank(999,11,&high[2][0],0x12340000L)!=0x12340064L)return 9;
 for(i=0;i<3;i++){before=hits;if(named_far_scaled(i)!=(i==0?13:i==1?23:37)||hits!=before+2)return 10;}
 for(n=0;n<2;n++){
  clear_high();switch_loops(high,2,97,n);
  for(i=0;i<4;i++)for(j=0;j<16;j++)if(high[i][j]!=(i==2&&(n?j<3:j>=2&&j<5)?97:0))return 11;
 }
 source_pack.a[1]=101;source_pack.z=0x12345678L;clear_high();
 if(copy_mix(high,1,103)!=204||destination_pack.z!=0x12345678L)return 12;
 for(i=0;i<4;i++)for(j=0;j<16;j++)if(high[i][j]!=(i==1&&j<3?103:0))return 13;
 if(padding[8999]!=0x5a)return 14;
 return 0;
}
