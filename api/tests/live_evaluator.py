"""S17 native CLI success, missing-baseline and deliberately corrupted replay exits."""
import copy
import json
import subprocess
import sys
import yaml
from live_support import ROOT,server

base=ROOT/"docs/evidence/app/sprints"
golden=base/"S17-probe-golden.yaml"
data=yaml.safe_load((ROOT/"eval/golden.yaml").read_text())
subset={"questions":[q for q in data["questions"] if q["id"] in {"q09","q13"}]}
golden.write_text(yaml.safe_dump(subset,sort_keys=False),encoding="utf-8")
baseline=base/"S17-probe-baseline.json"
with server(8002,{},"S17") as url:
    def run(extra,out):
        command=[sys.executable,str(ROOT/"eval/run_eval.py"),"--api",url,"--golden",str(golden),
                 "--baseline",str(baseline),"--out",str(base/out),"--bypass-cache",*extra]
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        (base/(out+".txt")).write_text(result.stdout+result.stderr+f"\nNATIVE_EXIT={result.returncode}",encoding="utf-8")
        return result.returncode
    code=run(["--update-baseline"],"S17-probe-results.json")
    assert code==0,(base/"S17-probe-results.json.txt").read_text()
    scored=json.loads((base/"S17-probe-results.json").read_text())
    replay={row["id"]:copy.deepcopy(row["response"]) for row in scored["rows"]}
    assert replay["q09"]["citations"],replay
    replay["q09"]["citations"][0]["source"]="fabricated-source.pdf"
    bad=base/"S17-degraded-responses.json"
    bad.write_text(json.dumps(replay,indent=2),encoding="utf-8")
    degraded=run(["--responses",str(bad)],"S17-degraded-results.json")
    assert degraded==1
report=dict(passed=True,baseline_scope="Two-question probe only, not shipped baseline",native_exit=code,
            degraded_exit=degraded,score={k:v for k,v in scored.items() if k not in {"rows"}})
(base/"S17-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("S17 PASS: native CLI scoring and real degraded-response runner failure")
