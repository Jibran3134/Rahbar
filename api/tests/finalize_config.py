"""S19 explicit publication and final real/fixture baseline creation after gates."""
import json
import subprocess
import sys
from dataclasses import replace

from live_support import ROOT,server
sys.path[:0]=[str(ROOT/"api"),str(ROOT/"indexer")]
from pipeline.config import get_settings  # noqa: E402
from pipeline.models import Chunk  # noqa: E402
from pipeline.store import store  # noqa: E402

base=ROOT/"docs/evidence/app/sprints"
measure=json.loads((base/"S19-measurements.json").read_text(encoding="utf-8"))
assert measure["passed"]
selected=measure["selected"]
size,overlap=selected["size"],selected["overlap"]
path=ROOT/f"corpus/raw/_s05-chunks/chunks-{size}-{overlap}.jsonl"
chunks=[Chunk(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()]
vectors=json.loads((ROOT/f"corpus/raw/_s19-vectors-{size}.json").read_text(encoding="utf-8"))
settings=replace(get_settings(),chroma_host="127.0.0.1",chroma_port=8001,collection="rahbar",ollama_url="http://127.0.0.1:11434")
store(chunks,vectors,settings)
reports=[]
for kind,golden,baseline,out,overrides in [
    ("real",ROOT/"eval/golden.yaml",ROOT/"eval/baseline.json",ROOT/"eval/results.json",{}),
    ("fixture",ROOT/"eval/fixtures/golden.fixture.yaml",ROOT/"eval/fixtures/baseline.json",ROOT/"eval/fixtures/results.json",
     {"CHROMA_COLLECTION":"rahbar_fixtures","LLM_PROVIDER":"stub","RELEVANCE_FLOOR":"0.65"})]:
    config={"RELEVANCE_FLOOR":str(selected["relevance_floor"]),"CACHE_THRESHOLD":str(selected["cache_threshold"]),**overrides}
    with server(8002,config,"S19-"+kind) as url:
        result=subprocess.run([sys.executable,str(ROOT/"eval/run_eval.py"),"--api",url,"--golden",str(golden),
            "--baseline",str(baseline),"--out",str(out),"--update-baseline","--bypass-cache"],cwd=ROOT,capture_output=True,text=True)
        (base/f"S19-{kind}-eval.txt").write_text(result.stdout+result.stderr+f"\nNATIVE_EXIT={result.returncode}",encoding="utf-8")
        scored=json.loads(out.read_text(encoding="utf-8"))
        reports.append(dict(kind=kind,exit_code=result.returncode,recall5=scored["recall@5"],citations=scored["citation_validity"],
            abstention=scored["abstention_correctness"],expect_failures=[r["id"] for r in scored["rows"] if r["expect_match"] is False]))
report=dict(passed=all(r["exit_code"]==0 for r in reports),selected=selected,reports=reports,
            final_baselines=["eval/baseline.json","eval/fixtures/baseline.json"])
(base/"S19-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
assert report["passed"],"Absolute gates must pass before baseline write"
