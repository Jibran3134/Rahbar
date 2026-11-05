"""Bounded probe work; at most one outstanding Chroma task per process."""
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

import httpx

from ..retrieval.index_state import resolve_active

_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix="readiness")
_lock=threading.Lock()
_pending: Future[Any]|None=None
log=logging.getLogger("rahbar.readiness")


def check_dependencies(state: Any) -> dict[str,bool]:
    global _pending
    if state.settings.retriever=="stub":
        return {"stub":True}
    checks={"chroma":False,"model":False,"dimension":False,"redis":False}
    with _lock:
        if _pending is None or _pending.done():
            _pending=_executor.submit(lambda:resolve_active(state.retriever.get_client(),state.settings.collection))
        future=_pending
    try:
        active,_=future.result(timeout=2)
        checks["chroma"]=True
        checks["model"]=active.embed_model==state.settings.embed_model
        if checks["model"]:
            response=httpx.post(state.settings.ollama_url.rstrip("/")+"/api/embed",json={
                "model":state.settings.embed_model,"input":["search_query: readiness"],"truncate":False},timeout=2)
            response.raise_for_status()
            vector=response.json()["embeddings"][0]
            import math
            checks["dimension"]=(len(vector)==active.dimension and bool(vector)
                and all(type(v) in (int,float) and math.isfinite(v) for v in vector) and any(vector))
    except Exception:
        pass
    try:
        checks["redis"]=bool(state.redis.ping())
    except Exception:
        pass
    if not all(checks.values()):
        log.warning("not ready",extra={"checks":checks,"expected_model":state.settings.embed_model})
    return checks
