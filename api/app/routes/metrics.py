"""Prometheus metrics at /metrics (section 4.8).

Request count and latency are wired up already. Add your own the same way:
retrieval latency, generation latency, cache hits, abstentions, fallbacks, tokens.
"""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from contextvars import ContextVar
from typing import Any

router = APIRouter()

REQUESTS = Counter("rahbar_requests_total", "HTTP requests", ["path", "status"])
LATENCY = Histogram(
    "rahbar_request_seconds",
    "HTTP request latency",
    ["path"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60,90,120),
)
RETRIEVAL=Histogram("rahbar_retrieval_seconds","Retrieval and query embedding time")
GENERATION=Histogram("rahbar_generation_seconds","All bounded generation attempts",buckets=(.1,.5,1,2,5,10,20,30,60,90,120))
CACHE_LOOKUPS=Counter("rahbar_cache_lookups_total","Eligible semantic cache lookups")
CACHE_HITS=Counter("rahbar_cache_hits_total","Safe semantic cache hits")
CACHE_OUTCOMES=Counter("rahbar_cache_outcomes_total","Request cache outcomes",["status"])
ABSTENTIONS=Counter("rahbar_abstentions_total","Ungrounded responses including fallback")
FALLBACKS=Counter("rahbar_fallbacks_total","Generation failures safely declined")
TOKENS=Counter("rahbar_tokens_total","Generation token usage or labeled estimates",["direction","kind"])
QUERY: ContextVar[dict[str,Any]|None]=ContextVar("query_statistics",default=None)


def field(name: str,value: Any) -> None:
    current=QUERY.get()
    if current is not None:
        current[name]=value


def tokens(incoming: int,outgoing: int,kind: str) -> None:
    TOKENS.labels(direction="in",kind=kind).inc(incoming)
    TOKENS.labels(direction="out",kind=kind).inc(outgoing)
    current=QUERY.get()
    if current is not None:
        current["tokens_in"]=current.get("tokens_in",0)+incoming
        current["tokens_out"]=current.get("tokens_out",0)+outgoing
        current["token_kind"]=kind


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
