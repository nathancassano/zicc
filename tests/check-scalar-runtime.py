"""Check scalar arithmetic, recursive calls and decimal parsing."""
import os
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('support',Path(__file__).with_name('check-compiler.py'))
support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'scalar-runtime-check'

def main():
 OUT.mkdir(parents=True, exist_ok=True);support.OUT=OUT
 extra=[ROOT/('build/'+n+'.o') for n in ['arithmetic','integers','ieee_engine','tables','io','decimal']]
 sources=[
 ('recursive','int fact(int n){if(n<2)return 1;return n*fact(n-1);}int main(void){return fact(6);}',720),
 ('loops','int main(void){int i=0,n=0;for(i=0;i<10;i++){if(i==3)continue;if(i==8)break;n+=i;}do{n--;}while(n>20);return n;}',20),
 ('longmath','int main(void){unsigned long a=0xfedcba98UL,b=0x1234UL;if(a/b!=0xe0042UL)return 1;if(a%b!=0x930UL)return 2;if((a>>17)!=0x7f6eUL)return 3;return 0;}',0),
 ('signedmath','int main(void){long a=-1234567L,b=97;if(a/b!=-12727L)return 1;if(a%b!=-48L)return 2;if((a>>4)!=-77161L)return 3;return 0;}',0),
 ('floatmath','int main(void){float a=12.0,b=3.0;if((a+b)*4.0/2.0!=30.0)return 1;if(a-b!=9.0)return 2;if(-a>=b)return 3;return 0;}',0),
 ('decimal','#include <stdlib.h>\nint main(void){char * __far p;float x;x=strtod("12.",&p);if(x!=12.0||*p)return 1;x=strtod("0.125x",&p);if(x!=0.125||*p!=120)return 2;x=strtod("0x1.8p2",&p);if(x!=6.0||*p)return 3;x=strtod("16777216",&p);if(x!=16777216.0)return 4;x=strtod("nan",0);if(x==x)return 5;if(-0.0)return 6;return 0;}',0),
 ('pointer','int main(void){char a[4];char *p=a;a[0]=65;a[1]=66;*p++=67;if(a[1]!=66)return 1;return a[0]+*p;}',133),
 ]
 report={}
 for name,source,expected in sources:
  _,rom,labels=support.compile_case(name,source,extra_objects=extra)
  report[name]=support.emulate(rom,labels,expected)

 (OUT/'results.json').write_text(json.dumps(report,indent=2))
 print('PASS: recursion, loops, scalar arithmetic, byte stores, and decimal parsing')

if __name__=='__main__':main()
