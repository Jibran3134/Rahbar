"""Explicit native fresh-checkout checks; release acceptance remains a separate gate."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKOUT = Path(sys.argv[1]).resolve()
BASE = ROOT / "docs/evidence/app/sprints"
assert CHECKOUT.is_relative_to(ROOT / ".venv")
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=CHECKOUT, text=True).strip()
resume = "--resume" in sys.argv
if resume:
    assert not subprocess.check_output(
        ["git", "diff", "--name-only", "--", "api/app", "indexer/pipeline", "eval", "corpus"],
        cwd=CHECKOUT, text=True)
else:
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=CHECKOUT, text=True)
sys.path.insert(0, str(CHECKOUT / "api/tests"))
from live_support import server  # noqa: E402


def digest() -> str:
    result = hashlib.sha256()
    for folder in ["api/app", "indexer/pipeline", "eval"]:
        for path in sorted((CHECKOUT / folder).rglob("*")):
            if path.suffix not in {".py", ".yaml", ".md", ".json"} or "__pycache__" in path.parts:
                continue
            result.update(path.relative_to(CHECKOUT).as_posix().encode())
            result.update(path.read_text(encoding="utf-8-sig").encode())
    for name in ["corpus/sources.yaml", "corpus/MANIFEST.md"]:
        result.update((CHECKOUT / name).read_text(encoding="utf-8-sig").encode())
    return result.hexdigest()


steps = json.loads((BASE / "S22-local-steps.json").read_text()) if resume else []
if resume:
    shutil.copyfile(BASE / "S22-local-steps.json", BASE / "S22-initial-local-steps.json")
    shutil.copyfile(BASE / "S22-fresh-fixture-index.txt", BASE / "S22-fixture-path-red.txt")
    steps = [step for step in steps if step["exit_code"] == 0]


def run(name: str, args: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    if any(step["name"] == name and step["exit_code"] == 0 for step in steps):
        print(name, "already passed; retained", flush=True)
        return
    command = [sys.executable, *args]
    process = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)
    (BASE / f"S22-{name}.txt").write_text(
        process.stdout + process.stderr + f"\nNATIVE_EXIT={process.returncode}\n", encoding="utf-8")
    steps.append(dict(name=name, command=command, cwd=str(cwd), exit_code=process.returncode))
    print(name, process.returncode, flush=True)
    (BASE / "S22-local-steps.json").write_text(json.dumps(steps, indent=2), encoding="utf-8")
    if process.returncode:
        raise RuntimeError(f"{name} failed; inspect its captured transcript")


before = digest()
run("fresh-checks", [str(CHECKOUT / "api/tests/sprint_checks.py"), "S22", "--eval", "--indexer"], CHECKOUT)
fresh_base = CHECKOUT / "docs/evidence/app/sprints"
for path in fresh_base.glob("S22-*"):
    shutil.copyfile(path, BASE / path.name)
for component in ["api", "indexer"]:
    run(f"fresh-{component}-coverage", [str(CHECKOUT / "api/tests/coverage_audit.py"), component], CHECKOUT)
    shutil.copyfile(fresh_base / f"S21-{component}-coverage.json", BASE / f"S22-{component}-coverage.json")

fixture_collection = "rahbar_s22_fixtures_" + revision[:8]
fixture_env = {**os.environ, "CORPUS_DIR": str(CHECKOUT / "eval/fixtures"),
               "CHROMA_HOST": "127.0.0.1", "CHROMA_PORT": "8001",
               "CHROMA_COLLECTION": fixture_collection, "OLLAMA_URL": "http://127.0.0.1:11434"}
run("fresh-fixture-index", ["-m", "pipeline.run"], CHECKOUT / "indexer", fixture_env)
reports = []
for kind, golden, baseline, overrides in [
    ("fixture", "eval/fixtures/golden.fixture.yaml", "eval/fixtures/baseline.json",
     {"CHROMA_COLLECTION": fixture_collection, "LLM_PROVIDER": "stub", "RELEVANCE_FLOOR": "0.65"}),
    ("real", "eval/golden.yaml", "eval/baseline.json", {"RELEVANCE_FLOOR": "0.74"}),
]:
    out = BASE / f"S22-{kind}-results.json"
    with server(8002, {"CACHE_THRESHOLD": "0.95", **overrides}, "S22-" + kind) as url:
        run("fresh-" + kind + "-eval", [str(CHECKOUT / "eval/run_eval.py"), "--api", url,
            "--golden", str(CHECKOUT / golden), "--baseline", str(CHECKOUT / baseline),
            "--out", str(out), "--bypass-cache"], CHECKOUT)
    shutil.copyfile(fresh_base / f"S22-{kind}-server.txt", BASE / f"S22-{kind}-server.txt")
    scored = json.loads(out.read_text(encoding="utf-8"))
    reports.append(dict(kind=kind, recall5=scored["recall@5"], citations=scored["citation_validity"],
                        abstention=scored["abstention_correctness"],
                        expect_misses=[r["id"] for r in scored["rows"] if r["expect_match"] is False]))

after = digest()
assert before == after, "Acceptance must not change production sources, frozen truth or baselines"
report = dict(local_checks_passed=True, release_status="BLOCKED", tested_commit=revision,
              checkout=str(CHECKOUT), source_digest_before=before, source_digest_after=after,
              reports=reports, steps=steps,
              environment="Fresh source checkout; reused installed Python/dependencies and native services. "
                          "Fixture index freshly built; real index was previously provisioned. "
                          "No new isolated machine or Kubernetes release is claimed.",
              blockers="Platform Dockerfiles/manifests/workflows/final assembly and protected CD evidence absent; "
                       "Jibran confirmed these will be developed separately.")
(BASE / "S22-local-acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2), flush=True)
