"""S19 real candidate builds/retrieval and explicit small cache calibration set.

No golden rewrite, generation claims or automatic baseline updates.
"""
import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import yaml

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/"api"),str(ROOT/"indexer"),str(ROOT/"eval")]
from app.config import Settings  # noqa: E402
from app.retrieval.chroma import ChromaRetriever  # noqa: E402
from app.retrieval.index_state import resolve_active  # noqa: E402
from app.services.cache import cosine,signature  # noqa: E402
from pipeline.config import get_settings  # noqa: E402
from pipeline.embed import embed  # noqa: E402
from pipeline.models import Chunk  # noqa: E402
from pipeline.store import store,get_client  # noqa: E402
from run_eval import recall_at_k  # noqa: E402

base=ROOT/"docs/evidence/app/sprints"
raw=ROOT/"corpus/raw"
golden=ROOT/"eval/golden.yaml"
freeze=json.loads((ROOT/"eval/golden.freeze.json").read_text())
assert hashlib.sha256(golden.read_text(encoding="utf-8-sig").encode()).hexdigest()==freeze["golden_sha256"]
questions=yaml.safe_load(golden.read_text(encoding="utf-8"))["questions"]
settings=replace(get_settings(),chroma_host="127.0.0.1",chroma_port=8001,ollama_url="http://127.0.0.1:11434")
client=get_client(settings)
qvectors={}
configs=[]
structural=json.loads((base/"S05-live.json").read_text())["configurations"]
for size,overlap in [(250,30),(400,50),(650,80)]:
    print("BUILD",size,overlap,flush=True)
    path=raw/f"_s05-chunks/chunks-{size}-{overlap}.jsonl"
    chunks=[Chunk(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()]
    cache=raw/f"_s19-vectors-{size}.json"
    if cache.exists():
        vectors=json.loads(cache.read_text(encoding="utf-8"))
    elif size==400:
        old=json.loads((raw/"_s07-vectors.json").read_text(encoding="utf-8"))
        assert old["chunks_sha256"]==hashlib.sha256(path.read_bytes()).hexdigest()
        vectors=old["vectors"]
        cache.write_text(json.dumps(vectors),encoding="utf-8")
    else:
        vectors=embed([c.text for c in chunks],settings)
        cache.write_text(json.dumps(vectors),encoding="utf-8")
    config=replace(settings,collection=f"rahbar_experiment_{size}")
    store(chunks,vectors,config,client=client)
    retriever=ChromaRetriever(Settings(chroma_host="127.0.0.1",chroma_port=8001,
        ollama_url=settings.ollama_url,collection=config.collection))
    active,collection=resolve_active(client,config.collection)
    rows=[]
    for q in questions:
        if q["id"] not in qvectors:
            qvectors[q["id"]]=retriever.prepare(q["question"])[2]
        hits=retriever.retrieve_prepared(q["question"],5,(active,collection,qvectors[q["id"]]))
        refs=[p.model_dump(exclude={"text"}) for p in hits]
        rows.append(dict(id=q["id"],type=q["type"],relevant=q["relevant"],must_abstain=q.get("must_abstain",False),
            hits=refs,recall3=recall_at_k(q["relevant"],refs,3),recall5=recall_at_k(q["relevant"],refs,5)))
    def mean(values):
        values=[v for v in values if v is not None]
        return sum(values)/len(values) if values else None
    floors=[]
    for floor in [.45,.65,.70,.74,.75,.78]:
        recalls=[recall_at_k(r["relevant"],r["hits"] if any(p["score"]>=floor for p in r["hits"]) else [],5) for r in rows]
        absent=sum(any(p["score"]>=floor for p in r["hits"]) for r in rows if r["must_abstain"])
        floors.append(dict(floor=floor,recall5=mean(recalls),absent_queries_reaching_generation=absent))
    counts=next(s for s in structural if s["size"]==size)
    configs.append(dict(size=size,overlap=overlap,chunks=len(chunks),recall3=mean([r["recall3"] for r in rows]),
        recall5=mean([r["recall5"] for r in rows]),amplification=counts["amplification"],
        original_tokens=counts["original_tokens"],stored_tokens=counts["stored_tokens"],floors=floors,
        by_type={kind:mean([r["recall5"] for r in rows if r["type"]==kind]) for kind in sorted({r["type"] for r in rows})},
        rows=rows,active=active.model_dump()))
    (base/"S19-partial.json").write_text(json.dumps(configs,indent=2),encoding="utf-8")
best=max(configs,key=lambda c:(c["recall5"],c["recall3"],-c["amplification"]))
admissible=[f for f in best["floors"] if f["absent_queries_reaching_generation"]==0]
floor=min(admissible,key=lambda f:f["floor"])["floor"]
pairs=[
    (True,"What is the course withdrawal deadline?","When is the course withdrawal deadline?"),
    (True,"What is the admission security deposit?","How much is the admission security deposit?"),
    (False,"Attendance is 80 percent?","Attendance is 90 percent?"),
    (False,"Is CS101 required?","Is CS102 required?"),
    (False,"What is the admission deposit?","What is the hostel deposit?"),
    (False,"Withdrawal under August 2023 rules?","Withdrawal under June 2026 rules?"),
    (False,"What is the regular semester withdrawal deadline?","What is the summer semester withdrawal deadline?")]
retriever=ChromaRetriever(Settings(chroma_host="127.0.0.1",chroma_port=8001,ollama_url=settings.ollama_url))
cache_rows=[]
for positive,a,b in pairs:
    va,vb=retriever.prepare(a)[2],retriever.prepare(b)[2]
    cache_rows.append(dict(positive=positive,a=a,b=b,cosine=cosine(va,vb),compatible=signature(a)==signature(b)))
thresholds=[]
for threshold in [.90,.95,.98]:
    thresholds.append(dict(threshold=threshold,positive_hits=sum(r["positive"] and r["compatible"] and r["cosine"]>=threshold for r in cache_rows),
        false_hits=sum(not r["positive"] and r["compatible"] and r["cosine"]>=threshold for r in cache_rows)))
safe=[t for t in thresholds if t["false_hits"]==0]
(base/"S19-cache-sample.json").write_text(json.dumps(dict(pairs=cache_rows,thresholds=thresholds),indent=2),encoding="utf-8")
assert safe,"Cache guards need repair: measured false reuse at every candidate threshold"
chosen=max(safe,key=lambda t:(t["positive_hits"],t["threshold"]))
report=dict(passed=True,scope="Real embedding/Chroma retrieval; cache sample calibration only, generation baseline follows",
    configurations=configs,cache_pairs=cache_rows,cache_thresholds=thresholds,
    selected=dict(size=best["size"],overlap=best["overlap"],relevance_floor=floor,cache_threshold=chosen["threshold"]))
(base/"S19-measurements.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report["selected"],indent=2),flush=True)
