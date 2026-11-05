"""Controlled local-cluster experiments; keep real outputs and restore overrides."""
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/evidence/platform/P04"
BASE.mkdir(parents=True, exist_ok=True)
report = {"passed": False, "checks": {}, "commands": []}
if "--resume" in sys.argv:
    report = json.loads((BASE / "acceptance.json").read_text())
K = ["kubectl", "--context", "rahbar", "-n", "rahbar"]


def save():
    (BASE / "acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def run(args, expected=(0,)):
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    report["commands"].append(dict(command=args, exit_code=result.returncode,
                                   stdout=result.stdout, stderr=result.stderr))
    save()
    if result.returncode not in expected:
        raise RuntimeError(f"Native exit {result.returncode}: {args}; {result.stderr}")
    return result.stdout


def kubectl(*args, expected=(0,)):
    return run([*K, *args], expected)


def record(name, data):
    report["checks"][name] = data
    save()
    print(name, "PASS", flush=True)


def pods(name):
    return json.loads(kubectl("get", "pods", "-l", "app.kubernetes.io/name=" + name, "-o", "json"))["items"]


def local_http(pod, path, payload=None):
    if path == "/healthz":
        code = """import httpx,json,time
for attempt in range(30):
    try:
        response=httpx.get('http://127.0.0.1:8000/healthz',timeout=2)
        if response.status_code==200:
            print(json.dumps(dict(status=response.status_code,body=response.json(),cache=None)))
            break
    except httpx.HTTPError:
        pass
    time.sleep(1)
else:
    raise RuntimeError('New pod HTTP startup timed out')
"""
        return json.loads(kubectl("exec", pod, "--", "python", "-c", code))
    code = ("import httpx,json; r=httpx." + ("post" if payload is not None else "get") +
            "('http://127.0.0.1:8000" + path + "',timeout=150" +
            (",json=" + repr(payload) if payload is not None else "") +
            "); print(json.dumps(dict(status=r.status_code,body=r.json(),cache=r.headers.get('X-Cache'))))")
    return json.loads(kubectl("exec", pod, "--", "python", "-c", code))


forward = subprocess.Popen(["kubectl", "--context", "rahbar", "-n", "ingress-nginx", "port-forward",
                            "service/ingress-nginx-controller", "18085:80", "--address", "127.0.0.1"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    with httpx.Client(base_url="http://127.0.0.1:18085", headers={"Host": "rahbar.local"}, timeout=150) as client:
        for _ in range(40):
            try:
                if client.get("/api/info").status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(.5)
        else:
            raise RuntimeError("Ingress did not become reachable")

        def ask(question, **kwargs):
            response = client.post("/api/ask", json={"question": question}, **kwargs)
            response.raise_for_status()
            return dict(response=response.json(), cache=response.headers.get("X-Cache"))

        question = "What is the last date to withdraw from a course under the current academic rules?"
        if "network" not in report["checks"]:
            denied = kubectl("exec", "deployment/ui", "--", "curl", "--connect-timeout", "3", "--max-time", "4",
                              "-fsS", "http://chroma:8000/api/v2/heartbeat", expected=(28,))
            allowed = kubectl("exec", "deployment/api", "--", "python", "-c",
                "import httpx,socket; assert httpx.get('http://chroma:8000/api/v2/heartbeat').status_code==200; socket.create_connection(('redis',6379),3).close(); print('API can reach Chroma and Redis')")
            record("network", dict(ui_to_chroma="curl exit 28: blocked", api_paths=allowed, denied_stdout=denied))
        if "dialog_cache" not in report["checks"]:
            first = ask(question)
            second = ask(question)
            assert second["cache"] == "HIT" and second["response"]["citations"]
            names = [p["metadata"]["name"] for p in pods("api") if not p["metadata"].get("deletionTimestamp")]
            turn = local_http(names[0], "/api/ask", {"question": question})
            follow = local_http(names[1], "/api/ask", {"question": "And under the August 2023 rules?",
                                                      "session_id": turn["body"]["session_id"]})
            assert follow["status"] == 200 and follow["cache"] == "BYPASS"
            assert any(c["source"] == "undergraduate-academic-rules-aug-2023.pdf" for c in follow["body"]["citations"])
            record("dialog_cache", dict(first=first, repeat=second, first_pod=names[0], second_pod=names[1], turn=turn, follow=follow))
        if "api_replacement" not in report["checks"]:
            deleted = pods("api")[0]["metadata"]["name"]
            kubectl("delete", "pod", deleted, "--wait=false")
            samples = [ask("What is the hostel room booking deadline?") for _ in range(8)]
            assert all(not x["response"]["answered_from_context"] for x in samples)
            kubectl("rollout", "status", "deployment/api", "--timeout=300s")
            record("api_replacement", dict(deleted=deleted, successful_ingress_requests=len(samples), endpoints=kubectl("get", "endpoints", "api")))
        if "chroma_persistence" not in report["checks"]:
            before = client.get("/api/info").json()["active"]
            uid = pods("chroma")[0]["metadata"]["uid"]
            kubectl("delete", "pod", "chroma-0", "--wait=true")
            kubectl("rollout", "status", "statefulset/chroma", "--timeout=300s")
            kubectl("rollout", "status", "deployment/api", "--timeout=300s")
            for _ in range(60):
                response = client.get("/api/info")
                if response.status_code == 200:
                    break
                time.sleep(2)
            after = response.json()["active"]
            assert before == after and pods("chroma")[0]["metadata"]["uid"] != uid
            record("chroma_persistence", dict(before=before, after=after, replacement_uid=pods("chroma")[0]["metadata"]["uid"]))
        if "redis_persistence" not in report["checks"]:
            session = report["checks"]["dialog_cache"]["turn"]["body"]["session_id"]
            code = "import redis; r=redis.Redis(host='redis'); print(r.llen('rahbar:session:v1:" + session + "'))"
            count = int(kubectl("exec", "deployment/api", "--", "python", "-c", code))
            assert count > 0
            time.sleep(2)
            deleted = pods("redis")[0]["metadata"]["name"]
            kubectl("delete", "pod", deleted, "--wait=true")
            kubectl("rollout", "status", "deployment/redis", "--timeout=300s")
            after = int(kubectl("exec", "deployment/api", "--", "python", "-c", code))
            assert after == count
            record("redis_persistence", dict(before_turns=count, after_turns=after, deleted=deleted))
        if "model_conflict" not in report["checks"]:
            initial = {p["metadata"]["name"] for p in pods("api")}
            try:
                kubectl("patch", "configmap", "rahbar-config", "--type=merge", "-p", json.dumps({"data": {"EMBED_MODEL": "nomic-embed-text-conflict-demo"}}))
                kubectl("rollout", "restart", "deployment/api")
                candidate = None
                for _ in range(90):
                    candidates = [p for p in pods("api") if p["metadata"]["name"] not in initial and p["status"]["phase"] == "Running"]
                    if candidates:
                        candidate = candidates[0]["metadata"]["name"]
                        break
                    time.sleep(2)
                assert candidate
                live = local_http(candidate, "/healthz")
                ready = local_http(candidate, "/readyz")
                assert live["status"] == 200 and ready["status"] == 503 and not ready["body"]["checks"]["model"]
                conflict = dict(pod=candidate, liveness=live, readiness=ready,
                                pods=kubectl("get", "pods"), logs=kubectl("logs", candidate, "--tail=30"))
            finally:
                kubectl("patch", "configmap", "rahbar-config", "--type=merge", "-p", json.dumps({"data": {"EMBED_MODEL": "nomic-embed-text"}}))
                kubectl("rollout", "restart", "deployment/api")
                kubectl("rollout", "status", "deployment/api", "--timeout=300s")
            record("model_conflict", conflict)
        if "reindex" not in report["checks"]:
            # Populate a known safe entry immediately before the rebuild.
            warm = ask(question)
            hit = ask(question)
            assert hit["cache"] == "HIT"
            before = client.get("/api/info").json()["active"]
            api_uids = sorted(p["metadata"]["uid"] for p in pods("api") if not p["metadata"].get("deletionTimestamp"))
            job = "acceptance-reindex-" + str(int(time.time()))
            kubectl("create", "job", "--from=cronjob/reindex", job)
            availability = []
            for _ in range(180):
                status = json.loads(kubectl("get", "job", job, "-o", "json"))["status"]
                if status.get("succeeded"):
                    break
                if status.get("failed", 0) > 2:
                    raise RuntimeError("Reindex Job failed")
                response = client.get("/api/info")
                availability.append(dict(status=response.status_code, active=response.json().get("active")))
                assert response.status_code == 200
                time.sleep(5)
            else:
                raise RuntimeError("Reindex did not complete within acceptance budget")
            after = client.get("/api/info").json()["active"]
            fresh = ask(question)
            assert before["generation"] != after["generation"] and fresh["cache"] == "MISS"
            assert api_uids == sorted(p["metadata"]["uid"] for p in pods("api") if not p["metadata"].get("deletionTimestamp"))
            record("reindex", dict(job=job, before=before, after=after, warm=warm, hit=hit, fresh=fresh,
                                   availability=availability, api_pods_unchanged=True,
                                   logs=kubectl("logs", "job/" + job, "-c", "indexer")))
        if "real_eval" not in report["checks"]:
            output = run([sys.executable, str(ROOT / "eval/run_eval.py"), "--api", "http://127.0.0.1:18085",
                "--host", "rahbar.local", "--golden", str(ROOT / "eval/golden.yaml"), "--baseline",
                str(ROOT / "eval/baseline.json"), "--out", str(BASE / "real-results.json"), "--bypass-cache"])
            record("real_eval", dict(native_exit=0, output=output))
        report["final_objects"] = kubectl("get", "pods,svc,ingress,pvc,hpa", "-o", "wide")
        report["final_top"] = kubectl("top", "pods")
        report["passed"] = True
        save()
finally:
    forward.terminate()
    forward.wait(timeout=10)
print("P04 core cluster experiments PASS", flush=True)
