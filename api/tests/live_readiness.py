"""S14 real dependency stop/restore and configured model conflict."""
import json
import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from fastapi.testclient import TestClient

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"api"))
from app.main import app  # noqa: E402
os.environ.update(RETRIEVER="chroma",LLM_PROVIDER="ollama-host",CHROMA_HOST="127.0.0.1",CHROMA_PORT="8001",
                  OLLAMA_URL="http://127.0.0.1:11434",REDIS_URL="redis://127.0.0.1:6379/0",CHROMA_COLLECTION="rahbar")
with TestClient(app) as client:
    def wait_ready():
        for _ in range(10):
            response=client.get("/readyz")
            if response.status_code==200:
                return response.json()
            time.sleep(.5)
        raise AssertionError(response.text)
    before=wait_ready()
    try:
        subprocess.run(["docker","stop","rahbar-redis-sprints"],check=True,capture_output=True)
        down=client.get("/readyz")
        assert down.status_code==503 and down.json()["checks"]["redis"] is False
        assert client.get("/healthz").status_code==200
    finally:
        subprocess.run(["docker","start","rahbar-redis-sprints"],check=True,capture_output=True)
    restored=wait_ready()
    original=app.state.settings
    app.state.settings=replace(original,embed_model="deliberately-wrong-model")
    mismatch=client.get("/readyz")
    assert mismatch.status_code==503 and mismatch.json()["checks"]["model"] is False
    app.state.settings=original
    recovered=wait_ready()
report=dict(passed=True,before=before,redis_stopped=down.json(),restored=restored,
            mismatch=mismatch.json(),recovered=recovered,healthz_during_outage=200)
(root/"docs/evidence/app/sprints/S14-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("S14 PASS: real outage, liveness, model mismatch and recovery")
