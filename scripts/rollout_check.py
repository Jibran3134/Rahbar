"""Demonstrate visible Ingress deployment changes with endpoint propagation waits."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parents[1] / "docs/evidence/platform/P04"
report = dict(passed=False, commands=[], observations=[],
              initial_attempt="A previous immediate GET raced Ingress endpoint propagation after rollout; "
                              "the new page was subsequently observed. This check waits for actual visibility.")


def save():
    (BASE / "rollout-rollback.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def run(*args):
    command = ["kubectl", "--context", "rahbar", "-n", "rahbar", *args]
    result = subprocess.run(command, capture_output=True, text=True)
    report["commands"].append(dict(command=command, native_exit=result.returncode,
                                   stdout=result.stdout, stderr=result.stderr))
    save()
    assert result.returncode == 0, result.stderr


with httpx.Client(base_url="http://127.0.0.1:18085", headers={"Host": "rahbar.local", "Connection": "close"}, timeout=15) as client:
    def page(new):
        for _ in range(60):
            response = client.get("/")
            visible = "FAST-NUCES policy assistant." in response.text
            report["observations"].append(dict(time=time.time(), status=response.status_code, new=visible))
            save()
            if response.status_code == 200 and visible == new:
                return response.text
            time.sleep(.5)
        raise RuntimeError("Ingress page did not converge to the selected revision")

    run("set", "image", "deployment/ui", "ui=rahbar-ui:platform-p03")
    run("rollout", "status", "deployment/ui", "--timeout=300s")
    before = page(False)
    run("set", "image", "deployment/ui", "ui=rahbar-ui:platform-p04")
    run("rollout", "status", "deployment/ui", "--timeout=300s")
    after = page(True)
    run("rollout", "undo", "deployment/ui")
    run("rollout", "status", "deployment/ui", "--timeout=300s")
    rollback = page(False)
    assert before == rollback and before != after
    run("set", "image", "deployment/ui", "ui=rahbar-ui:platform-p04")
    run("rollout", "status", "deployment/ui", "--timeout=300s")
    assert page(True) == after
    report.update(passed=True, before_hash=hashlib.sha256(before.encode()).hexdigest(),
                  after_hash=hashlib.sha256(after.encode()).hexdigest(),
                  rollback_hash=hashlib.sha256(rollback.encode()).hexdigest(),
                  final_image="rahbar-ui:platform-p04")
    save()
print("PASS: actual visible change, rollback, and final redeploy")
