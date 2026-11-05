"""S15 real query/semantic hit, JSON outcomes and metrics capture."""
import contextlib
import io
import json
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"api"))
from app.main import app  # noqa: E402
from app.config import Settings  # noqa: E402
tag=os.environ.get("EVIDENCE_SPRINT","S15")
os.environ.update(RETRIEVER="chroma",LLM_PROVIDER="ollama-host",CHROMA_HOST="127.0.0.1",CHROMA_PORT="8001",
    CHROMA_COLLECTION="rahbar",OLLAMA_URL="http://127.0.0.1:11434",REDIS_URL="redis://127.0.0.1:6379/0",
    RELEVANCE_FLOOR=str(Settings().relevance_floor),CACHE_THRESHOLD=str(Settings().cache_threshold))
capture=io.StringIO()
with contextlib.redirect_stdout(capture):
    with TestClient(app) as client:
        question={"question":"Under the current undergraduate rules, what is the course-withdrawal deadline?"}
        first=client.post("/api/ask",json=question,headers={"X-Request-ID":"native-observe"})
        second=client.post("/api/ask",json=question)
        refusal=client.post("/api/ask",json={"question":"What is the hostel-room allotment application deadline for the Peshawar campus?"})
        text=client.get("/metrics").text
logs=[json.loads(line) for line in capture.getvalue().splitlines() if line.startswith("{")]
outcomes=[r for r in logs if r.get("msg")=="query outcome"]
assert first.status_code==200 and second.headers["X-Cache"]=="HIT"
assert not refusal.json()["answered_from_context"]
assert len(outcomes)==3 and outcomes[0]["request_id"]=="native-observe"
assert all("reasoning" not in r and "session_id" not in r for r in outcomes)
assert "rahbar_cache_hits_total" in text and "rahbar_tokens_total" in text
base=root/"docs/evidence/app/sprints"
(base/f"{tag}-metrics.prom").write_text(text,encoding="utf-8")
(base/f"{tag}-query-logs.json").write_text(json.dumps(outcomes,indent=2),encoding="utf-8")
(base/f"{tag}-live.json").write_text(json.dumps(dict(passed=True,first=first.headers["X-Cache"],
    second=second.headers["X-Cache"],outcomes=outcomes,metrics_file=f"{tag}-metrics.prom"),indent=2),encoding="utf-8")
print("S15 PASS: real query, safe hit, refusal, correlated JSON outcomes and metrics")
