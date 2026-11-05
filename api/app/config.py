"""Runtime configuration, read once from environment variables.

On the cluster these variables come from your ConfigMap and Secret (section 4.1).
Nothing here is baked into the image, so one image runs in every environment.
S02 validates settings without contacting dependencies. Threshold defaults are
provisional until the S19 measurements; no cache/provider behavior is implied.
"""

from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f"{name} must be an integer") from None


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        raise ValueError(f"{name} must be a finite number") from None


def _token(name: str, value: str) -> None:
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise ValueError(f"{name} must be nonempty and contain no whitespace")


def _positive_int(name: str, value: int, maximum: int | None = None) -> None:
    if type(value) is not int or value <= 0 or (maximum is not None and value > maximum):
        raise ValueError(f"{name} must be a positive integer" +
                         (f" at most {maximum}" if maximum is not None else ""))


def _number(name: str, value: float, minimum: float, maximum: float | None = None) -> None:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < minimum
            or (maximum is not None and value > maximum)):
        raise ValueError(f"{name} must be finite and within its configured range")


def _http_base_url(name: str, value: str) -> None:
    _token(name, value)
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                 and parsed.port != 0 and not parsed.query and not parsed.fragment
                 and parsed.username is None and parsed.password is None)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(f"{name} must be an HTTP(S) base URL without credentials/query/fragment")


def _redis_url(value: str) -> None:
    _token("REDIS_URL", value)
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme in {"redis", "rediss"} and bool(parsed.hostname)
                 and parsed.port != 0 and not parsed.query and not parsed.fragment
                 and (parsed.path in {"", "/"} or re.fullmatch(r"/[0-9]+", parsed.path) is not None))
    except ValueError:
        valid = False
    if not valid:
        # Do not echo URLs: they can contain credentials, including on parse failures.
        raise ValueError("REDIS_URL must be a redis(s) URL with a valid port and database number")


@dataclass(frozen=True)
class Settings:
    # Which implementations to load. "stub" needs no cluster, no model, no network.
    retriever: str = "stub"          # RETRIEVER: stub | chroma
    llm_provider: str = "stub"       # LLM_PROVIDER: stub | ollama-host

    # The embedding pin (section 4.4). The indexer reads the same ConfigMap key.
    embed_model: str = "nomic-embed-text"

    # Vector store
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    collection: str = "rahbar"

    # Retrieval and generation
    top_k: int = 5
    temperature: float = 0.2
    relevance_floor: float = 0.74   # S19 measured selected-corpus operating point
    llm_model: str = "llama3.2:3b"
    ollama_url: str = "http://host.minikube.internal:11434"
    hosted_base_url: str = ""        # e.g. an OpenAI-compatible endpoint
    llm_api_key: str = field(default="", repr=False)   # from the Secret; never log it

    redis_url: str = field(default="redis://redis:6379/0", repr=False)
    cache_threshold: float = 0.95   # S19 conservative small-sample calibration
    cache_ttl_seconds: int = 3600
    cache_max_entries: int = 256
    session_ttl_seconds: int = 1800
    llm_timeout_seconds: float = 60.0

    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if self.retriever not in {"stub", "chroma"}:
            raise ValueError("RETRIEVER must be stub or chroma")
        if self.llm_provider not in {"stub", "ollama-host"}:
            raise ValueError("LLM_PROVIDER must be stub or ollama-host; other modes are unsupported")
        for name, value in (("EMBED_MODEL", self.embed_model), ("LLM_MODEL", self.llm_model),
                            ("CHROMA_HOST", self.chroma_host),
                            ("CHROMA_COLLECTION", self.collection)):
            _token(name, value)
        if "://" in self.chroma_host:
            raise ValueError("CHROMA_HOST must be a hostname, not a URL")
        _positive_int("CHROMA_PORT", self.chroma_port, maximum=65535)
        _positive_int("TOP_K", self.top_k)
        _number("TEMPERATURE", self.temperature, 0.0, 2.0)
        _number("RELEVANCE_FLOOR", self.relevance_floor, -1.0, 1.0)
        _number("CACHE_THRESHOLD", self.cache_threshold, 0.0, 1.0)
        _positive_int("CACHE_TTL_SECONDS", self.cache_ttl_seconds)
        _positive_int("CACHE_MAX_ENTRIES", self.cache_max_entries)
        _positive_int("SESSION_TTL_SECONDS", self.session_ttl_seconds)
        _number("LLM_TIMEOUT_SECONDS", self.llm_timeout_seconds, 0.0)
        if self.llm_timeout_seconds == 0:
            raise ValueError("LLM_TIMEOUT_SECONDS must be positive")
        _http_base_url("OLLAMA_URL", self.ollama_url)
        if self.hosted_base_url:
            _http_base_url("HOSTED_BASE_URL", self.hosted_base_url)
        _redis_url(self.redis_url)
        if self.log_level.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL must be DEBUG, INFO, WARNING, ERROR or CRITICAL")


def get_settings() -> Settings:
    return Settings(
        retriever=os.environ.get("RETRIEVER", "stub"),
        llm_provider=os.environ.get("LLM_PROVIDER", "stub"),
        embed_model=os.environ.get("EMBED_MODEL", "nomic-embed-text"),
        chroma_host=os.environ.get("CHROMA_HOST", "chroma"),
        chroma_port=_int("CHROMA_PORT", 8000),
        collection=os.environ.get("CHROMA_COLLECTION", "rahbar"),
        top_k=_int("TOP_K", 5),
        temperature=_float("TEMPERATURE", 0.2),
        relevance_floor=_float("RELEVANCE_FLOOR", 0.74),
        llm_model=os.environ.get("LLM_MODEL", "llama3.2:3b"),
        ollama_url=os.environ.get("OLLAMA_URL", "http://host.minikube.internal:11434"),
        hosted_base_url=os.environ.get("HOSTED_BASE_URL", ""),
        llm_api_key=os.environ.get("LLM_API_KEY", ""),
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        cache_threshold=_float("CACHE_THRESHOLD", 0.95),
        cache_ttl_seconds=_int("CACHE_TTL_SECONDS", 3600),
        cache_max_entries=_int("CACHE_MAX_ENTRIES", 256),
        session_ttl_seconds=_int("SESSION_TTL_SECONDS", 1800),
        llm_timeout_seconds=_float("LLM_TIMEOUT_SECONDS", 60.0),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )
