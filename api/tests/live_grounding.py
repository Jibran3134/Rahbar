"""Explicit S11 ASGI HTTP with real Chroma/Ollama; malformed reply uses real parser.

The injected transport case is clearly separate from native model observations.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app  # noqa: E402
from app.providers.llm.ollama import OllamaProvider  # noqa: E402


def main():
    previous_floor = json.loads(Path("docs/evidence/app/sprints/S09-live.json").read_text())["provisional_live_floor"]
    # Explicit demo profile: S09's two absent maxima are < .735, while S08's
    # historical withdrawal hit is .766. S19 must calibrate the complete set.
    provisional = .75
    os.environ.update(RETRIEVER="chroma",LLM_PROVIDER="ollama-host",CHROMA_HOST="127.0.0.1",
                      CHROMA_PORT="8001",OLLAMA_URL="http://127.0.0.1:11434",
                      RELEVANCE_FLOOR=str(provisional),LLM_MODEL="llama3.2:3b")
    probes = [
        ("current_withdrawal","Under the current undergraduate rules, what is the course-withdrawal deadline?",
         "makeup",True),
        ("historical_withdrawal","Under the August 2023 undergraduate rules specifically, what was the course-withdrawal deadline?",
         "classes",True),
        ("absent_deadline","What is the hostel-room allotment application deadline for the Peshawar campus?",None,False),
        ("absent_deposit","How much is the refundable hostel-room security deposit at the Chiniot-Faisalabad campus?",None,False)]
    results = []
    with TestClient(app) as client:
        for name,question,term,grounded in probes:
            response = client.post("/api/ask",json={"question":question})
            body = response.json()
            matched = response.status_code == 200 and body.get("answered_from_context") == grounded
            matched = matched and "reasoning" not in body
            if term:
                matched = matched and term in body["answer"].lower() and bool(body["citations"])
            else:
                matched = matched and not body["citations"]
            triples = {(r["source"],r["section"],r["page"]) for r in body.get("retrieved",[])}
            matched = matched and all((c["source"],c["section"],c["page"]) in triples
                                      for c in body.get("citations",[]))
            results.append(dict(probe=name,passed=bool(matched),status=response.status_code,response=body))
        native_provider = app.state.provider
        calls = []
        def malformed(request):
            calls.append(request.url.path)
            return httpx.Response(200,json={"message":{"content":"this is not JSON"}})
        with httpx.Client(transport=httpx.MockTransport(malformed)) as fake_http:
            app.state.provider = OllamaProvider(app.state.settings,client=fake_http)
            response = client.post("/api/ask",json={"question":probes[0][1]})
            body = response.json()
            results.append(dict(probe="injected_malformed_provider_json",status=response.status_code,
                passed=response.status_code == 200 and len(calls) == 2
                       and body["answered_from_context"] is False and body["citations"] == [],
                provider_calls=len(calls),response=body))
        app.state.provider = native_provider
    report = dict(passed=all(r["passed"] for r in results),
                  checked_at_utc=datetime.now(timezone.utc).isoformat(),provisional_floor=provisional,
                  previous_selected_pair_floor=previous_floor,
                  model="llama3.2:3b",scope="Real services through ASGI HTTP; final case is explicit transport injection",
                  probes=results)
    Path("docs/evidence/app/sprints/S11-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    assert report["passed"], "Inspect failed native answer or malformed-output probe"


if __name__ == "__main__":
    main()
