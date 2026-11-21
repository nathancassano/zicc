"""Time prerequisite builds while retaining the initialized MSVC environment."""
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def main():
    make=os.environ.get('ZICC_MAKE','make')
    begin=time.perf_counter()
    # Make still owns prerequisite dependencies. Its jobserver can be overridden
    # by an explicit caller -j; otherwise leave two threads free (minimum four)
    import re
    flags=os.environ.get('MAKEFLAGS','')
    parallel=[] if re.search(r'(?:^|\s)-?j',flags) else ['-j'+str(max(4,(os.cpu_count() or 1)-2))]
    low_priority=getattr(subprocess,'BELOW_NORMAL_PRIORITY_CLASS',0x00004000)
    result=subprocess.run([make,'--no-print-directory',*parallel,'BINARY64=1','check-prerequisites'],
                          cwd=ROOT,creationflags=low_priority)
    if result.returncode:return result.returncode
    os.environ['ZICC_PREREQUISITE_SECONDS']=str(time.perf_counter()-begin)
    print('Prerequisite builds: '+os.environ['ZICC_PREREQUISITE_SECONDS']+'s',flush=True)
    return subprocess.run([make,'--no-print-directory','check-suites','CHECK_PREREQUISITES_DONE=1'],cwd=ROOT,creationflags=low_priority).returncode

if __name__=='__main__':sys.exit(main())
