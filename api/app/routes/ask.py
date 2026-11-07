"""POST /api/ask. The Ingress sends /api/* here unchanged, so the prefix stays."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from redis.exceptions import RedisError
import logging
import time
from . import metrics

from ..retrieval.index_state import IndexStateError
from ..schemas import AskRequest, AskResponse
from ..services.answer import answer_question
from ..services.cache import answer_cached

router = APIRouter(prefix="/api")


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request, response: Response) -> AskResponse:
    state = request.app.state
    started=time.perf_counter()
    trace={"cache":"BYPASS","fallback":False,"tokens_in":0,"tokens_out":0}
    token=metrics.QUERY.set(trace)
    try:
        turn = state.sessions.prepare(body.question,body.session_id) if state.sessions else None
        question=turn.question if turn else body.question
        bypass=request.headers.get("X-Bypass-Cache","").lower()=="true"
        if state.cache and not bypass:
            result,status=answer_cached(question,state.retriever,state.provider,state.settings,state.cache,
                                        follow_up=bool(turn and turn.follow_up))
        else:
            trace["cache_reason"]="requested_bypass" if bypass else "unavailable"
            result,status=answer_question(question,state.retriever,state.provider,state.settings),"BYPASS"
        response.headers["X-Cache"]=status
        response.headers["X-Cache-Reason"]=str(trace.get("cache_reason","unavailable"))
        trace["cache"]=status
        trace.update(top_k=state.settings.top_k,chunk_ids=[r.chunk_id for r in result.retrieved],
                     scores=[round(r.score,4) for r in result.retrieved],abstained=not result.answered_from_context)
        metrics.CACHE_OUTCOMES.labels(status=status).inc()
        if turn:
            state.sessions.save(turn,result.answer)
            result = result.model_copy(update={"session_id":turn.session_id})
        return result
    except IndexStateError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except (ConnectionError,RedisError):
        raise HTTPException(status_code=503,detail="Session dependency unavailable") from None
    finally:
        logging.getLogger("rahbar.query").info("query outcome",extra={**trace,"ms":round((time.perf_counter()-started)*1000,2)})
        metrics.QUERY.reset(token)
