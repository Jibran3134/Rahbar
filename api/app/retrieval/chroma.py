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
            raise IndexStateError("Query vector is invalid or dimension conflicts with active index")
        return active,collection,vectors[0]

    def retrieve_prepared(self, question: str, k: int,
                          prepared: tuple[ActiveIndex,Any,list[float]]) -> list[Passage]:
        if type(k) is not int or k <= 0:
            raise ValueError("k must be a positive integer")
        try:
            active, collection, vector = prepared
            where = version_filter(question)
            rows = collection.query(query_embeddings=[vector],n_results=min(k,collection.count()),
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
                passages.append(Passage(chunk_id=identifier,text=text,source=meta["source"],
                                        section=meta["section"],page=page,score=1-float(distance)))
            return passages
        except IndexStateError:
            raise
        except Exception:
            raise IndexStateError("Retrieval dependencies are unavailable or returned invalid data") from None
