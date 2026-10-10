#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys
p=Path(__file__).resolve().parent
required=['run.sh','harness.py','agent_task.md','README.md','adapters/antigravity_adapter.sh','.env.harness.example']
missing=[x for x in required if not (p/x).exists()]
if missing: print('Missing:',missing); sys.exit(1)
r=subprocess.run(['python3',str(p/'harness.py'),'preflight'],cwd=p,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
if r.returncode not in (0,1): print(r.stdout); sys.exit(r.returncode)
print('Bundle sanity checks passed.')
