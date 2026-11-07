"""Safe bounded semantic reuse and generation/config isolation."""
from app.config import Settings
from app.schemas import ActiveIndex, AskResponse, Citation, RetrievedRef


class Memory:
    def __init__(self):
        self.rows={}
    def zrange(self,key,start,end):
        rows=sorted(self.rows.get(key,{}),key=self.rows.get(key,{}).get)
        return rows[start:None if end==-1 else end+1]
    def pipeline(self,**kwargs):
        return self
    def __enter__(self):
        return self
    def __exit__(self,*args):
        pass
    def zremrangebyscore(self,key,low,high):
        self.rows[key]={v:s for v,s in self.rows.get(key,{}).items() if s>float(high)}
    def zadd(self,key,mapping):
        self.rows.setdefault(key,{}).update(mapping)
    def zremrangebyrank(self,key,start,end):
        for value in self.zrange(key,start,end):
            self.rows[key].pop(value)
    def expire(self,*args):
        pass
    def execute(self):
        return []


def response():
    return AskResponse(request_id="old",answer="Makeup week [p.pdf / 4.25].",
        citations=[Citation(source="p.pdf",section="4.25",page=1)],answered_from_context=True,
        confidence="high",retrieved=[RetrievedRef(chunk_id="a",source="p.pdf",section="4.25",page=1,score=.9)],provider="ollama")


def test_hit_threshold_ttl_bounds_and_generation_namespace():
    from app.services.cache import SemanticCache, namespace
    from dataclasses import replace
    config=Settings(cache_max_entries=2,cache_ttl_seconds=10)
    active=ActiveIndex(collection="rahbar__g_a",generation="a",embed_model="nomic-embed-text",dimension=2)
    key=namespace(active,config)
    cache=SemanticCache(Memory(),config)
    cache.put(key,"course withdrawal deadline",[1,0],response(),now=1)
    assert cache.get(key,"deadline for course withdrawal",[1,0],now=2)
    assert cache.get(key,"deadline for course withdrawal",[1,0],now=12) is None
    assert namespace(active.model_copy(update={"generation":"b"}),config)!=key
    assert namespace(active,replace(config,temperature=.1))!=key
    for i in range(5):
        cache.put(key,f"course withdrawal {i}",[1,0],response(),now=2+i)
    assert len(cache.client.zrange(key,0,-1))<=2


def test_numeric_version_scope_and_unsafe_answer_exclusions():
    from app.services.cache import SemanticCache
    cache=SemanticCache(Memory(),Settings())
    cache.put("key","withdrawal under August 2023 rules",[1,0],response(),now=1)
    assert cache.get("key","withdrawal under current rules",[1,0],now=2) is None
    cache.put("fees","admission deposit Rs 20000",[1,0],response(),now=1)
    assert cache.get("fees","hostel deposit Rs 20000",[1,0],now=2) is None
    assert cache.get("fees","admission deposit Rs 30000",[1,0],now=2) is None
    unsafe=response().model_copy(update={"answered_from_context":False,"citations":[]})
    cache.put("unsafe","withdrawal",[1,0],unsafe,now=1)
    assert not cache.client.zrange("unsafe",0,-1)


def test_cache_preparation_embeds_once_and_followup_bypasses():
    from types import SimpleNamespace
    from app.services.cache import SemanticCache, answer_cached
    from app.schemas import Answer, Passage
    config=Settings()
    calls=[]
    active=ActiveIndex(collection="rahbar__g_a",generation="a",embed_model="nomic-embed-text",dimension=2)
    p=Passage(chunk_id="a",text="Makeup week.",source="p.pdf",section="4.25",page=1,score=.9)
    def prepare(q):
        calls.append(q)
        return active,None,[1,0]
    retriever=SimpleNamespace(name="chroma",prepare=prepare,retrieve_prepared=lambda q,k,prepared:[p],retrieve=lambda q,k:[p])
    provider=SimpleNamespace(name="ollama",generate=lambda q,p:Answer(reasoning="private",**response().model_dump(
        include={"answer","citations","answered_from_context","confidence"})))
    cache=SemanticCache(Memory(),config)
    assert answer_cached("withdrawal",retriever,provider,config,cache)[1]=="MISS"
    assert len(calls)==1
    assert answer_cached("withdrawal",retriever,provider,config,cache)[1]=="HIT"
    assert answer_cached("withdrawal",retriever,provider,config,cache,follow_up=True)[1]=="BYPASS"


def test_threshold_boundary_course_codes_and_negation():
    import math
    from app.services.cache import SemanticCache
    cache=SemanticCache(Memory(),Settings(cache_threshold=.95))
    cache.put("key","Is CS101 required?",[1,0],response(),now=1)
    assert cache.get("key","Is CS102 required?",[1,0],now=2) is None
    assert cache.get("key","Is CS101 not required?",[1,0],now=2) is None
    assert cache.get("key","Is CS101 required?",[.95,math.sqrt(1-.95**2)],now=2)
    assert cache.get("key","Is CS101 required?",[.949,math.sqrt(1-.949**2)],now=2) is None


def test_gpa_cache_distinguishes_cumulative_semester_and_unspecified_values():
    from app.services.cache import SemanticCache
    cache=SemanticCache(Memory(),Settings())
    cache.put("gpa","My CGPA is 3.6; academic warning?",[1,0],response(),now=1)
    assert cache.get("gpa","My cumulative GPA is 3.6; academic warning?",[1,0],now=2)
    for question in ["My semester GPA is 3.6; academic warning?",
                     "My SGPA is 3.6; academic warning?",
                     "My GPA is 3.6; academic warning?",
                     "My CGPA is 1.6; academic warning?"]:
        assert cache.get("gpa",question,[1,0],now=2) is None
    cache.put("semester","My SGPA is 3.6; academic warning?",[1,0],response(),now=1)
    assert cache.get("semester","My semester GPA is 3.6; academic warning?",[1,0],now=2)


def test_http_repeat_hit_is_identical_and_session_followup_is_bypassed(monkeypatch):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from app.main import app
    from app.schemas import Answer, Passage
    from app.services.cache import SemanticCache
    from app.services.sessions import SessionStore
    from test_sessions import RedisDouble
    monkeypatch.setenv("RETRIEVER","stub")
    monkeypatch.setenv("LLM_PROVIDER","stub")
    active=ActiveIndex(collection="g-a",generation="a",embed_model="nomic-embed-text",dimension=2)
    p=Passage(chunk_id="a",text="Makeup week.",source="p.pdf",section="4.25",page=1,score=.9)
    calls=[]
    def generate(q,passages):
        calls.append(q)
        return Answer(reasoning="private",**response().model_dump(include={
            "answer","citations","answered_from_context","confidence"}))
    with TestClient(app) as client:
        app.state.cache=SemanticCache(Memory(),app.state.settings)
        app.state.sessions=SessionStore(RedisDouble(),ttl=30)
        app.state.retriever=SimpleNamespace(name="chroma",prepare=lambda q:(active,None,[1,0]),
            retrieve_prepared=lambda q,k,prepared:[p],retrieve=lambda q,k:[p])
        app.state.provider=SimpleNamespace(name="ollama",generate=generate)
        first=client.post("/api/ask",json={"question":"course withdrawal deadline"})
        second=client.post("/api/ask",json={"question":"course withdrawal deadline"})
        assert first.headers["X-Cache"]=="MISS" and first.headers["X-Cache-Reason"]=="miss_stored"
        assert second.headers["X-Cache"]=="HIT" and second.headers["X-Cache-Reason"]=="matched"
        for field in ["answer","citations","answered_from_context","confidence","retrieved","provider"]:
            assert first.json()[field]==second.json()[field]
        assert "reasoning" not in second.json()
        assert first.json()["request_id"]!=second.json()["request_id"]
        assert len(calls)==1  # A real cache hit must not call the provider again.
        follow=client.post("/api/ask",json={"question":"And under the old rules?",
                                           "session_id":first.json()["session_id"]})
        assert follow.headers["X-Cache"]=="BYPASS"
        assert follow.headers["X-Cache-Reason"]=="conversation_context"
        forced=client.post("/api/ask",json={"question":"course withdrawal deadline"},headers={"X-Bypass-Cache":"true"})
        assert forced.headers["X-Cache-Reason"]=="requested_bypass"
        assert len(calls)==3


def test_refusal_miss_explains_why_it_was_not_stored(monkeypatch):
    from types import SimpleNamespace
    from app.routes import metrics
    from app.services.cache import SemanticCache, answer_cached
    from app.services.relevance import abstention
    active=ActiveIndex(collection="g-a",generation="a",embed_model="nomic-embed-text",dimension=2)
    retriever=SimpleNamespace(name="chroma",prepare=lambda q:(active,None,[1,0]),
        retrieve_prepared=lambda *a,**k:[])
    trace={}
    token=metrics.QUERY.set(trace)
    memory=Memory()
    try:
        provider=SimpleNamespace(name="unused",generate=lambda *a,**k:None)
        result,status=answer_cached("Hostel deadline",retriever,provider,Settings(),SemanticCache(memory,Settings()))
        assert status=="MISS" and result.answer==abstention().answer
        assert trace["cache_reason"]=="not_grounded"
        assert not memory.rows
    finally:
        metrics.QUERY.reset(token)


def test_model_timeout_miss_is_not_reported_as_missing_document_evidence():
    from types import SimpleNamespace
    from app.routes import metrics
    from app.schemas import Passage
    from app.providers.llm.base import ProviderError,ProviderFailureKind
    from app.services.cache import SemanticCache,answer_cached
    active=ActiveIndex(collection="g-a",generation="a",embed_model="nomic-embed-text",dimension=2)
    p=Passage(chunk_id="a",text="The required CGPA is 2.00.",source="p.pdf",section="5.4",page=24,score=.9)
    retriever=SimpleNamespace(name="chroma",prepare=lambda q:(active,None,[1,0]),
        retrieve_prepared=lambda *a,**k:[p])
    def fail(*args,**kwargs):
        raise ProviderError(ProviderFailureKind.TIMEOUT)
    trace={}
    token=metrics.QUERY.set(trace)
    memory=Memory()
    try:
        result,status=answer_cached("Academic warning?",retriever,SimpleNamespace(name="ollama",generate=fail),
            Settings(),SemanticCache(memory,Settings()))
        assert status=="MISS" and result.answered_from_context is False
        assert trace['cache_reason']=='generation_timeout' and trace['fallback'] is True
        assert not memory.rows
    finally:
        metrics.QUERY.reset(token)
