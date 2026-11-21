"""Exact branch limits, iterative cascades and target execution checks."""
import os
import importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'relax-check'
spec=importlib.util.spec_from_file_location('strength',Path(__file__).with_name('check-strength.py'));support=importlib.util.module_from_spec(spec);spec.loader.exec_module(support)
run=support.support.run

def fixture(name,body):
 source=OUT/(name+'.input.s');asm=OUT/(name+'.s');obj=OUT/(name+'.o');rom=OUT/(name+'.bin')
 source.write_text('.setcpu "65816"\n.a16\n.i16\n.segment "CODE"\n'+body,encoding='ascii')
 run([OUT/'driver.exe',source,asm]);run([support.support.CC65/'ca65.exe','--cpu','65816','-o',obj,asm])
 run([support.support.CC65/'ld65.exe','-C',OUT/'layout.cfg','-o',rom,obj])
 return rom.read_bytes(),asm.read_text()

def main():
 OUT.mkdir(parents=True, exist_ok=True)
 run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/W4','/WX','/D_CRT_SECURE_NO_WARNINGS','/O2','/Fo'+str(OUT)+'/', '/Fe'+str(OUT/'driver.exe'),ROOT/'tests/relax-driver.c',ROOT/'src/relax.c'])
 (OUT/'layout.cfg').write_text('MEMORY { ROM: start=$808000, size=$8000, type=ro, file=%O; }\nSEGMENTS { CODE: load=ROM, type=ro; }\n',encoding='ascii')
 # The encoded displacements must be exact, not merely accepted by ca65
 data,_=fixture('forward127','bne target\n.res 127,$EA\ntarget:\nrtl\n');assert data[:2]==bytes([0xd0,0x7f])
 data,_=fixture('forward128','bne target\n.res 128,$EA\ntarget:\nrtl\n');assert data[:5]==bytes.fromhex('f0 03 4c 85 80')
 data,_=fixture('backward128','target:\n.res 126,$EA\nbne target\nrtl\n');assert data[126:128]==bytes([0xd0,0x80])
 data,_=fixture('backward129','target:\n.res 127,$EA\nbne target\nrtl\n');assert data[127:132]==bytes.fromhex('f0 03 4c 00 80')
 data,_=fixture('jump127','jmp .loword(target)\n.res 127,$EA\ntarget:\nrtl\n');assert data[:2]==bytes([0x80,0x7f])
 data,_=fixture('jump128','jmp .loword(target)\n.res 128,$EA\ntarget:\nrtl\n');assert data[:3]==bytes.fromhex('4c 83 80')
 # A compiler-owned function can return directly at its internal jump site
 data,_=fixture('function_return','; allocation function 1 begin\njmp .loword(target)\nnop\ntarget:\nrts\n; allocation function 1 end\n')
 assert data==bytes.fromhex('60 ea 60'),data.hex()
 data,_=fixture('cascade','beq target\nbne near\nnop\nnear:\n.res 124,$EA\ntarget:\nrtl\n');assert data[:5]==bytes.fromhex('f0 7f d0 01 ea')
 data,_=fixture('mutual','start:\nbeq target\n.res 124,$EA\nbne start\ntarget:\nrtl\n');assert data[:2]==bytes.fromhex('f0 7e') and data[126:128]==bytes.fromhex('d0 80')
 data,_=fixture('cascade_expansion','start:\nbne target\n.res 124,$EA\nbne start\nnop\nnop\ntarget:\nrtl\n');assert data[:5]==bytes.fromhex('f0 03 4c 88 80') and data[129:134]==bytes.fromhex('f0 03 4c 00 80')
 data,_=fixture('fold','bne :+\njmp .loword(target)\n:\n.res 9,$EA\ntarget:\nrtl\n');assert data[:2]==bytes.fromhex('f0 09')
 data,_=fixture('named_fold','beq skip\ncg_body = *\n; comment\njmp .loword(target)\nskip:\nnop\ntarget:\nrtl\n');assert data==bytes.fromhex('d0 01 ea 6b')
 data,_=fixture('named_entry','bra cg_body\nbeq skip\ncg_body = *\njmp .loword(target)\nskip:\nnop\ntarget:\nrtl\n');assert data[:4]==bytes.fromhex('80 02 f0 02')
 data,_=fixture('named_external','beq skip\ncg_body = *\njmp .loword(target)\nskip:\nnop\nrtl\ntarget = $1234\n');assert data[:5]==bytes.fromhex('f0 03 4c 34 12')
 data,_=fixture('shared_anonymous','beq :+\nbne :+\njmp .loword(target)\n:\nnop\ntarget:\nrtl\n');assert data[:4]==bytes.fromhex('f0 02 f0 01')
 data,_=fixture('self','target:\njmp .loword(target)\n');assert data==bytes.fromhex('80 fe')
 data,_=fixture('fallthrough','jmp .loword(target)\ntarget:\nrtl\n');assert data==bytes([0x6b])
 data,_=fixture('widths','bne target\nsep #$20\n.a8\nlda #$12\nrep #$20\n.a16\nlda #$1234\nldx #$1234\nlda z:$00,x\nlda a:$0000,y\ntarget:\nrtl\n');assert data[:2]==bytes([0xd0,17]),data.hex()
 # Named anonymous references must remain stable when expansions add skip labels
 data,_=fixture('anonymous_distant','beq :+\n.res 128,$EA\n:\nrtl\n');assert data[:5]==bytes.fromhex('d0 03 4c 85 80')
 for op,opcode in [('beq',0xf0),('bne',0xd0),('bcc',0x90),('bcs',0xb0),('bmi',0x30),('bpl',0x10),('bvc',0x50),('bvs',0x70)]:
  data,_=fixture(op+'_near',op+' target\n.res 7,$EA\ntarget:\nrtl\n');assert data[:2]==bytes([opcode,7])
  data,_=fixture(op+'_far',op+' target\n.res 128,$EA\ntarget:\nrtl\n');assert data[:2]==bytes([opcode^0x20,3]) and data[2]==0x4c
 # Actual C execution in both modes, including a deliberately distant branch
 support.OUT=OUT
 sources={
 'small':'int main(void){int i=0,n=0;while(i<10){if(i==3){i++;continue;}if(i==8)break;n+=i;i++;}return n!=25;}',
 # Out-of-line calls keep the target more than 127 bytes from the branch
 'large':'__noinline int tick(int n){return n+1;}int main(void){int i=0,n=0;while(i<3){if(i==1){'+('n=tick(n);'*60)+'}i++;}return n!=60;}',
 'nested':'int calls;int hit(void){calls++;return 1;}int main(void){int n=0;if((n==0||hit())&&(n!=0&&hit()))return 1;if(calls)return 2;do{n++;}while(n<4);return n!=4;}',
 'insertion_sort':(ROOT/'samples/insertion_sort.c').read_text(),
 }
 result={}
 for name,source in sources.items():
  pair={mode:support.build(name+'_'+mode,source,True,indexed_dpage=True,branch_relaxation=mode=='relaxed',debug_symbols=True) for mode in ('long','relaxed')}
  result[name]={mode:dict(master_clocks=x['master_clocks']) for mode,x in pair.items()}
  if name=='large':assert re.search(r'b\w+ :\+\n    jmp',pair['relaxed']['assembly'])
  if name=='insertion_sort':assert pair['relaxed']['code_bytes']<pair['long']['code_bytes']
  if name=='insertion_sort':
   assert set(re.findall(r'^\.import.*$',pair['long']['assembly'],re.M))==set(re.findall(r'^\.import.*$',pair['relaxed']['assembly'],re.M))
   for mode in pair:
    mapping=(OUT/('insertion_sort_'+mode+'_on.map')).read_text()
    assert all(x not in mapping for x in ('arithmetic.o:','ieee_engine.o:','integers.o:'))
  print('PASS '+name+' '+str(result[name]),flush=True)
 (OUT/'results.json').write_text(json.dumps(dict(boundary_fixtures=32,execution=result),indent=2),encoding='utf-8')
 print('PASS: exact signed branch boundaries, multi-pass cascade, fallthroughs, widths, anonymous labels and execution')

if __name__=='__main__':main()
