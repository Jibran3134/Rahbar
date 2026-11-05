"""S02 indexer configuration validation; no live services or documents."""

from __future__ import annotations

import socket
from dataclasses import replace

import pytest

from pipeline.config import get_settings

KEYS = (
    "EMBED_MODEL CHROMA_HOST CHROMA_PORT CHROMA_COLLECTION CORPUS_DIR "
    "CHUNK_SIZE CHUNK_OVERLAP OLLAMA_URL"
).split()


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


def test_indexer_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "EMBED_MODEL": "example-embed:v1", "OLLAMA_URL": "http://127.0.0.1:11435",
        "CHROMA_HOST": "127.0.0.1", "CHROMA_PORT": "8001", "CHROMA_COLLECTION": "test-index",
        "CORPUS_DIR": "C:/data/corpus", "CHUNK_SIZE": "250", "CHUNK_OVERLAP": "30",
    }.items():
        monkeypatch.setenv(key, value)
    settings = get_settings()
    assert settings.embed_model == "example-embed:v1"
    assert settings.ollama_url == "http://127.0.0.1:11435"
    assert settings.chroma_port == 8001
    assert (settings.chunk_size, settings.chunk_overlap) == (250, 30)
    assert settings.corpus_dir == "C:/data/corpus"


@pytest.mark.parametrize(("key", "value"), [
    ("CHUNK_SIZE", "0"), ("CHUNK_SIZE", "-1"), ("CHUNK_SIZE", "abc"),
    ("CHUNK_OVERLAP", "-1"), ("CHUNK_OVERLAP", "400"), ("CHUNK_OVERLAP", "401"),
    ("CHROMA_PORT", "0"), ("CHROMA_PORT", "65536"),
    ("EMBED_MODEL", ""), ("CHROMA_HOST", ""), ("CHROMA_COLLECTION", ""),
    ("CORPUS_DIR", ""), ("OLLAMA_URL", "localhost:11434"),
    ("OLLAMA_URL", "http://localhost:invalid"), ("OLLAMA_URL", "http://localhost#fragment"),
])
def test_invalid_indexer_settings_fail_clearly(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str,
) -> None:
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match=key):
        get_settings()


def test_direct_indexer_construction_validates_overlap() -> None:
    with pytest.raises(ValueError, match="CHUNK_OVERLAP"):
        replace(get_settings(), chunk_overlap=400)


def test_zero_overlap_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHUNK_OVERLAP", "0")
    assert get_settings().chunk_overlap == 0


def test_indexer_configuration_never_connects(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("Configuration attempted a live connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)
    assert get_settings().embed_model == "nomic-embed-text"
