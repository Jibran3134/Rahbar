"""Sample actual indexer cgroup peak/limit and kubectl top during a live Job."""
import json
import subprocess
import time
from pathlib import Path

base = Path(__file__).resolve().parents[1] / "docs/evidence/platform/P02"
rows = []
command = ["kubectl", "--context", "rahbar", "-n", "rahbar"]
pods = json.loads(subprocess.check_output([*command, "get", "pods", "-l", "job-name=indexer", "-o", "json"]))
pod = pods["items"][0]["metadata"]["name"]
probe = "import json,pathlib; p=pathlib.Path('/sys/fs/cgroup'); print(json.dumps({n:(p/n).read_text().strip() for n in ['memory.current','memory.peak','memory.max']}))"
for _ in range(180):
    status = json.loads(subprocess.check_output([*command, "get", "pod", pod, "-o", "json"]))
    if status["status"]["phase"] in {"Succeeded", "Failed"}:
        break
    result = subprocess.run([*command, "exec", pod, "-c", "indexer", "--", "python", "-c", probe],
                            capture_output=True, text=True)
    top = subprocess.run([*command, "top", "pods"], capture_output=True, text=True)
    rows.append(dict(time_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     memory=json.loads(result.stdout) if result.returncode == 0 else None,
                     probe_exit=result.returncode, top=top.stdout, top_exit=top.returncode))
    (base / "indexer-memory.json").write_text(json.dumps(dict(pod=pod, samples=rows), indent=2), encoding="utf-8")
    time.sleep(5)
print("Captured", len(rows), "live samples")
