"""Compare loops that step through an array at a fixed stride. Compile the assignment functions separately from their callers."""
import os
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'affine-loop-check'
spec=importlib.util.spec_from_file_location('checks',ROOT/'tests/check-strength.py')
checks=importlib.util.module_from_spec(spec);spec.loader.exec_module(checks)
checks.OUT=OUT
support=checks.support
MODES={'off':(False,False),'frame':(True,False),'register':(True,True)}
CASES={
    'paired_words':'''unsigned a[32*8];
void borders(unsigned x,unsigned y,unsigned w,unsigned h){
    for(int i=x+1;i<x+w-1;i++){a[y*32+i]=0x248a;a[(y+h-1)*32+i]=0x248a;}
    for(int i=y+1;i<y+h-1;i++){a[i*32+x]=0x248c;a[i*32+x+w-1]=0x248c;}
}
int main(void){
    borders(3,2,1,1);
    for(unsigned i=0;i<256;i++)if(a[i])return 1;
    borders(3,2,1,5);
    for(unsigned i=0;i<256;i++)if(a[i]!=(i%32==3&&i/32>=3&&i/32<=5?0x248c:0))return 2;
    borders(3,2,7,5);
    for(unsigned i=0;i<256;i++){
        unsigned x=i%32,y=i/32,expected=0;
        if((y==2||y==6)&&x>3&&x<9)expected=0x248a;
        if((x==3||x==9)&&y>2&&y<6)expected=0x248c;
        if(a[i]!=expected)return 3;
    }
    return 0;
}''',
    'multidimensional':(ROOT/'tests/multidimensional_cases.c').read_text(),
    'unsigned_wrap':'''int a[2][5];int main(void){unsigned short j;for(j=65535U;j!=3;j++)a[0][(unsigned short)(j+1)]=j;
if(j!=3||(unsigned short)a[0][0]!=65535U||a[0][1]!=0||a[0][2]!=1||a[0][3]!=2)return 1;return 0;}''',
    'control':'''int a[2][7];
int run(int m[][7],int row,int n){int j;for(j=1;j<n;j+=2){if(j==3)continue;m[row][j]+=j;if(j==5)break;}return j;}
int main(void){if(run(a,1,0)!=1)return 1;if(run(a,1,7)!=5||a[1][1]!=1||a[1][3]!=0||a[1][5]!=5)return 2;return 0;}''',
    'descending':'''int a[2][7];int run(int m[][7],int row){int j;for(j=6;j>=0;j-=2)m[row][j]=j+1;return j;}
int main(void){if(run(a,1)!=-2||a[1][0]!=1||a[1][2]!=3||a[1][4]!=5||a[1][6]!=7||a[0][0])return 1;return 0;}''',
    'affine_index':'''int a[2][7];void run(int m[][7],int row){int j;for(j=0;j<3;j++)m[row][2*j+1]=9;}
int main(void){run(a,1);if(a[1][1]!=9||a[1][3]!=9||a[1][5]!=9||a[1][2]||a[0][1])return 1;return 0;}''',
    'overlap':'''int a[2][7];void run(int m[][7],int row){int j;for(j=1;j<7;j++)m[row][j]=m[row][j-1]+1;}
int main(void){int j;a[1][0]=5;run(a,1);for(j=0;j<7;j++)if(a[1][j]!=j+5||a[0][j])return 1;return 0;}''',
    'widths':'''char a[2][7];long b[2][7];struct S{int x;char y;};struct S c[2][7];
int main(void){int i,j;for(i=0;i<2;i++)for(j=0;j<7;j++){a[i][j]=j;b[i][j]=100000L+j;c[i][j].x=j;c[i][j].y=i;}
for(i=0;i<2;i++)for(j=0;j<7;j++)if(a[i][j]!=j||b[i][j]!=100000L+j||c[i][j].x!=j||c[i][j].y!=i)return 1;return 0;}''',
    'observable_index':'''int a[2][5];int run(int m[][5],int row,int n){int j;for(j=0;j<n;j++)m[row][j]=j;return j+m[row][j-1];}
int main(void){if(run(a,1,5)!=9||a[0][0])return 1;return 0;}''',
    'zero':'''int a[2][5];int run(int m[][5],int n){int row,j;for(j=0;j<n;j++)m[row][j]=3;return j;}
int main(void){return run(a,0);}''',
    'changing_bound':'''int a[2][7];int run(int m[][7],int row,int n){int j;for(j=0;j<n;j++){m[row][j]=j+1;if(j==2)n=3;}return j;}
int main(void){if(run(a,1,7)!=3||a[1][2]!=3||a[1][3])return 1;return 0;}''',
}
FALLBACKS={
    'array_address_comparison':'''int a[2][3];int *identity(int *p){return p;}
int main(void){int local[2][3];a[0][0]=37;local[0][0]=41;
if(identity(a[0])!=a[0]||identity(a[1])!=a[1]||identity(local[0])!=local[0])return 1;
if(identity(a[0])==a[1]||identity(local[0])==local[1])return 2;return 0;}''',

    'call_index':'''int a[2][5];void bump(int *j){++*j;}void run(int m[][5]){int j;for(j=0;j<5;j++){m[1][j]=7;bump(&j);}}
int main(void){run(a);if(a[1][0]!=7||a[1][2]!=7||a[1][4]!=7||a[1][1])return 1;return 0;}''',
    'changing_row':'''int a[2][5];void run(int m[][5]){int row=0,j;for(j=0;j<5;j++){m[row][j]=7;row=1;}}
int main(void){run(a);if(a[0][0]!=7||a[1][1]!=7||a[1][4]!=7||a[0][1])return 1;return 0;}''',
    'changing_base':'''int a[2][5],b[2][5];void run(int m[][5],int n[][5]){int j;for(j=0;j<5;j++){m[1][j]=7;m=n;}}
int main(void){run(a,b);if(a[1][0]!=7||b[1][1]!=7||b[1][4]!=7||a[1][1])return 1;return 0;}''',
    'narrow_index':'''int a[2][256];int main(void){int j;for(j=255;j<258;j++)a[0][(unsigned char)j]=7;
if(a[0][255]!=7||a[0][0]!=7||a[0][1]!=7||a[0][2])return 1;return 0;}''',
    'nonlinear':'''int a[2][5];void run(int m[][5]){int j;for(j=1;j<5;j*=2)m[1][j]=7;}
int main(void){run(a);if(a[1][1]!=7||a[1][2]!=7||a[1][4]!=7||a[1][3])return 1;return 0;}''',
}
KERNELS=(ROOT/'tests/multidimensional_cases.c').read_text().split('void across_row',1)[1].split('int main(void)',1)[0]
KERNELS='void across_row'+KERNELS
DRIVER='''void across_row(int m[][5],int row,int value);void down_column(int m[][5],int col,int value);
void nested_rows(int m[][5],int value);void nested_columns(int m[][5],int value);
int matrix[3][5];int main(void){int i,j,r;
for(r=0;r<3;r++){
 nested_rows(matrix,0);
 across_row(matrix,1,r+3);
 for(i=0;i<3;i++)for(j=0;j<5;j++){if(i==1){if(matrix[i][j]!=r+3)return 1;}else if(matrix[i][j])return 2;}
 down_column(matrix,2,r+7);
 for(i=0;i<3;i++)if(matrix[i][2]!=r+7)return 3;
 nested_rows(matrix,r+11);
 for(i=0;i<3;i++)for(j=0;j<5;j++)if(matrix[i][j]!=r+11)return 4;
 nested_columns(matrix,r+17);
 for(i=0;i<3;i++)for(j=0;j<5;j++)if(matrix[i][j]!=r+17)return 5;
}return 0;}'''

SPELLINGS=r'''
unsigned matrix[3][64], data, count;
volatile unsigned observed_count;
unsigned *after;
unsigned char bytes[262],*bytes_after;
__noinline unsigned preincrement(unsigned r,unsigned n,unsigned v) {
    unsigned j;
    for(j=0;j<n;++j) matrix[r][2*j+1]=v;
    return j;
}
__noinline unsigned assign(unsigned r,unsigned n,unsigned v) {
    unsigned j;
    for(j=0;j<n;j=j+1) matrix[r][2*j+1]=v;
    return j;
}
__noinline unsigned guarded(unsigned r,unsigned n,unsigned v) {
    unsigned j=0;
    if(n) { do { matrix[r][2*j+1]=v; ++j; } while(j<n); }
    return j;
}
__noinline unsigned shifted(unsigned r,unsigned n,unsigned v) {
    unsigned j;
    for(j=0;j<n;++j) matrix[r][(j<<1)+1]=v;
    return j;
}
__noinline unsigned pointer(unsigned r,unsigned n,unsigned v) {
    unsigned j,*p=matrix[r]+1;
    for(j=0;j<n;++j) { *p=v; p+=2; }
    after=p;
    return j;
}
__noinline unsigned byte_fill(unsigned n) {
    unsigned j;
    unsigned char *p=bytes+1;
    for(j=3;j<n;++j) *p++=0xA5;
    bytes_after=p;
    return j;
}
__noinline unsigned bypass(unsigned n) {
    unsigned j=0, trips=0;
    if(n) do { ++trips; if(trips==1) continue; ++j; } while(j<n);
    return trips;
}
__noinline void shift_reverse(void) { do { data>>=1; } while(0!=--count); }
__noinline void shift_tail(void) { do { data>>=1; count--; } while(count!=0); }
__noinline void shift_bypass(void) {
    do { data>>=1; if(data==4) continue; --count; } while(count!=0);
}
__noinline void shift_volatile(void) {
    do { data>>=1; --observed_count; } while(observed_count!=0);
}
int choices[10]={-32768,32767,1,32767,0,-1,-32768,42,42,0};
volatile int volatile_choices[10];
__noinline int select_max(int seed) {
    int i,chosen=-1,best=seed;
    for(i=0;i<10;++i) if(choices[i]>best) { best=choices[i]; chosen=i; }
    return chosen+i*16;
}
__noinline int select_min(int seed) {
    int i,chosen=-1,best=seed;
    for(i=9;i>=0;--i) if(best>choices[i]) { chosen=i; best=choices[i]; }
    return chosen;
}
__noinline int select_volatile(int seed) {
    int i,chosen=-1,best=seed;
    for(i=0;i<10;++i) if(volatile_choices[i]>best) { best=volatile_choices[i]; chosen=i; }
    return chosen;
}
int main(void) {
    unsigned i,j,n;
    for(i=0;i<3;++i) {
        n=i==0?0:i==1?3:24;
        for(j=0;j<64;++j) matrix[1][j]=0;
        if(preincrement(1,n,6)!=n) return 13;
        for(j=0;j<64;++j) if(matrix[1][j]!=((j&1)&&j/2<n?6:0)) return 14;
        if(assign(1,n,7)!=n) return 1;
        for(j=0;j<64;++j) if(matrix[1][j]!=((j&1)&&j/2<n?7:0)) return 2;
        if(guarded(1,n,8)!=n) return 3;
        for(j=0;j<64;++j) if(matrix[1][j]!=((j&1)&&j/2<n?8:0)) return 4;
        if(shifted(1,n,9)!=n) return 5;
        for(j=0;j<64;++j) if(matrix[1][j]!=((j&1)&&j/2<n?9:0)) return 6;
        if(pointer(1,n,10)!=n||after!=matrix[1]+2*n+1) return 7;
        for(j=0;j<64;++j) if(matrix[1][j]!=((j&1)&&j/2<n?10:0)) return 8;
    }
    if(bypass(0)!=0||bypass(3)!=4) return 9;
    if(byte_fill(1)!=3||bytes_after!=bytes+1||bytes[1]) return 15;
    if(byte_fill(263)!=263||bytes_after!=bytes+261||bytes[0]||bytes[261]) return 16;
    for(j=1;j<=260;++j) if(bytes[j]!=0xA5) return 17;
    for(i=1;i<=8;i+=7) {
        data=0xabcd; count=i; shift_reverse();
        if(count||data!=(0xabcdU>>i)) return 10;
        data=0xabcd; count=i; shift_tail();
        if(count||data!=(0xabcdU>>i)) return 11;
    }
    data=8; count=2; shift_bypass();
    if(data!=1||count) return 12;
    data=8; observed_count=2; shift_volatile();
    if(select_max(-32768)!=161||select_max(32767)!=159) return 18;
    if(select_min(32767)!=6||select_min(-32768)!=-1) return 19;
    choices[1]=-1;choices[3]=-1;
    if(select_max(-32768)!=167) return 20;
    volatile_choices[6]=3;volatile_choices[9]=3;
    if(select_volatile(-1)!=6) return 21;
    return data!=2||observed_count!=0;
}
'''


def instrument(stem,cpu_samples=False):
    labels={n.removeprefix('_'):int(a,16) for a,n in re.findall(r'^al (\w+) \.(\S+)$',stem.with_suffix('.labels').read_text(),re.M)}
    names=('across_row','down_column','nested_rows','nested_columns')
    lua='''local active=nil
local returns={}
local samples={across_row={},down_column={},nested_rows={},nested_columns={}}
local writes=0
'''
    for name in names:
        lua+=f'''emu.addMemoryCallback(function()
 assert(active==nil,'nested kernel')
 local s=emu.getState()
 local count=#samples['{name}']
 assert(s['cpu.x']=={labels['matrix']&0xffff},'kernel matrix argument')
 if '{name}'=='across_row' or '{name}'=='down_column' then
  assert(s['cpu.a']==('{name}'=='across_row' and 1 or 2),'row/column argument')
  assert(emu.read16(((s['cpu.sp']+3)&0x1ffff),emu.memType.snesWorkRam,false)==count+('{name}'=='across_row' and 3 or 7),'value argument')
 else
  local expected='{name}'=='nested_columns' and count+17 or (count%2==0 and 0 or (count//2)+11)
  assert(s['cpu.a']==expected,'nested value argument')
 end
 active={{name='{name}',clock=s.masterClock,writes=0}}
 local target=(s['cpu.k']<<16)|((emu.read16(((s['cpu.sp']+1)&0x1ffff),emu.memType.snesWorkRam,false)+1)&0xffff)
 if not returns[target] then
  returns[target]=true
  emu.addMemoryCallback(function()
   if active==nil then return end
   local expected=active.name=='across_row' and 10 or active.name=='down_column' and 6 or 30
   assert(active.writes==expected,'kernel write count '..active.name..' '..active.writes)
   local list=samples[active.name]
   list[#list+1]=emu.getState().masterClock-active.clock
   active=nil
  end,emu.callbackType.exec,target,target)
 end
end,emu.callbackType.exec,{labels[name]},{labels[name]})
'''
    # DBR=$7E: native word stores generate two byte writes to physical WRAM
    address=0x7e0000|(labels['matrix']&0xffff)
    lua+=f'''emu.addMemoryCallback(function() if active~=nil then active.writes=active.writes+1 end end,
emu.callbackType.write,{address},{address+29})
emu.addMemoryCallback(function()
 assert(active==nil,'unfinished kernel')
 local s=emu.getState()
 assert(s['cpu.a']==0 and s['cpu.sp']==0x04ff,'result/stack')
 for name,list in pairs(samples) do
  assert(#list==(name=='nested_rows' and 6 or 3),'kernel calls '..name)
  print('KERNEL '..name..' '..table.concat(list,','))
 end
 print('PASS');emu.stop(0)
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
'''
    if cpu_samples:
        lua=lua.replace('local writes=0\n','local writes=0\nlocal finished=false\nlocal cpu_samples={across_row={},down_column={},nested_rows={},nested_columns={}}\n')
        lua=lua.replace('clock=s.masterClock,writes=0',"clock=s.masterClock,cpu=s['cpu.cycleCount'],writes=0")
        lua=lua.replace('list[#list+1]=emu.getState().masterClock-active.clock',"local state=emu.getState()\n   list[#list+1]=state.masterClock-active.clock\n   local cycles=cpu_samples[active.name]\n   cycles[#cycles+1]=(state['cpu.cycleCount']-active.cpu)&0xffffffff")
        lua=lua.replace(" assert(active==nil,'unfinished kernel')"," if finished then return end;finished=true\n assert(active==nil,'unfinished kernel')")
        lua=lua.replace("  print('KERNEL '..name..' '..table.concat(list,','))","  print('KERNEL '..name..' '..table.concat(list,','))\n  print('CPU_CYCLES '..name..' '..table.concat(cpu_samples[name],','))")
    path=stem.with_name(stem.name+'_kernels.lua');path.write_text(lua)
    runs=[];cpu_runs=[]
    for _ in range(3):
        result=support.run([support.mesen_executable(OUT),'--testRunner','--doNotSaveSettings','--timeout=10',stem.with_suffix('.sfc'),path])
        assert 'PASS' in result.stdout and 'FAIL' not in result.stdout,result.stdout+result.stderr
        runs.append({name:list(map(int,values.split(','))) for name,values in re.findall(r'KERNEL (\w+) ([0-9,]+)',result.stdout)})
        if cpu_samples:
            cpu_runs.append({name:list(map(int,values.split(','))) for name,values in re.findall(r'^CPU_CYCLES (\w+) ([0-9,]+)',result.stdout,re.M)})
    assert runs[0]==runs[1]==runs[2],runs
    if cpu_samples:
        assert cpu_runs[0]==cpu_runs[1]==cpu_runs[2],cpu_runs
        assert all(set(row)==set(names) for row in cpu_runs),cpu_runs
        return runs,cpu_runs
    return runs


def main():
    OUT.mkdir(parents=True,exist_ok=True);report={'cases':{},'kernels':{}}
    for mode,enabled,unroll in [('off',False,False),('rolled',True,False),('unrolled',True,True)]:
        result=checks.build('loop_spellings_'+mode,SPELLINGS,enabled,unroll=unroll)
        assembly=result['assembly']
        for name,marker in {
            'preincrement':'; affine register cursor:',
            'assign':'; affine register cursor:', 'guarded':'; affine register cursor:',
            'shifted':'; affine register cursor:', 'pointer':'; explicit register cursor:',
            'byte_fill':'; explicit register byte fill',
            'shift_reverse':'; register-resident fixed word shift loop',
            'shift_tail':'; register-resident fixed word shift loop',
        }.items():
            body=assembly.split(f'_{name}:\n',1)[1].split(f'__size_{name}',1)[0]
            assert (marker in body)==enabled,(mode,name,body)
            if name=='preincrement':
                lowering='affine register cursor' if enabled else 'generic fallback'
                assert f'; loop lowering: {lowering}\n' in body,(mode,name,body)
            if name in ('preincrement','assign','guarded','shifted'):
                # Match actual consecutive indexed stores. Three trips use
                # only the tail, and 24 execute a group plus a nonzero tail
                groups=re.findall(r'(?:^    sta a:\$[0-9A-F]{4},x\n){2,}',body,re.M)
                if unroll:
                    assert len(groups)==1,(mode,name,body)
                    offsets=[int(x,16) for x in re.findall(r'\$([0-9A-F]{4})',groups[0])]
                    factor=len(offsets)
                    assert 3<factor<24 and 24%factor and offsets==list(range(0,4*factor,4)),(name,offsets)
                    assert '    sta a:$0000,x\n' in body.split(groups[0],1)[1],(mode,name,body)
                else:
                    assert not groups,(mode,name,body)
        for name in ('shift_bypass','shift_volatile'):
            body=assembly.split(f'_{name}:\n',1)[1].split(f'__size_{name}',1)[0]
            assert '; register-resident fixed word shift loop' not in body,(mode,name)
        for name in ('select_max','select_min','select_volatile'):
            body=assembly.split(f'_{name}:\n',1)[1].split(f'__size_{name}',1)[0]
            assert ('; loop lowering:' not in body)==(unroll and name!='select_volatile'),(mode,name,body)
        print('PASS loop spellings '+mode,flush=True)
    for name,source in {**CASES,**FALLBACKS}.items():
        pair={}
        for mode,(enabled,register) in MODES.items():
            result=checks.build(name+'_'+mode,source,enabled,register_loops=register)
            if name=='paired_words':
                for stride in (2,64):
                    marker=f'; paired affine word stores: shared byte stride {stride}'
                    assert (marker in result['assembly'])==(mode=='register'),(mode,stride)
            elif mode=='register':
                if name in FALLBACKS:assert '; affine loop:' not in result['assembly'],name
                else:assert '; affine loop:' in result['assembly'],name
            pair[mode]={k:result[k] for k in ('master_clocks','code_bytes')}
        # The ordinary C reference is independent of either lowering path
        path=OUT/(name+'_host.c');path.write_text(source);host=path.with_suffix('.exe')
        support.run([ROOT/'tools/msvc.cmd','/nologo','/std:c17','/O2','/Fo'+str(path.with_suffix('.obj')),'/Fe'+str(host),path])
        support.run([host]);report['cases'][name]=pair
        print('PASS affine '+name,flush=True)
    kernel_source=OUT/'kernels.c';kernel_source.write_text(KERNELS)
    assembly=[]
    headings = {
        'off': 'Recalculate the address',
        'frame': 'Keep a running address in the stack frame',
        'register': 'Keep a running address in register X',
    }
    for mode,(enabled,register) in MODES.items():
        target=OUT/('kernels_'+mode+'.s');obj=target.with_suffix('.o')
        command=[ROOT/'build/zicc.exe',kernel_source,'-o',target]
        if not enabled:command.append('--no-strength-reduction')
        if not register:command.append('--no-register-loops')
        support.run(command);support.run([support.CC65/'ca65.exe','--cpu','65816','-g','-o',obj,target])
        checks.build('kernels_'+mode,DRIVER,enabled,register_loops=register,extra_objects=[obj],
                     required_imports=re.findall(r'^\.import (\S+)$',target.read_text(),re.M))
        stem=OUT/('kernels_'+mode+('_on' if enabled else '_off'))
        runs=instrument(stem)
        text=target.read_text()
        if mode=='register':assert text.count('; affine register cursor:')==4,text
        report['kernels'][mode]={'samples':runs,'assembly_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                                 'rom_sha256':hashlib.sha256(stem.with_suffix('.sfc').read_bytes()).hexdigest()}
        assembly.append('## '+headings[mode]+'\n\n```asm\n'+text+'\n```\n')
    for name in ('across_row','down_column','nested_rows','nested_columns'):
        baseline=report['kernels']['off']['samples'][0][name]
        optimized=report['kernels']['register']['samples'][0][name]
        assert max(optimized)<min(baseline),(name,baseline,optimized)
        print(name+': '+str(baseline)+' -> '+str(optimized),flush=True)
    report['inputs']={str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path):
                      hashlib.sha256(path.read_bytes()).hexdigest() for path in
                      [ROOT/'build/zicc.exe',*sorted((ROOT/'runtime/integers').glob('*.s')),ROOT/'build/integers.o',ROOT/'build/startup.o',ROOT/'build/nmi.o',kernel_source,
                       OUT/'kernels_off_off.c',ROOT/'tests/multidimensional_cases.c',Path(__file__)]}
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUT/'assembly.md').write_text(
        '# Walking through an array one address at a time\n\n'
        'Each loop visits cells a fixed distance apart. Compare the assembly for three ways to find the next cell.\n\n'
        +'\n'.join(assembly))
    print('PASS affine loops: differential semantics, fallback guards, opaque kernels and repeated execution assertions')


if __name__=='__main__':main()
