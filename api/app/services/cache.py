"""Bounded Redis semantic candidates, namespaced by immutable index/config identity."""
import hashlib
import json
import math
import re
import time
from types import SimpleNamespace
from typing import Any

from ..config import Settings
from ..logjson import request_id_var
from ..providers.llm.base import LLMProvider
from ..retrieval.chroma import version_filter
from ..schemas import ActiveIndex, Answer, AskResponse, Passage
from .grounding import validate_grounding
from ..routes import metrics

PROMPT_VERSION="grounded-v12-instruct-decimal-policy"
_NUMBERS = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:%)?(?!\w)")
_SCOPE_TERMS = re.compile(r"hostel|admission|withdraw\w*|tuition|deposit|prerequisite|"
                          r"lab|theory|not|never|without|cannot|optional|[a-z]{2,}-\d+")
_CUMULATIVE_GPA = re.compile(r"\bcgpa\b|\bcumulative\b")
_SEMESTER_GPA = re.compile(r"\bsgpa\b|\bsemester\b")
_UNSPECIFIED_GPA = re.compile(r"\bgpa\b")
_COURSE_CODES = re.compile(r"\b[a-z]{2,}[- ]?\d{2,}\b")


def namespace(active: ActiveIndex, settings: Settings) -> str:
    data=[active.model_dump(),settings.llm_model,settings.llm_provider,settings.temperature,
          settings.top_k,settings.relevance_floor,settings.cache_threshold,PROMPT_VERSION]
    return "rahbar:cache:v1:"+hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


def signature(question: str) -> tuple[Any,...]:
    text=question.lower()
    numbers=tuple(sorted(_NUMBERS.findall(text)))
    scope=tuple(sorted(set(_SCOPE_TERMS.findall(text))))
    # A semester result cannot stand in for a cumulative result, even when the
    # embeddings and numbers match. Normalize abbreviations without equating an
    # unspecified GPA with either interpretation.
    gpa_scope=[]
    if _CUMULATIVE_GPA.search(text):
        gpa_scope.append("gpa:cumulative")
    if _SEMESTER_GPA.search(text):
        gpa_scope.append("gpa:semester")
    if not gpa_scope and _UNSPECIFIED_GPA.search(text):
        gpa_scope.append("gpa:unspecified")
    scope=tuple(sorted((*scope,*gpa_scope)))
    courses=tuple(sorted(_COURSE_CODES.findall(text)))
    return numbers,scope,courses,json.dumps(version_filter(question),sort_keys=True)


def cosine(a: list[float], b: list[float]) -> float:
    if len(a)!=len(b) or not a or any(type(v) not in (int,float) or not math.isfinite(v) for v in a+b):
        return -1
    norm=math.sqrt(sum(v*v for v in a)*sum(v*v for v in b))
    return sum(x*y for x,y in zip(a,b,strict=True))/norm if norm else -1


def cache_exclusion(response: AskResponse) -> str | None:
    if not response.answered_from_context:
        return "not_grounded"
    if response.confidence=="low":
        return "low_confidence"
    if not response.retrieved:
        return "no_evidence"
    try:
        answer=Answer(reasoning="cache integrity",**response.model_dump(include={
            "answer","citations","answered_from_context","confidence"}))
        refs=[Passage(text="Cached immutable-generation evidence reference",**r.model_dump()) for r in response.retrieved]
        validate_grounding(answer,refs)
        return None
    except (ValueError,RuntimeError):
        return "invalid_citations"


def safe(response: AskResponse) -> bool:
    return cache_exclusion(response) is None


class SemanticCache:
    def __init__(self, client: Any, settings: Settings):
        self.client,self.settings=client,settings

    def get(self,key: str,question: str,vector: list[float],*,now: float|None=None) -> AskResponse|None:
        now=time.time() if now is None else now
        best=None
        best_score=self.settings.cache_threshold
        for raw in self.client.zrange(key,-self.settings.cache_max_entries,-1):
            try:
                entry=json.loads(raw)
                if entry["expires"]<=now or signature(question)!=signature(entry["question"]):
                    continue
                score=cosine(vector,entry["vector"])
                response=AskResponse.model_validate(entry["response"],strict=True)
                if score>=best_score and safe(response):
                    best,best_score=response,score
            except (ValueError,TypeError,KeyError):
                continue
        return best

    def put(self,key: str,question: str,vector: list[float],response: AskResponse,*,now: float|None=None) -> None:
        if not safe(response) or cosine(vector,vector)<0:
            return
        now=time.time() if now is None else now
        entry=json.dumps(dict(question=question,vector=vector,expires=now+self.settings.cache_ttl_seconds,
                              response=response.model_copy(update={"session_id":None,"request_id":"-"}).model_dump()))
        with self.client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(key,"-inf",now)
            pipe.zadd(key,{entry:now+self.settings.cache_ttl_seconds})
            pipe.zremrangebyrank(key,0,-self.settings.cache_max_entries-1)
            pipe.expire(key,self.settings.cache_ttl_seconds)
            pipe.execute()


def answer_cached(question: str,retriever: Any,provider: LLMProvider,settings: Settings,
                  cache: SemanticCache,*,follow_up: bool=False) -> tuple[AskResponse,str]:
    from .answer import answer_question
    if follow_up:
        metrics.field("cache_reason","conversation_context")
        return answer_question(question,retriever,provider,settings),"BYPASS"
    started=time.perf_counter()
    prepared=retriever.prepare(question)
    preparation=time.perf_counter()-started
    metrics.field("prepare_ms",preparation*1000)
    active,_,vector=prepared
    key=namespace(active,settings)
    metrics.CACHE_LOOKUPS.inc()
    cached=cache.get(key,question,vector)
    if cached:
        metrics.field("cache_reason","matched")
        metrics.CACHE_HITS.inc()
        metrics.RETRIEVAL.observe(preparation)
        metrics.field("retrieval_ms",round(preparation*1000,2))
        metrics.field("generation_ms",0)
        metrics.field("abstained",False)
        return cached.model_copy(update={"request_id":request_id_var.get(),"session_id":None}),"HIT"
    frozen=SimpleNamespace(name=retriever.name,retrieve=lambda q,k:retriever.retrieve_prepared(q,k,prepared))
    result=answer_question(question,frozen,provider,settings)
    cache.put(key,question,vector,result)
    reason=cache_exclusion(result) or "miss_stored"
    trace=metrics.QUERY.get() or {}
    if reason=="not_grounded" and trace.get("fallback"):
        reason="generation_timeout" if trace.get("generation_failure")=="timeout" else "generation_failure"
    metrics.field("cache_reason",reason)
    return result,"MISS"
