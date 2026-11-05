"""Truthful probe state and process-only liveness."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("failure",["chroma","model","dimension","redis",None])
def test_readiness_dependency_failure_and_recovery(monkeypatch,failure):
    from app.main import app
    from app.services import readiness
    monkeypatch.setenv("RETRIEVER","stub")
    monkeypatch.setenv("LLM_PROVIDER","stub")
    with TestClient(app) as client:
        monkeypatch.setattr(readiness,"check_dependencies",lambda state:{
            name:(failure!=name) for name in ("chroma","model","dimension","redis")})
        result=client.get("/readyz")
        assert result.status_code==(503 if failure else 200)
        if failure:
            assert result.json()["checks"][failure] is False
        assert client.get("/healthz").json()=={"status":"alive"}
        monkeypatch.setattr(readiness,"check_dependencies",lambda state:{"chroma":True,"redis":True})
        assert client.get("/readyz").status_code==200


def test_stub_readiness_is_offline():
    from app.services.readiness import check_dependencies
    assert check_dependencies(SimpleNamespace(settings=SimpleNamespace(retriever="stub")))=={"stub":True}
