"""S13 isolated real Redis/Chroma/model cache invalidation experiment."""
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/"api"),str(root/"indexer")]
from app.main import app  # noqa: E402
from pipeline.config import get_settings  # noqa: E402
from pipeline.embed import embed  # noqa: E402
from pipeline.models import Chunk  # noqa: E402
from pipeline.store import store  # noqa: E402

os.environ.update(RETRIEVER="chroma",LLM_PROVIDER="ollama-host",CHROMA_HOST="127.0.0.1",CHROMA_PORT="8001",
    CHROMA_COLLECTION="rahbar_cache_audit",OLLAMA_URL="http://127.0.0.1:11434",REDIS_URL="redis://127.0.0.1:6379/0",
    RELEVANCE_FLOOR="0.3",CACHE_THRESHOLD="0.95")
settings=replace(get_settings(),collection="rahbar_cache_audit")
def publish(day):
    c=Chunk("policy-"+day,f"4.25 The course withdrawal deadline is {day}.","owned-cache-policy.txt","4.25",1,"2026",False)
    store([c],embed([c.text],settings),settings)
publish("Monday")
with TestClient(app) as client:
    def ask(question,sid=None):
        response=client.post("/api/ask",json={"question":question,**({"session_id":sid} if sid else {})})
        assert response.status_code==200,response.text
        return {"cache":response.headers["X-Cache"],"body":response.json()}
    first=ask("What is the course withdrawal deadline?")
    second=ask("When is the course withdrawal deadline?")
    near=ask("Under the August 2023 rules what is the course withdrawal deadline?")
    follow=ask("What is the course withdrawal deadline?",first["body"]["session_id"])
    publish("Tuesday")
    changed=ask("What is the course withdrawal deadline?")
assert first["cache"]=="MISS" and "monday" in first["body"]["answer"].lower(),first
assert second["cache"]=="HIT",second
assert near["cache"]=="MISS" and not near["body"]["answered_from_context"],near
assert follow["cache"]=="BYPASS",follow
assert changed["cache"]=="MISS" and "tuesday" in changed["body"]["answer"].lower(),changed
report=dict(passed=True,scope="Isolated owned policy and actual model/Redis/Chroma; normal index untouched",
            first=first,paraphrase=second,near_miss=near,follow_up=follow,changed_policy=changed)
(root/"docs/evidence/app/sprints/S13-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("S13 PASS: semantic hit, version rejection, follow-up bypass and actual changed-policy invalidation")
