"""Compare adapted binary32 decimal conversion with the MSVC C runtime."""
import os
import ctypes as C,json,random,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'decimal-check'

def main():
 OUT.mkdir(parents=True, exist_ok=True)
 values=re.findall(r'\$([0-9a-fA-F]+)',(ROOT/'runtime/ieee32/tables.s').read_text())
 source=OUT/'host.c'
 source.write_text('#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n#include "' + (ROOT / 'runtime/ieee32/decimal.c').as_posix() + '"\nconst U32 decade_floor[88]={'+','.join('0x'+x+'UL' for x in values)+'};\n__declspec(dllexport) U32 parse(const char *s){return __ieee_parse(s,0);}\n__declspec(dllexport) char *format(U32 x){return dec_format(x);}\n__declspec(dllexport) U32 reference(const char *s){float f=strtof(s,0);U32 u;memcpy(&u,&f,4);return u;}\n__declspec(dllexport) char *ref_format(U32 x){static char text[48];float f;memcpy(&f,&x,4);sprintf(text,"%.6g",f);return text;}\n')
 command=[str(ROOT/'tools/msvc.cmd'),'/nologo','/std:c17','/O2','/LD','/Fe'+str(OUT/'host.dll'),'/Fo'+str(OUT/'host.obj'),str(source)]
 p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
 assert p.returncode==0,p.stdout+p.stderr
 m=C.CDLL(str(OUT/'host.dll'))
 for name in ['parse','reference']:
  f=getattr(m,name);f.argtypes=[C.c_char_p];f.restype=C.c_uint32
 for name in ['format','ref_format']:
  f=getattr(m,name);f.argtypes=[C.c_uint32];f.restype=C.c_char_p
 rng=random.Random(65816);count=0
 for u in [0,0x80000000,1,0x7fffff,0x800000,0x7f7fffff,0x3f800000,0x4b800000]+[rng.getrandbits(32) for _ in range(2000)]:
  if (u&0x7f800000)==0x7f800000:continue
  a=m.format(u);b=m.ref_format(u);assert a==b,(hex(u),a,b)
  assert m.parse(a)==m.reference(a),(a,hex(m.parse(a)),hex(m.reference(a)))
  count+=1
 fixtures=['12','3','4','2','16777216','16777215','99999999','-0','12.','0.125','1e-40','1.17549435e-38','3.4028235e38','0x1.8p2']
 for text in fixtures:
  s=text.encode();assert m.parse(s)==m.reference(s),text
 (OUT/'results.json').write_text(json.dumps(dict(random_seed=65816,format_parse_pairs=count,fixtures=fixtures),indent=2))
 print(f'PASS: {count} MSVC binary32 format/parse pairs and {len(fixtures)} boundary fixtures')

if __name__=='__main__':main()
