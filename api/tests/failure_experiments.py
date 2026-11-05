"""S20 isolated actual stage perturbations; no production code/config mutation."""
import hashlib
import importlib
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

import yaml
from live_support import ROOT

sys.path[:0]=[str(ROOT/"api"),str(ROOT/"indexer"),str(ROOT/"eval")]
from app.config import Settings  # noqa: E402
from app.retrieval.chroma import ChromaRetriever,version_filter  # noqa: E402
from app.retrieval.index_state import resolve_active  # noqa: E402
from app.services.relevance import usable_passages  # noqa: E402
from app.schemas import Passage  # noqa: E402
from pipeline.config import get_settings  # noqa: E402
from pipeline.chunk import chunk  # noqa: E402
from pipeline.embed import embed  # noqa: E402
from pipeline.models import Chunk,Document,Page  # noqa: E402
from pipeline.store import store,get_client  # noqa: E402
from run_eval import recall_at_k,gate  # noqa: E402

base=ROOT/"docs/evidence/app/sprints"
raw=ROOT/"corpus/raw"
questions=yaml.safe_load((ROOT/"eval/golden.yaml").read_text(encoding="utf-8"))["questions"]
settings=replace(get_settings(),chroma_host="127.0.0.1",chroma_port=8001,ollama_url="http://127.0.0.1:11434")
api=Settings(chroma_host="127.0.0.1",chroma_port=8001,ollama_url=settings.ollama_url)
client=get_client(settings)
before=resolve_active(client,"rahbar")[0]
retriever=ChromaRetriever(api,client=client)
vectors={q["id"]:retriever.prepare(q["question"])[2] for q in questions}
def measure(reader,k=5,no_filter=False):
    active,col=resolve_active(client,reader.settings.collection)
    rows=[]
    for q in questions:
        if no_filter:
            result=col.query(query_embeddings=[vectors[q["id"]]],n_results=k,include=["documents","metadatas","distances"])
            hits=[Passage(chunk_id=i,text=t,source=m["source"],section=m["section"],
                page=None if Path(m["source"]).suffix in {".html",".htm"} else m["page"],score=1-d)
                for i,t,m,d in zip(result["ids"][0],result["documents"][0],result["metadatas"][0],result["distances"][0])]
            disallowed=sum(m["superseded"] for m in result["metadatas"][0]) if version_filter(q["question"])=={"superseded":False} else 0
        else:
            hits=reader.retrieve_prepared(q["question"],k,(active,col,vectors[q["id"]]))
            disallowed=0
        hits=usable_passages(hits,api.relevance_floor)
        refs=[p.model_dump(exclude={"text"}) for p in hits]
        rows.append(dict(id=q["id"],type=q["type"],recall5=recall_at_k(q["relevant"],refs,5),
                         disallowed_historical_hits=disallowed,retrieved=refs))
    values=[r["recall5"] for r in rows if r["recall5"] is not None]
    return dict(recall5=sum(values)/len(values),rows=rows)

normal=measure(retriever)
top1=measure(retriever,k=1)
unfiltered=measure(retriever,no_filter=True)
print("Retrieval perturbations complete",flush=True)

# Disable only the real OCR adapter. Empty scanned content must fail ingestion.
extractor=importlib.import_module("pipeline.extract")
original=extractor._ocr_image
try:
    extractor._ocr_image=lambda image:""
    try:
        extractor.extract(str(raw/"faculty-entrepreneurship-and-technical-start-ups-policy.pdf"),"2022-05-30",False)
    except RuntimeError as error:
        ocr=dict(failed=True,error=str(error))
    else:
        ocr=dict(failed=False)
finally:
    extractor._ocr_image=original

# Fixed windows, no overlap, first-token section convention; genuine boundary loss.
fixed=[]
for entry in json.loads((raw/"_index.json").read_text(encoding="utf-8")):
    text=(raw/"_s04-cleaned"/(entry["file"]+".txt")).read_text(encoding="utf-8")
    matches=re.findall(r"\n--- SOURCE PAGE (\d+); OCR=(True|False) ---\n(.*?)(?=\n\n--- SOURCE PAGE|\Z)",text,re.S)
    doc=Document(entry["file"],entry["doc_version"],entry["superseded"],
        [Page(entry["file"],int(p),body,ocr=="True") for p,ocr,body in matches])
    sections=chunk(doc,100000,0)
    for page in doc.pages:
        pieces=[c for c in sections if c.page==page.page]
        joined=""
        spans=[]
        for piece in pieces:
            start=len(joined)
            joined+=piece.text+"\n"
            spans.append((start,len(joined),piece.section))
        tokens=list(re.finditer(r"\w{1,4}|[^\w\s]",joined))
        for start in range(0,len(tokens),100):
            end=min(start+100,len(tokens))
            label=next(label for low,high,label in spans if low<=tokens[start].start()<high)
            body=joined[tokens[start].start():tokens[end-1].end()]
            identity=hashlib.sha256(f"fixed100:{doc.source}:{page.page}:{start}:{body}".encode()).hexdigest()
            fixed.append(Chunk(identity,body,doc.source,label,page.page,doc.doc_version,doc.superseded))
vector_path=raw/"_s20-fixed-vectors.json"
if vector_path.exists():
    fvec=json.loads(vector_path.read_text(encoding="utf-8"))
else:
    fvec=embed([c.text for c in fixed],settings)
    vector_path.write_text(json.dumps(fvec),encoding="utf-8")
store(fixed,fvec,replace(settings,collection="rahbar_failure_fixed100"),client=client)
fixed_result=measure(ChromaRetriever(replace(api,collection="rahbar_failure_fixed100"),client=client))
assert ocr["failed"] and top1["recall5"]<normal["recall5"] and fixed_result["recall5"]<normal["recall5"]
assert any(r["disallowed_historical_hits"]>0 for r in unfiltered["rows"])
assert resolve_active(client,"rahbar")[0]==before,"Normal publication was modified"
restored=measure(retriever)
assert restored["recall5"]==normal["recall5"]
final=json.loads((ROOT/"eval/results.json").read_text(encoding="utf-8"))
baseline=json.loads((ROOT/"eval/baseline.json").read_text(encoding="utf-8"))
assert not gate(final,baseline)
report=dict(passed=True,baseline=normal,top_k_1=top1,unfiltered=unfiltered,ocr_disabled=ocr,
    fixed100=fixed_result,fixed_chunks=len(fixed),restored=restored,active_identity_unchanged=before.model_dump(),
    scope="Actual OCR/render failure and real vector queries/builds; no new generated-answer claims; final native baseline gate rechecked")
(base/"S20-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print("S20 PASS",normal["recall5"],top1["recall5"],fixed_result["recall5"],flush=True)
