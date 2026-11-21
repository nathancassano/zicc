#include <stdio.h>
#include <stdlib.h>
#include "../src/headers/relax.h"
int main(int argc,char **argv)
{
    FILE *in,*out;long size;char *text;int ok;
    if(argc!=3)return 2;
    in=fopen(argv[1],"rb");if(!in)return 2;
    if(fseek(in,0,SEEK_END)||(size=ftell(in))<0||fseek(in,0,SEEK_SET)){fclose(in);return 2;}
    text=malloc((size_t)size+1);if(!text){fclose(in);return 2;}
    if(fread(text,1,(size_t)size,in)!=(size_t)size){free(text);fclose(in);return 2;}
    text[size]=0;fclose(in);out=fopen(argv[2],"wb");if(!out){free(text);return 2;}
    ok=relax_assembly(out,text,"fixture",1);if(fclose(out))ok=0;free(text);return ok?0:1;
}
