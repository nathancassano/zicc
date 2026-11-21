"""Expose existing fixture builders and independent child runs as queued stages.

Setup executes the original build/assertion path, recording self-invoked workers
instead of launching them. Each worker retains the original command, timeout,
home and assertions. Collection requires every report from this setup.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ('time','interrupts','assembly-render','scalar-values','far-loop-interrupts','assembly-match','assembly-rounded','literal-copies','dp-counters','loop-unroll')

def location(name):
    # Read the literal OUT instead of duplicating scripts' directory ownership
    import re
    text=(ROOT/f'tests/check-{name}.py').read_text()
    match=re.search(r"OUT\s*=.*?\.resolve\(\)\s*/\s*'([^']+)'",text)
    return Path(os.environ.get('ZICC_LOGS_DIR', 'logs')).resolve() / match[1]

def fixture_hashes(out):
    return {str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in out.rglob('*') if p.suffix in ('.sfc','.labels','.dll')}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('script',choices=SCRIPTS)
    p.add_argument('--setup',action='store_true');p.add_argument('--list-workers',action='store_true')
    p.add_argument('--collect',action='store_true');p.add_argument('--worker',type=int)
    a=p.parse_args();out=location(a.script);manifest=out/'queue-setup.json'
    os.environ['ZICC_LOGS_DIR'] = str(out.parent)
    if a.list_workers:
        # Counts are derived from the owning script's actual worker loops by setup
        print(json.dumps(json.loads(manifest.read_text())['workers']));return
    script=(ROOT/f'tests/check-{a.script}.py').resolve()
    if a.setup:
        workers=[];original=subprocess.run
        def capture(command,*args,**kwargs):
            command=list(map(str,command))
            if len(command)>1 and Path(command[1]).resolve()==script:
                workers.append(dict(index=len(workers),command=command,
                    timeout=kwargs.get('timeout',30),cwd=str(kwargs.get('cwd',ROOT))))
                return subprocess.CompletedProcess(command,0,'__ZICC_QUEUED_%04d__'%(len(workers)-1),'')
            return original(command,*args,**kwargs)
        subprocess.run=capture;sys.argv=[str(script)]
        try:runpy.run_path(str(script),run_name='__main__')
        finally:subprocess.run=original
        assert workers,'no independent workers recorded'
        template=json.loads((out/'results.json').read_text())
        (out/'results.json').unlink()
        manifest.write_text(json.dumps(dict(run_id=uuid.uuid4().hex,workers=workers,template=template,fixtures=fixture_hashes(out)),indent=2))
        return
    setup=json.loads(manifest.read_text())
    assert fixture_hashes(out)==setup['fixtures'],'fixtures changed after setup'
    if a.worker is not None:
        item=setup['workers'][a.worker];home=out/'queue-workers'/str(a.worker);home.mkdir(parents=True,exist_ok=True)
        result=subprocess.run(item['command'],cwd=item['cwd'],timeout=item['timeout'],capture_output=True,text=True,
                              creationflags=subprocess.CREATE_NO_WINDOW)
        assert result.returncode==0,result.stdout+result.stderr
        (home/'report.json').write_text(json.dumps(dict(run_id=setup['run_id'],worker=item,stdout=result.stdout)))
        if result.stderr:
            print(result.stderr, file=sys.stderr, end='', flush=True)
        print(result.stdout,flush=True);return
    if a.collect:
        reports=[]
        for item in setup['workers']:
            report=json.loads((out/'queue-workers'/str(item['index'])/'report.json').read_text())
            assert report['run_id']==setup['run_id'] and report['worker']==item,'stale/wrong worker report'
            reports.append(report)
        def restore(value):
            if isinstance(value,dict):return {key:restore(v) for key,v in value.items()}
            if isinstance(value,list):return [restore(v) for v in value]
            if isinstance(value,str):
                for index,report in enumerate(reports):value=value.replace('__ZICC_QUEUED_%04d__'%index,report['stdout'])
            return value
        template=restore(setup['template']);template['queue_workers']=reports
        (out/'results.json').write_text(json.dumps(template,indent=2)+'\n')
        print('PASS collected',len(reports),a.script,'workers');return
    p.error('select a stage')

if __name__=='__main__':main()
