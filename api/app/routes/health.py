"""Liveness and readiness (section 4.3). They answer different questions."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from ..services import readiness

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Is the process alive? Must never touch Chroma, Redis or the LLM."""
    return {"status": "alive"}


@router.get("/readyz")
def readyz(request: Request, response: Response) -> dict[str, object]:
    checks=readiness.check_dependencies(request.app.state)
    ready=all(checks.values())
    response.status_code=200 if ready else 503
    return {"status":"ready" if ready else "not_ready","checks":checks}


@router.get("/api/info")
def info(request: Request) -> dict[str,object]:
    from ..retrieval.index_state import resolve_active
    state=request.app.state
    active=(resolve_active(state.retriever.get_client(),state.settings.collection)[0].model_dump()
            if state.settings.retriever=="chroma" else None)
    s=state.settings
    return {"active":active,"embed_model":s.embed_model,"llm_model":s.llm_model,"provider":s.llm_provider,
            "top_k":s.top_k,"temperature":s.temperature,"relevance_floor":s.relevance_floor,
            "cache_threshold":s.cache_threshold,"cache_ttl_seconds":s.cache_ttl_seconds}
