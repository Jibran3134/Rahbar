"""Bounded-cardinality metrics and request-correlated safe outcome records."""
import json
import logging

from fastapi.testclient import TestClient


def test_success_abstention_fallback_metrics_and_safe_logs(monkeypatch,caplog):
    from app.main import app
    from app.logjson import JsonFormatter
    from app.providers.llm.base import ProviderError,ProviderFailureKind
    monkeypatch.setenv("RETRIEVER","stub")
    monkeypatch.setenv("LLM_PROVIDER","stub")
    caplog.set_level(logging.INFO)
    with TestClient(app) as client:
        client.post("/api/ask",json={"question":"What is the rule?"},headers={"X-Request-ID":"observe-123"})
        class Bad:
            name="bad"
            def generate(self,*args,**kwargs):
                raise ProviderError(ProviderFailureKind.INVALID_JSON)
        app.state.provider=Bad()
        client.post("/api/ask",json={"question":"What is the rule?"})
        text=client.get("/metrics").text
    for metric in ["rahbar_retrieval_seconds","rahbar_generation_seconds","rahbar_cache_outcomes_total",
                   "rahbar_abstentions_total","rahbar_fallbacks_total","rahbar_tokens_total"]:
        assert metric in text
    assert 'kind="estimated"' in text
    from app.routes import metrics
    for collector in [metrics.CACHE_OUTCOMES,metrics.TOKENS]:
        assert not ({"request_id","session_id","chunk_id"}&set(collector._labelnames))
    # Logger handlers are configured for stdout; inspect the formatter contract directly.
    record=logging.LogRecord("rahbar.query",logging.INFO,"",1,"query outcome",(),None)
    record.cache="BYPASS"
    parsed=json.loads(JsonFormatter().format(record))
    assert parsed["msg"]=="query outcome" and "reasoning" not in parsed


def test_coherent_outcome_includes_evidence_for_bypass_and_hit(monkeypatch):
    from app.main import app
    from app.routes import ask
    from app.schemas import AskResponse
    monkeypatch.setenv("RETRIEVER","stub")
    monkeypatch.setenv("LLM_PROVIDER","stub")
    records=[]
    class Capture(logging.Handler):
        def emit(self,record):
            if record.getMessage()=="query outcome":
                records.append(record)
    with TestClient(app) as client:
        handler=Capture()
        logging.getLogger().addHandler(handler)
        try:
            first=client.post("/api/ask",json={"question":"What is the rule?"}).json()
            app.state.cache=object()
            monkeypatch.setattr(ask,"answer_cached",lambda *a,**k:(AskResponse(**first),"HIT"))
            client.post("/api/ask",json={"question":"What is the rule?"})
        finally:
            logging.getLogger().removeHandler(handler)
    assert len(records)==2
    assert records[-1].cache=="HIT" and records[-1].top_k==5
    assert records[-1].chunk_ids and records[-1].scores
    assert hasattr(records[-1],"abstained")
