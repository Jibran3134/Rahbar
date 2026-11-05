"""Explicit S12: two separate ASGI API processes share real Redis history."""
import json
import os
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/"api"))

if len(sys.argv)>1:
    from fastapi.testclient import TestClient
    from app.main import app
    body={"question":sys.argv[1]}
    if len(sys.argv)>2:
        body["session_id"]=sys.argv[2]
    with TestClient(app) as client:
        response=client.post("/api/ask",json=body)
        assert response.status_code==200,response.text
        print("S12_RESPONSE="+json.dumps(response.json()))
else:
    env={**os.environ,"RETRIEVER":"chroma","LLM_PROVIDER":"stub","CHROMA_HOST":"127.0.0.1",
         "CHROMA_PORT":"8001","OLLAMA_URL":"http://127.0.0.1:11434","REDIS_URL":"redis://127.0.0.1:6379/0"}
    def child(question,sid=None):
        result=subprocess.run([sys.executable,__file__,question,*([sid] if sid else [])],
                              env=env,capture_output=True,text=True,check=True)
        return json.loads(next(line.removeprefix("S12_RESPONSE=") for line in result.stdout.splitlines()
                               if line.startswith("S12_RESPONSE=")))
    first=child("Under the current rules, what is the course withdrawal deadline?")
    second=child("And under the August 2023 rules?",first["session_id"])
    assert first["session_id"]==second["session_id"] and "classes" in second["answer"].lower(),second
    report={"passed":True,"processes":2,"first":first,"follow_up":second,
            "scope":"Real Redis, Chroma and query embeddings; evidence-based stub generation"}
    (root/"docs/evidence/app/sprints/S12-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("S12 PASS: two processes continue a session and retrieve historical deadline")
