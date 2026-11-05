"""Explicit dependency-free line-coverage audit using Python's standard trace tool."""
import json
import os
import sys
import trace
from pathlib import Path

import pytest

root=Path(__file__).resolve().parents[2]
component=sys.argv[1]
assert component in {"api","indexer"}
target=root/component/("app" if component=="api" else "pipeline")
os.chdir(root/component)
sys.path.insert(0,str(root/component))
tracer=trace.Trace(count=True,trace=False,ignoredirs=[str(Path(sys.prefix)/"Lib"),str(Path(sys.base_prefix)/"Lib")])
code=tracer.runfunc(pytest.main,["-q","-p","no:cacheprovider","--tb=short"])
counts=tracer.results().counts
files=[]
for path in sorted(target.rglob("*.py")):
    executable=set(trace._find_executable_linenos(str(path)))
    covered={line for (name,line),count in counts.items() if Path(name).resolve()==path.resolve() and count}
    files.append(dict(path=str(path.relative_to(root)),executable=len(executable),
                      covered=len(executable&covered),missing=sorted(executable-covered)))
total=sum(f["executable"] for f in files)
hit=sum(f["covered"] for f in files)
report=dict(passed=code==0 and hit/total>=.60,component=component,tool="Python 3.12 stdlib trace",
            executable=total,covered=hit,line_coverage=hit/total,minimum=.60,
            scope="Owned production Python modules only; line coverage, not branch coverage",files=files)
path=root/f"docs/evidence/app/sprints/S21-{component}-coverage.json"
path.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k!="files"},indent=2))
raise SystemExit(0 if report["passed"] else 1)
