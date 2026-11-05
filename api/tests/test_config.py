"""S02 configuration behavior: offline parsing, limits and safe diagnostics."""

from __future__ import annotations

import socket
from dataclasses import replace

import pytest

from app.config import Settings, get_settings

KEYS = (
    "RETRIEVER LLM_PROVIDER EMBED_MODEL CHROMA_HOST CHROMA_PORT CHROMA_COLLECTION "
    "TOP_K TEMPERATURE LLM_MODEL OLLAMA_URL HOSTED_BASE_URL LLM_API_KEY LOG_LEVEL "
    "RELEVANCE_FLOOR REDIS_URL CACHE_THRESHOLD CACHE_TTL_SECONDS CACHE_MAX_ENTRIES "
    "SESSION_TTL_SECONDS LLM_TIMEOUT_SECONDS"
).split()


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults_remain_offline_and_expose_s02_settings() -> None:
    settings = get_settings()
    assert (settings.retriever, settings.llm_provider) == ("stub", "stub")
    assert settings.embed_model == "nomic-embed-text"
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.cache_ttl_seconds > 0
    assert settings.cache_max_entries > 0
    assert settings.session_ttl_seconds > 0
    assert settings.llm_timeout_seconds > 0


def test_environment_overrides_are_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    overrides = {
        "RETRIEVER": "chroma", "LLM_PROVIDER": "ollama-host",
        "EMBED_MODEL": "example-embed:v1", "OLLAMA_URL": "http://127.0.0.1:11435",
        "CHROMA_HOST": "127.0.0.1", "CHROMA_PORT": "8001", "CHROMA_COLLECTION": "test-index",
        "TOP_K": "7", "TEMPERATURE": "0.1", "RELEVANCE_FLOOR": "0.4",
        "REDIS_URL": "rediss://cache.example:6380/2", "CACHE_THRESHOLD": "0.97",
        "CACHE_TTL_SECONDS": "120", "CACHE_MAX_ENTRIES": "32",
        "SESSION_TTL_SECONDS": "600", "LLM_TIMEOUT_SECONDS": "12.5", "LOG_LEVEL": "debug",
    }
    for key, value in overrides.items():
        monkeypatch.setenv(key, value)
    settings = get_settings()
    assert settings.top_k == 7 and settings.chroma_port == 8001
    assert settings.relevance_floor == 0.4 and settings.cache_threshold == 0.97
    assert settings.cache_ttl_seconds == 120 and settings.cache_max_entries == 32
    assert settings.session_ttl_seconds == 600 and settings.llm_timeout_seconds == 12.5
    assert settings.embed_model == "example-embed:v1"
    assert settings.ollama_url == "http://127.0.0.1:11435"
    assert settings.log_level == "DEBUG"


@pytest.mark.parametrize(("key", "value"), [
    ("RETRIEVER", "other"), ("RETRIEVER", ""),
    ("LLM_PROVIDER", "other"), ("LLM_PROVIDER", ""),
    ("LLM_PROVIDER", "hosted"), ("LLM_PROVIDER", "ollama-incluster"),
    ("EMBED_MODEL", ""), ("EMBED_MODEL", "   "), ("LLM_MODEL", ""),
    ("CHROMA_HOST", ""), ("CHROMA_COLLECTION", ""),
    ("CHROMA_PORT", "0"), ("CHROMA_PORT", "65536"), ("CHROMA_PORT", "abc"),
    ("TOP_K", "0"), ("TOP_K", "-1"), ("TOP_K", "1.5"),
    ("TEMPERATURE", "-0.01"), ("TEMPERATURE", "2.01"), ("TEMPERATURE", "nan"),
    ("RELEVANCE_FLOOR", "-1.01"), ("RELEVANCE_FLOOR", "1.01"),
    ("RELEVANCE_FLOOR", "inf"), ("CACHE_THRESHOLD", "-0.01"),
    ("CACHE_THRESHOLD", "1.01"), ("CACHE_THRESHOLD", "nan"),
    ("CACHE_TTL_SECONDS", "0"), ("CACHE_MAX_ENTRIES", "-1"),
    ("SESSION_TTL_SECONDS", "0"), ("LLM_TIMEOUT_SECONDS", "0"),
    ("LLM_TIMEOUT_SECONDS", "inf"), ("LLM_TIMEOUT_SECONDS", "invalid"),
    ("OLLAMA_URL", "localhost:11434"), ("OLLAMA_URL", "ftp://localhost"),
    ("OLLAMA_URL", "http://"), ("OLLAMA_URL", "http://localhost:invalid"),
    ("OLLAMA_URL", "http://localhost:11434?model=wrong"),
    ("REDIS_URL", "http://redis:6379"), ("REDIS_URL", "redis://"),
    ("REDIS_URL", "redis://localhost:99999/0"), ("REDIS_URL", "redis://localhost/not-a-db"),
    ("LOG_LEVEL", "VERBOSE"),
])
def test_bad_environment_fails_with_configuration_key(
    monkeypatch: pytest.MonkeyPatch, key: str, value: str,
) -> None:
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match=key):
        get_settings()


def test_direct_settings_cannot_bypass_validation() -> None:
    with pytest.raises(ValueError, match="TOP_K"):
        replace(Settings(), top_k=0)


def test_boundary_values_are_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RELEVANCE_FLOOR", "-1")
    monkeypatch.setenv("CACHE_THRESHOLD", "1")
    monkeypatch.setenv("TEMPERATURE", "0")
    settings = get_settings()
    assert (settings.relevance_floor, settings.cache_threshold, settings.temperature) == (-1, 1, 0)


def test_settings_parsing_never_connects(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError("Configuration attempted a live connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)
    monkeypatch.setenv("RETRIEVER", "chroma")
    monkeypatch.setenv("LLM_PROVIDER", "ollama-host")
    assert get_settings().retriever == "chroma"


def test_credentials_stay_out_of_repr_and_bad_url_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "unit-test-key")
    monkeypatch.setenv("REDIS_URL", "redis://:unit-test-password@localhost:6379/0")
    settings = get_settings()
    assert "unit-test" not in repr(settings)
    monkeypatch.setenv("REDIS_URL", "redis://:unit-test-password@localhost:invalid/0")
    with pytest.raises(ValueError, match="REDIS_URL") as error:
        get_settings()
    assert "unit-test-password" not in str(error.value)


def test_invalid_startup_configuration_fails_before_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from app import main

    def forbidden_factory(*args: object, **kwargs: object) -> None:
        raise AssertionError("Dependencies were initialized before settings validation")

    monkeypatch.setattr(main, "get_retriever", forbidden_factory)
    monkeypatch.setattr(main, "get_provider", forbidden_factory)
    monkeypatch.setenv("RETRIEVER", "chroma")
    monkeypatch.setenv("TOP_K", "0")
    with pytest.raises(ValueError, match="TOP_K"):
        with TestClient(main.app):
            pytest.fail("Invalid application configuration became usable")
