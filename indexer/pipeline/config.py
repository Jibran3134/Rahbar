"""Indexer configuration, from the same ConfigMap the API reads (section 4.1)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None


def _token(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise ValueError(f"{name} must be nonempty and contain no whitespace")


def _http_base_url(value: str) -> None:
    _token("OLLAMA_URL", value)
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                 and parsed.port != 0 and not parsed.query and not parsed.fragment
                 and parsed.username is None and parsed.password is None)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("OLLAMA_URL must be an HTTP(S) base URL without credentials/query/fragment")


@dataclass(frozen=True)
class IndexerSettings:
    embed_model: str        # EMBED_MODEL: must equal the API's value (section 4.4)
    chroma_host: str
    chroma_port: int
    collection: str
    corpus_dir: str         # where the documents and _index.json sit inside the Job's pod
    chunk_size: int
    chunk_overlap: int
    ollama_url: str

    def __post_init__(self) -> None:
        for name, value in (("EMBED_MODEL", self.embed_model),
                            ("CHROMA_HOST", self.chroma_host),
                            ("CHROMA_COLLECTION", self.collection)):
            _token(name, value)
        if "://" in self.chroma_host:
            raise ValueError("CHROMA_HOST must be a hostname, not a URL")
        if type(self.chroma_port) is not int or not 1 <= self.chroma_port <= 65535:
            raise ValueError("CHROMA_PORT must be an integer from 1 to 65535")
        if not isinstance(self.corpus_dir, str) or not self.corpus_dir.strip():
            raise ValueError("CORPUS_DIR must be a nonempty path")
        if type(self.chunk_size) is not int or self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE must be a positive integer")
        if (type(self.chunk_overlap) is not int or self.chunk_overlap < 0
                or self.chunk_overlap >= self.chunk_size):
            raise ValueError("CHUNK_OVERLAP must satisfy 0 <= overlap < CHUNK_SIZE")
        _http_base_url(self.ollama_url)


def get_settings() -> IndexerSettings:
    return IndexerSettings(
        embed_model=os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        chroma_host=os.environ.get("CHROMA_HOST", "chroma"),
        chroma_port=_int("CHROMA_PORT", 8000),
        collection=os.environ.get("CHROMA_COLLECTION", "rahbar"),
        corpus_dir=os.environ.get("CORPUS_DIR", "/corpus"),
        chunk_size=_int("CHUNK_SIZE", 250),
        chunk_overlap=_int("CHUNK_OVERLAP", 30),
        ollama_url=os.environ.get("OLLAMA_URL", "http://host.minikube.internal:11434"),
    )
