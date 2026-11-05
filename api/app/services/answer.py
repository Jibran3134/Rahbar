"""Retrieve, gate evidence, verify bounded generation and expose public fields.

Shared sessions and semantic cache remain S12/S13 work.
"""

from __future__ import annotations

import logging
import time

from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..retrieval.base import Retriever
from ..schemas import AskResponse, RetrievedRef
from .generation import generate_verified
from .relevance import abstention, usable_passages
from ..routes import metrics

log = logging.getLogger("rahbar.answer")


def answer_question(
    question: str, retriever: Retriever, provider: LLMProvider, settings: Settings
) -> AskResponse:
    # Sessions/semantic cache are added in S12/S13 around this verified path.
    started=time.perf_counter()
    passages = usable_passages(retriever.retrieve(question, k=settings.top_k), settings.relevance_floor)
    trace=metrics.QUERY.get() or {}
    elapsed=time.perf_counter()-started+trace.get("prepare_ms",0)/1000
    metrics.RETRIEVAL.observe(elapsed)
    metrics.field("retrieval_ms",round(elapsed*1000,2))
    started=time.perf_counter()
    answer = generate_verified(question, passages, provider) if passages else abstention()
    elapsed=time.perf_counter()-started
    metrics.GENERATION.observe(elapsed)
    metrics.field("generation_ms",round(elapsed*1000,2))
    if not answer.answered_from_context:
        metrics.ABSTENTIONS.inc()
    metrics.field("abstained",not answer.answered_from_context)

    log.info(
        "answered",
        extra={
            "retriever": retriever.name,
            "provider": provider.name,
            "top_k": settings.top_k,
            "chunk_ids": [p.chunk_id for p in passages],
            "scores": [round(p.score, 4) for p in passages],
            "answered_from_context": answer.answered_from_context,
        },
    )
    return AskResponse(
        request_id=request_id_var.get(),
        answer=answer.answer,
        citations=answer.citations,
        answered_from_context=answer.answered_from_context,
        confidence=answer.confidence,
        retrieved=[
            RetrievedRef(
                chunk_id=p.chunk_id, source=p.source, section=p.section, page=p.page, score=p.score
            )
            for p in passages
        ],
        provider=provider.name,
    )
