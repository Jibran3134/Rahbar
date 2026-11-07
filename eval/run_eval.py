#!/usr/bin/env python3
"""Score a running RAHBAR against a golden set, and gate CI on the result (section 5).

    python eval/run_eval.py --api http://<ingress>                 # your corpus
    python eval/run_eval.py --api ... --golden eval/fixtures/golden.fixture.yaml
    python eval/run_eval.py --api ... --update-baseline            # after a deliberate improvement

Exit code 0 when every gate passes, 1 when any fails. CI relies on that exit code.

Unique recall, citation integrity and required abstentions gate explicit baselines.
Missing/undefined metrics and cross-dataset baselines fail closed.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import math
import sys
import time
from pathlib import Path

import httpx
import yaml

HERE = Path(__file__).resolve().parent

# The gate from section 5.4. Change these only with a reason written in docs/PIPELINE.md.
MAX_RECALL5_DROP = 0.05        # recall@5 may fall at most 5 points below the baseline
MIN_CITATION_VALIDITY = 0.95   # at least 95% of citations must match retrieved passages
REQUIRED_ABSTENTION = 1.0      # every must-abstain question must be declined


def load_golden(path: Path) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = data.get("questions") or []
    if not questions:
        sys.exit(f"no questions in {path}")
    if (any(not isinstance(q,dict) or not isinstance(q.get("question"),str) or not q.get("id") for q in questions)
            or len({q["id"] for q in questions})!=len(questions)):
        sys.exit("golden requires unique IDs and text questions")
    return questions


def ask(client: httpx.Client, api: str, question: str) -> dict:
    """POST one question and return the AskResponse as a dict (see api/app/schemas.py)."""
    response = client.post(f"{api.rstrip('/')}/api/ask", json={"question": question})
    response.raise_for_status()
    return response.json()


def recall_at_k(relevant: list[dict], retrieved: list[dict], k: int) -> float | None:
    """Fraction of the relevant (source, section) pairs found in the top k retrieved.
    Return None when the question has no relevant passages (must-abstain questions)."""
    wanted={(str(p["source"]),str(p["section"])) for p in relevant}
    found={(str(p["source"]),str(p["section"])) for p in retrieved[:k]}
    return len(wanted&found)/len(wanted) if wanted else None


def citation_validity(response: dict) -> float | None:
    """Fraction of the response's citations that match a passage in response['retrieved'].
    Return None when there are no citations."""
    citations={(c["source"],str(c["section"]),c.get("page")) for c in response.get("citations",[])}
    retrieved={(c["source"],str(c["section"]),c.get("page")) for c in response.get("retrieved",[])}
    if not citations:
        return 0.0 if response.get("answered_from_context") is True else None
    return len(citations&retrieved)/len(citations)


def summarise(rows: list[dict]) -> dict:
    """Overall recall@3, recall@5, citation validity and abstention correctness, plus
    recall@5 broken down by question type. This dict becomes results.json."""
    def mean(values):
        values=[v for v in values if v is not None]
        return sum(values)/len(values) if values else None
    diagnostics=[]
    for row in rows:
        response=row.get("response",{})
        diagnostic={**row,"recall@3":recall_at_k(row.get("relevant",[]),response.get("retrieved",[]),3),
                    "recall@5":recall_at_k(row.get("relevant",[]),response.get("retrieved",[]),5),
                    "citation_validity":citation_validity(response)}
        diagnostic["abstention_correct"]=(response.get("answered_from_context") is False
            and not response.get("citations") and response.get("confidence")=="low") if row.get("must_abstain") else None
        expect=row.get("expect")
        diagnostic["expect_match"]=expect.lower() in " ".join(response.get("answer","").lower().split()) if expect else None
        diagnostics.append(diagnostic)
    by_type={kind:{"recall@5":mean([r["recall@5"] for r in diagnostics if r.get("type")==kind]),
                  "questions":sum(r.get("type")==kind for r in diagnostics)} for kind in sorted({r.get("type","ordinary") for r in rows})}
    return {"recall@3":mean([r["recall@3"] for r in diagnostics]),
            "recall@5":mean([r["recall@5"] for r in diagnostics]),
            "citation_validity":mean([r["citation_validity"] for r in diagnostics]),
            "abstention_correctness":mean([r["abstention_correct"] for r in diagnostics]),
            "by_type":by_type,"questions":len(rows),"rows":diagnostics,
            "execution_errors":sum(bool(r.get("error")) for r in rows),
            "denominators":{"recall":sum(r["recall@5"] is not None for r in diagnostics),
                            "citation_questions":sum(r["citation_validity"] is not None for r in diagnostics),
                            "must_abstain":sum(r["abstention_correct"] is not None for r in diagnostics)}}


def gate(results: dict, baseline: dict | None) -> list[str]:
    """Return one message per failed gate (section 5.4); an empty list means pass."""
    failures=[]
    def valid(value):
        return type(value) in (int,float) and math.isfinite(value) and 0<=value<=1
    for key in ("recall@5","citation_validity","abstention_correctness"):
        if not valid(results.get(key)):
            failures.append("Undefined/nonfinite/out-of-range "+key)
    if results.get("execution_errors",0):
        failures.append("API execution errors")
    if baseline is None:
        failures.append("Missing baseline; bootstrap requires explicit --update-baseline")
    elif not results.get("dataset_id") or results.get("dataset_id")!=baseline.get("dataset_id"):
        failures.append("Wrong/missing baseline dataset identity")
    elif not valid(baseline.get("recall@5")):
        failures.append("Invalid baseline recall@5")
    elif valid(results.get("recall@5")) and baseline["recall@5"]-results["recall@5"]>MAX_RECALL5_DROP+1e-12:
        failures.append("recall@5 regression exceeds 0.05")
    if valid(results.get("citation_validity")) and results["citation_validity"]<MIN_CITATION_VALIDITY:
        failures.append("citation validity below 0.95")
    if valid(results.get("abstention_correctness")) and results["abstention_correctness"]<REQUIRED_ABSTENTION:
        failures.append("A required abstention failed")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAHBAR against a golden set.")
    parser.add_argument("--api", required=True, help="base URL, e.g. http://192.168.49.2")
    parser.add_argument("--host", help="Host header, when your Ingress rule names a host")
    parser.add_argument("--golden", type=Path, default=HERE / "golden.yaml")
    parser.add_argument("--baseline", type=Path, default=HERE / "baseline.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    parser.add_argument("--update-baseline", action="store_true",
                        help="write these results as the new baseline")
    parser.add_argument("--bypass-cache",action="store_true",help="explicitly bypass query cache for experiments")
    parser.add_argument("--responses",type=Path,help="explicit diagnostic replay mapping IDs to responses")
    args = parser.parse_args()

    questions = load_golden(args.golden)
    replay=json.loads(args.responses.read_text()) if args.responses else None
    rows = []
    headers = {"Host": args.host} if args.host else {}
    if args.bypass_cache:
        headers["X-Bypass-Cache"]="true"
    with httpx.Client(timeout=480.0, headers=headers) as client:
        try:
            info=client.get(args.api.rstrip("/")+"/api/info").json()
        except Exception:
            info={"unavailable":True}
        for q in questions:
            started = time.perf_counter()
            try:
                response = replay[q["id"]] if replay is not None else ask(client, args.api, q["question"])
                error=None
            except Exception as exc:
                response={}
                error=type(exc).__name__
            rows.append({
                "id": q["id"], "type": q.get("type", "ordinary"),
                "must_abstain": bool(q.get("must_abstain", False)),
                "relevant": q.get("relevant") or [],
                "expect": q.get("expect"),
                "response": response,
                "error":error,
                "seconds": round(time.perf_counter() - started, 2),
            })
            print(f"  {q['id']:<5} {rows[-1]['seconds']:>6.2f}s  {q['question'][:60]}")

    try:
        results = summarise(rows)
        results["dataset_id"]=hashlib.sha256(args.golden.read_text(encoding="utf-8-sig").encode()).hexdigest()
        results["configuration"]=info
        import subprocess
        revision=subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
        source_digest=hashlib.sha256()
        for folder in (HERE.parent/"api/app",HERE.parent/"indexer/pipeline"):
            for path in sorted(folder.rglob("*.py")):
                source_digest.update(str(path.relative_to(HERE.parent)).replace("\\","/").encode())
                source_digest.update(path.read_text(encoding="utf-8-sig").encode())
        results["source_revision"]={"git":revision,"application_digest":source_digest.hexdigest()}
        try:
            baseline = json.loads(args.baseline.read_text()) if args.baseline.exists() else None
        except (ValueError,OSError):
            baseline={"invalid":True}
        failures = gate(results, results if args.update_baseline and baseline is None else baseline)
        if info.get("unavailable") or "active" not in info:
            failures.append("Missing runtime configuration/index identity")
    except NotImplementedError as exc:
        print(f"\nnot implemented yet: {exc}")
        return 2

    results["golden"] = str(args.golden)
    results["questions"] = len(rows)
    results["gate_failures"]=failures
    args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nresults written to {args.out}")
    if args.update_baseline and not failures:
        args.baseline.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"baseline updated: {args.baseline}")

    if failures:
        print("\nGATE FAILED")
        for message in failures:
            print(f"  - {message}")
        return 1
    print("\ngate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
