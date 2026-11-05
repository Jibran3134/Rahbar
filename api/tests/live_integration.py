"""S18 actual real/fixture corpora and production CLI; no final baseline refresh."""
import json
import subprocess
import sys
from dataclasses import replace

from live_support import ROOT,server

sys.path[:0]=[str(ROOT/"api"),str(ROOT/"indexer")]
from pipeline.config import get_settings  # noqa: E402
from pipeline.run import run_pipeline  # noqa: E402

base=ROOT/"docs/evidence/app/sprints"
settings=replace(get_settings(),chroma_host="127.0.0.1",chroma_port=8001,collection="rahbar_fixtures",
                 corpus_dir=str(ROOT/"eval/fixtures"),ollama_url="http://127.0.0.1:11434")
count=run_pipeline(settings)
reports=[]
previous=json.loads((base/"S18-live.json").read_text()) if "--fixture-only" in sys.argv else None
for kind,golden,overrides in [
    ("real",ROOT/"eval/golden.yaml",{}),
    ("fixture",ROOT/"eval/fixtures/golden.fixture.yaml",{"CHROMA_COLLECTION":"rahbar_fixtures","LLM_PROVIDER":"stub","RELEVANCE_FLOOR":"0.65"})]:
    if kind=="real" and previous:
        reports.extend(r for r in previous["reports"] if r["kind"]=="real")
        continue
    with server(8002,overrides,"S18-"+kind) as url:
        baseline=base/f"S18-{kind}-provisional-baseline.json"
        out=base/f"S18-{kind}-results.json"
        cmd=[sys.executable,str(ROOT/"eval/run_eval.py"),"--api",url,"--golden",str(golden),
             "--baseline",str(baseline),"--out",str(out),"--update-baseline","--bypass-cache"]
        result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
        (base/f"S18-{kind}-eval.txt").write_text(result.stdout+result.stderr+f"\nNATIVE_EXIT={result.returncode}",encoding="utf-8")
        scored=json.loads(out.read_text())
        reports.append(dict(kind=kind,exit_code=result.returncode,recall5=scored["recall@5"],
            citations=scored["citation_validity"],abstention=scored["abstention_correctness"],
            gate_failures=scored["gate_failures"],expect_failures=[r["id"] for r in scored["rows"] if r["expect_match"] is False]))
report=dict(passed=all(r["exit_code"]==0 for r in reports),fixture_chunks=count,reports=reports,
            scope="Local actual services; baselines provisional only; S19 selects shipped configuration")
(base/"S18-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
assert report["passed"],"Inspect native diagnostic results; do not refresh failed baselines"
