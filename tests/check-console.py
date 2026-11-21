"""Check that scrolling and changed text rows reach the screen on time on both NTSC and PAL systems."""
import os
import importlib.util,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mesen_core import Core,SnesConfig
spec=importlib.util.spec_from_file_location('prompt',ROOT/'tests/check-prompt.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
c=p.support;OUT=Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / 'console-check'
SOURCE=r"""
#include <stdio.h>
#include <time.h>
#define REG(a) (*(const volatile unsigned char * __far)(a))
volatile unsigned delayed,calls;
__interrupt(nmi) void user_vblank(void){
 unsigned line,limit;
 calls++;
 if(delayed){
  limit=(REG(0x213fUL)&16)?300:250;
  if(delayed==2)limit-=24;
  do{(void)REG(0x213fUL);(void)REG(0x2137UL);
     line=REG(0x213dUL);line|=(REG(0x213dUL)&1)<<8;
  }while(line<limit);
 }
}
__noinline void checkpoint(unsigned stage){}
void wait_frames(void){clock_t start=clock();while(clock()-start<2UL){}}
int main(void){unsigned i;
 checkpoint(0);
 printf("A");wait_frames();checkpoint(1);
 fflush(stdout);wait_frames();checkpoint(2);
 printf("\rA");fflush(stdout);checkpoint(3);
 printf("\nB");fflush(stdout);checkpoint(4);
 checkpoint(5);for(i=0;i<60;i++)printf("\nX");checkpoint(6);
 wait_frames();checkpoint(7);
 checkpoint(8);printf("\nC\nD\nE");checkpoint(9);wait_frames();checkpoint(10);
 checkpoint(11);printf("\nL");wait_frames();checkpoint(12);
 wait_frames();checkpoint(13);
 checkpoint(14);for(i=0;i<2100;i++)printf("%c",33+i%94);checkpoint(15);
 wait_frames();checkpoint(16);return 0;
}
"""

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 if len(sys.argv)==1:
  for region in ('ntsc','pal'):
   c.run([sys.executable,Path(__file__),region],timeout=40)
   print('PASS console '+region,flush=True)
  return
 region=sys.argv[1];c.OUT=OUT
 extra=[ROOT/f'build/{n}.o' for n in ('arithmetic','integers','ieee_engine')]
 _,rom,labels=c.compile_case('presentation',SOURCE,console=True,extra_objects=extra)
 texts={0:'',1:'A',2:'A',3:'A\rA',4:'A\rA\nB',5:'A\rA\nB'}
 for stage in (6,7,8):texts[stage]=texts[5]+'\nX'*60
 for stage in (9,10,11):texts[stage]=texts[8]+'\nC\nD\nE'
 for stage in (12,13):texts[stage]=texts[11]+'\nL'
 texts[14]=texts[13]
 for stage in (15,16):texts[stage]=texts[14]+''.join(chr(33+i%94) for i in range(2100))
 model={stage:p.terminal(text) for stage,text in texts.items()}
 table='{'+','.join('['+str(k)+']={map={'+','.join(map(str,v[0]))+'},cursor='+str(v[1])+',origin='+str(v[2]*128)+'}' for k,v in model.items())+'}'
 script=f"""
local phase=-1
local nmis,deferred,done,frames=0,0,false,0
local dmas={{}}
local vaddr=0
local scroll=511
local scroll_low=nil
local scroll2,scroll2_low=511,nil
local latest_start,latest_end=0,0
local scroll_writes=0
local model={table}
local function check(ok,message) if not ok then error(message) end end
local function word(a) return emu.read16(a&0x1ffff,emu.memType.snesWorkRam,false) end
local function put(a,v) emu.write(a&0x1ffff,v,emu.memType.snesWorkRam) end
local function setword(a,v) put(a,v&255);put(a+1,v>>8) end
local function hw(a) return emu.read(a,emu.memType.snesMemory,false) end
local function pending() return word({labels['console_pending']}) end
local function verify(stage,presented)
 local m=model[stage]
 check(word({labels['console_cursor']})==m.cursor,'logical cursor stage '..stage)
 check(word({labels['console_origin']})==m.origin,'ring origin stage '..stage)
 for i=0,4095 do
  check(emu.read(({labels['console_map']}+i)&0x1ffff,emu.memType.snesWorkRam,false)==m.map[i+1],'WRAM stage '..stage..' byte '..i)
  if presented then check(emu.read(0x6000+i,emu.memType.snesVideoRam,false)==m.map[i+1],'VRAM stage '..stage..' byte '..i) end
 end
 if presented then
  check(pending()==0,'pending after presentation')
  check(word({labels['console_display_origin']})==m.origin,'display origin')
  check(scroll==((m.origin//16-1)&511),'PPU scroll '..scroll)
  check(scroll2==scroll,'BG2 scroll differs')
 end
end
emu.addMemoryCallback(function(a,v) vaddr=(vaddr&0xff00)|v end,emu.callbackType.write,0x002116)
emu.addMemoryCallback(function(a,v) vaddr=(vaddr&0xff)|(v<<8) end,emu.callbackType.write,0x002117)
emu.addMemoryCallback(function(a,v)
 if scroll_low==nil then scroll_low=v else scroll=(scroll_low|(v<<8))&511;scroll_low=nil end
 scroll_writes=scroll_writes+1
 if phase>=0 then check((hw(0x4212)&128)~=0,'scroll outside VBlank') end
end,emu.callbackType.write,0x00210e)
emu.addMemoryCallback(function(a,v)
 if scroll2_low==nil then scroll2_low=v else scroll2=(scroll2_low|(v<<8))&511;scroll2_low=nil end
 if phase>=0 then check((hw(0x4212)&128)~=0,'BG2 scroll outside VBlank') end
end,emu.callbackType.write,0x002110)
emu.addMemoryCallback(function()
 nmis=nmis+1
end,emu.callbackType.exec,{labels['interrupt_body_user_vblank']},{labels['interrupt_body_user_vblank']})
emu.addMemoryCallback(function(a,v)
 if phase<0 then return end
 check(v==1,'DMA channel')
 check((hw(0x4212)&128)~=0,'DMA outside VBlank')
 check(word({labels['calls']})==nmis and nmis>0,'DMA before user NMI')
 check(word({labels['console_busy']})==0,'DMA during buffer mutation')
 local source=hw(0x4302)|(hw(0x4303)<<8)
 local size=hw(0x4305)|(hw(0x4306)<<8)
 local offset=source-{labels['console_map']&65535}
 check(offset>=0 and offset%64==0 and size>0 and size%64==0 and offset+size<=4096,'DMA row range')
 check(vaddr==0x3000+offset//2 and hw(0x4304)==0x7f,'DMA mapping')
 dmas[#dmas+1]={{offset,size}}
end,emu.callbackType.write,0x00420b)
emu.addMemoryCallback(function()
 if phase==15 then latest_start=emu.getState()['ppu.scanline'] end
end,emu.callbackType.exec,{labels['console_present_ready']},{labels['console_present_ready']})
emu.addMemoryCallback(function()
 check((hw(0x4212)&128)~=0,'presentation exceeded VBlank')
 if phase==15 then
  local state=emu.getState()
  latest_end=state['ppu.scanline']
 end
end,emu.callbackType.exec,{labels['console_present_done']},{labels['console_present_done']})
emu.addMemoryCallback(function()
 deferred=deferred+1
 check((hw(0x4212)&128)~=0,'late fixture left VBlank before deadline check')
end,emu.callbackType.exec,{labels['console_present_defer']},{labels['console_present_defer']})
emu.addMemoryCallback(function()
 local s=emu.getState();s['cpu.y']=0x5a3c;emu.setState(s)
end,emu.callbackType.exec,{labels['main']},{labels['main']})
emu.addMemoryCallback(function()
 local stage=emu.getState()['cpu.x']
 check(stage==phase+1,'checkpoint order '..stage);phase=stage
 local held=stage==6 or stage==9 or stage==12 or stage==15
 verify(stage,not held)
 if stage<=3 then check(#dmas==(stage==0 and 0 or 2),'clean/repeated output uploaded') end
 if stage==1 then check(dmas[1][1]==0 and dmas[1][2]==64,'one row update') end
 if stage==4 then check(#dmas==4 and dmas[3][1]==64 and dmas[3][2]==64,'second row') end
 if stage==5 or stage==8 then setword({labels['console_busy']},1) end
 if stage==6 then check(#dmas==4 and pending()==1,'busy mutation uploaded');setword({labels['console_busy']},0) end
 if stage==7 then check(#dmas==6 and dmas[5][1]==0 and dmas[5][2]==2048 and dmas[6][1]==2048 and dmas[6][2]==2048,'coalesced full map') end
 if stage==9 then check(#dmas==6,'busy wrap uploaded');setword({labels['console_busy']},0) end
 if stage==10 then
  check(#dmas==10 and dmas[7][1]==0 and dmas[7][2]==64 and dmas[9][1]==1920 and dmas[9][2]==128,'wrapped range did not split into two DMAs')
 end
 if stage==11 then setword({labels['delayed']},1) end
 if stage==12 then
  check(#dmas==10 and pending()==1 and deferred>=2,'late user NMI did not defer presentation')
  check(word({labels['console_display_origin']})==model[11].origin,'scroll advanced without upload')
  setword({labels['delayed']},0)
 end
 if stage==13 then check(#dmas==12 and dmas[11][1]==64 and dmas[11][2]==64,'deferred row not presented') end
 if stage==14 then setword({labels['console_busy']},1) end
 if stage==15 then
  check(#dmas==12 and pending()==1,'full-map fixture escaped busy')
  setword({labels['delayed']},2);setword({labels['console_busy']},0)
 end
 if stage==16 then
  check(#dmas==14 and dmas[13][2]==2048 and dmas[14][2]==2048,'latest full-map DMA')
  check(latest_start>=226 and latest_end>latest_start,'latest-start fixture did not execute '..latest_start..'/'..latest_end)
  setword({labels['delayed']},0)
 end
end,emu.callbackType.exec,{labels['checkpoint']},{labels['checkpoint']})
emu.addMemoryCallback(function()
 local s=emu.getState()
 check(phase==16 and s['cpu.a']==0,'completion')
 check(s['cpu.sp']==0x04ff and s['cpu.y']==0x5a3c and s['cpu.d']==0 and s['cpu.dbr']==0x7e,'ABI')
 done=true
end,emu.callbackType.exec,{labels['main_exit']},{labels['main_exit']})
emu.addEventCallback(function()
 if done then
  frames=frames+1
  if frames==2 then
   verify(16,true)
   check(#dmas==14,'idle DMA')
   emu.log('PASS dmas='..#dmas..' deferred='..deferred..' scroll_writes='..scroll_writes..' latest_start='..latest_start..' latest_end='..latest_end)
   emu.breakExecution()
  end
 end
end,emu.eventType.endFrame)
"""
 home=OUT/region;core=Core(home)
 try:
  config=SnesConfig();config.Region=1 if region=='ntsc' else 2
  config.Port1.Type=1;config.DisableFrameSkipping=True;config.RamPowerOnState=1
  config.GsuClockSpeed=100;config.BsxCustomDate=-1
  for i in range(8):config.ChannelVolumes[i]=100
  core.bind('SetSnesConfig',None,SnesConfig)(config)
  core.load(rom,home/'check.lua',script);core.start();log=core.wait_for('PASS',20)
  (home/'results.json').write_text(json.dumps(dict(region=region,result=log.splitlines()[-1],checkpoints=17),indent=2)+'\n')
 finally:
  core.close_with_log(home/'check.log')

if __name__=='__main__':main()
