"""Read-only version-aware retrieval with one active identity/query embedding."""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Any

import httpx

from ..config import Settings
from ..schemas import ActiveIndex, Passage
from .index_state import IndexStateError, resolve_active

log = logging.getLogger("rahbar.retrieval")


def version_filter(question: str) -> dict[str, Any]:
    """Only an edition date immediately attached to a policy noun selects history."""
    months = {name.lower(): str(i).zfill(2) for i, name in enumerate(
        ["January","February","March","April","May","June","July","August", "September",
         "October","November","December"],1)}
    pattern = (r"\b(?:(?P<month>" + "|".join(months) + r")\s+)?(?P<year>20\d{2})"
               r"(?:-(?P<number>0[1-9]|1[0-2]))?\s+(?:(?:undergraduate|academic)\s+)*"
               r"(?:rules|policy|handbook|edition)\b")
    match = re.search(pattern,question,re.I)
    if not match:
        return {"superseded": False}
    year = match.group("year")
    month = match.group("number") or months.get((match.group("month") or "").lower())
    if month:
        return {"doc_version": year + "-" + month}
    return {"doc_version": {"$in": [year] + [f"{year}-{i:02d}" for i in range(1,13)]}}


def heading_only(text: str, section: str) -> bool:
    """A repeated section label has no policy facts; retain short numeric facts."""
    def normalize(value: str) -> str:
        return re.sub(r"[\W_]+", "", value.casefold())
    return normalize(text) == normalize(section)


def page_context(collection: Any, title: str, metadata: dict[str, Any]) -> str | None:
    """Expand a matched PDF heading with authentic, bounded same-page context.

    The score remains the heading's actual query similarity. Context is fetched
    from the same immutable collection/source/page/version, never another edition.
    Short facts are retained whole; no new policy text or citation IDs are invented.
    """
    if Path(metadata['source']).suffix.lower() != '.pdf':
        return None  # HTML's logical page 1 is not a physical parent-page boundary.
    fields=('source','page','doc_version','superseded')
    rows=collection.get(where={'$and':[{key:metadata[key]} for key in fields]},
                        include=['documents','metadatas'],limit=32)
    documents,metadatas=rows.get('documents'),rows.get('metadatas')
    if not isinstance(documents,list) or not isinstance(metadatas,list) or len(documents)!=len(metadatas):
        raise IndexStateError('Parent-page context columns disagree')
    blocks=[]
    for text,meta in zip(documents,metadatas,strict=True):
        if (not isinstance(meta,dict) or any(type(meta.get(key)) is not type(metadata[key])
                                            or meta.get(key)!=metadata[key] for key in fields)
                or not isinstance(meta.get('section'),str) or not meta['section'].strip()
                or not isinstance(text,str) or not text.strip()):
            raise IndexStateError('Parent-page context identity is invalid')
        if not heading_only(text,meta['section']):
            blocks.append((meta['section'],text))
    used=len(title)
    selected=[]
    for section,text in sorted(set(blocks)):
        block=f'Section {section}: {text}'
        if used+len(block)+1<=1800:
            selected.append(block)
            used+=len(block)+1
        if len(selected)==8:
            break
    return '\n'.join([title,*selected]) if selected else None


class ChromaRetriever:
    name = "chroma"

    def __init__(self, settings: Settings, *, client: Any = None,
                 http_client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client
        self.http_client = http_client

    def get_client(self) -> Any:
        if self.client is not None:
            return self.client
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        return chromadb.HttpClient(host=self.settings.chroma_host, port=self.settings.chroma_port,
                                   settings=ChromaSettings(anonymized_telemetry=False))

    def retrieve(self, question: str, k: int) -> list[Passage]:
        return self.retrieve_prepared(question,k,self.prepare(question))

    def prepare(self, question: str) -> tuple[ActiveIndex,Any,list[float]]:
        """Resolve one generation and embed once, also usable by the cache."""
        try:
            return self._prepare(question)
        except IndexStateError:
            raise
        except Exception:
            raise IndexStateError("Query embedding dependencies are unavailable or invalid") from None

    def _prepare(self, question: str) -> tuple[ActiveIndex,Any,list[float]]:
        active, collection = resolve_active(self.get_client(),self.settings.collection)
        if active.embed_model != self.settings.embed_model:
            log.error("embedding model conflict",extra={"expected_model":self.settings.embed_model,
                                                       "actual_model":active.embed_model})
            raise IndexStateError("Configured embedding model conflicts with active index")
        connection = self.http_client or httpx.Client()
        try:
            response = connection.post(self.settings.ollama_url.rstrip("/") + "/api/embed",
                json={"model":self.settings.embed_model,"input":["search_query: " + question],
                      "truncate":False},timeout=60)
            response.raise_for_status()
            vectors=response.json()["embeddings"]
        finally:
            if self.http_client is None:
                connection.close()
        if (not isinstance(vectors,list) or len(vectors)!=1 or not isinstance(vectors[0],list)
                or len(vectors[0])!=active.dimension
                or any(type(v) not in (int,float) or not math.isfinite(v) for v in vectors[0])
                or not any(v!=0 for v in vectors[0])):
            observed=len(vectors[0]) if isinstance(vectors,list) and vectors and isinstance(vectors[0],list) else None
            log.error("embedding vector conflict",extra={"expected_dimension":active.dimension,"actual_dimension":observed})
            raise IndexStateError("Query vector is invalid or dimension conflicts with active index")
        return active,collection,vectors[0]

    def retrieve_prepared(self, question: str, k: int,
                          prepared: tuple[ActiveIndex,Any,list[float]]) -> list[Passage]:
        if type(k) is not int or k <= 0:
            raise ValueError("k must be a positive integer")
        try:
            active, collection, vector = prepared
            where = version_filter(question)
            # Fetch a bounded candidate pool so title-only chunks do not crowd
            # actual policy clauses out of the requested top-k evidence.
            rows = collection.query(query_embeddings=[vector],n_results=min(k*3,collection.count()),
                                    where=where,include=["documents","metadatas","distances"])
            columns = [rows[key][0] for key in ("ids","documents","metadatas","distances")]
            if len({len(col) for col in columns}) != 1:
                raise IndexStateError("Retrieved result columns disagree")
            passages = []
            for identifier,text,meta,distance in zip(*columns,strict=True):
                if (not isinstance(meta,dict)
                        or any(not isinstance(meta.get(key),str) or not meta[key].strip()
                               for key in ("source","section","doc_version"))
                        or type(meta.get("page")) is not int or meta["page"] <= 0
                        or type(meta.get("superseded")) is not bool
                        or not isinstance(identifier,str) or not identifier or not isinstance(text,str)
                        or not text.strip() or type(distance) not in (float,int)
                        or not math.isfinite(distance) or not 0 <= distance <= 2):
                    raise IndexStateError("Retrieved passage metadata or distance is invalid")
                if where == {"superseded": False} and meta["superseded"]:
                    raise IndexStateError("Unexpected superseded result")
                if "doc_version" in where:
                    wanted = where["doc_version"]
                    if meta["doc_version"] not in (wanted["$in"] if isinstance(wanted,dict) else [wanted]):
                        raise IndexStateError("Unexpected historical version result")
                page = None if Path(meta["source"]).suffix.lower() in {".html",".htm"} else meta["page"]
                if heading_only(text,meta["section"]):
                    expanded=page_context(collection,text,meta)
                    if not expanded:
                        continue
                    text=expanded
                passages.append(Passage(chunk_id=identifier,text=text,source=meta["source"],
                                        section=meta["section"],page=page,score=1-float(distance)))
                if len(passages)==k:
                    break
            return passages[:k]
        except IndexStateError:
            raise
        except Exception:
            raise IndexStateError("Retrieval dependencies are unavailable or returned invalid data") from None
