"""Explicit owned evidence runner; no hidden test skips or baseline refresh."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sprint = sys.argv[1]
checks = [("api-tests",root/"api",["-m","pytest","-q","-p","no:cacheprovider","--tb=short"]),
          ("api-mypy",root/"api",["-m","mypy","app"]),
          ("ruff",root,["-m","ruff","check","api","indexer","eval","corpus"])]
if "--indexer" in sys.argv:
    checks.extend([( "indexer-tests",root/"indexer",["-m","pytest","-q","-p","no:cacheprovider","--tb=short"]),
                   ("indexer-mypy",root/"indexer",["-m","mypy","pipeline"])])
if "--eval" in sys.argv:
    checks.append(("eval-tests",root,["-m","pytest","eval/tests","-q","-p","no:cacheprovider","--tb=short"]))
results=[]
for name,cwd,args in checks:
    proc=subprocess.run([sys.executable,*args],cwd=cwd,capture_output=True,text=True)
    log=proc.stdout+proc.stderr+f"\nNATIVE_EXIT={proc.returncode}\n"
    (root/f"docs/evidence/app/sprints/{sprint}-{name}.txt").write_text(log,encoding="utf-8")
    results.append(dict(check=name,cwd=str(cwd),command=[sys.executable,*args],exit_code=proc.returncode))
    print(name,proc.returncode,log[-1200:],flush=True)
(root/f"docs/evidence/app/sprints/{sprint}-checks.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
raise SystemExit(1 if any(r["exit_code"] for r in results) else 0)
