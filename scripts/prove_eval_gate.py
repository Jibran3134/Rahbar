"""Show actual live fixture-regression failure and restored success; no PR is fabricated."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/evidence/platform/P04"
K = ["kubectl", "--kubeconfig", str(ROOT / ".venv/e2e/kubeconfig"), "--context", "kind-rahbar-ci", "-n", "rahbar"]
steps = []


def run(command, expected=0):
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    steps.append(dict(command=command, native_exit=result.returncode, stdout=result.stdout, stderr=result.stderr))
    (BASE / "live-eval-gate.json").write_text(json.dumps(dict(passed=False, steps=steps), indent=2), encoding="utf-8")
    assert result.returncode == expected, result.stdout + result.stderr


baseline = ROOT / "eval/fixtures/baseline.json"
before = hashlib.sha256(baseline.read_bytes()).hexdigest()
try:
    run([*K, "patch", "configmap", "rahbar-config", "--type=merge", "-p", json.dumps({"data": {"RELEVANCE_FLOOR": "0.99"}})])
    run([*K, "rollout", "restart", "deployment/api"])
    run([*K, "rollout", "status", "deployment/api", "--timeout=300s"])
    args = [sys.executable, str(ROOT / "eval/run_eval.py"), "--api", "http://127.0.0.1:18080", "--host", "rahbar.local",
            "--golden", str(ROOT / "eval/fixtures/golden.fixture.yaml"), "--baseline", str(baseline), "--bypass-cache"]
    run([*args, "--out", str(BASE / "fixture-regression-results.json")], expected=1)
finally:
    run([*K, "patch", "configmap", "rahbar-config", "--type=merge", "-p", json.dumps({"data": {"RELEVANCE_FLOOR": "0.65"}})])
    run([*K, "rollout", "restart", "deployment/api"])
    run([*K, "rollout", "status", "deployment/api", "--timeout=300s"])
run([*args, "--out", str(BASE / "fixture-restored-results.json")])
assert hashlib.sha256(baseline.read_bytes()).hexdigest() == before
(BASE / "live-eval-gate.json").write_text(json.dumps(dict(passed=True, baseline_unchanged=before,
    red_exit=1, restored_exit=0, remote_pr="Not created; account-level blocked merge evidence remains pending", steps=steps), indent=2), encoding="utf-8")
print("PASS: live fixture regression rejected, corrected configuration passes; baseline unchanged")
