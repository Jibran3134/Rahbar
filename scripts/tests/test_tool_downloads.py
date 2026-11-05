import hashlib
import importlib.util
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location("tool_bootstrap", Path(__file__).parents[1] / "bootstrap_tools.py")
assert spec and spec.loader
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)
DATA = b"verified official executable"
SPEC = dict(url="https://example.org/release", sha256=hashlib.sha256(DATA).hexdigest())


@pytest.mark.parametrize("failure", [504, "transport"])
def test_transient_download_retry_keeps_checksum_validation(monkeypatch, failure):
    calls = []
    sleeps = []
    def download(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            if failure == "transport":
                raise httpx.ReadError("Interrupted release transfer")
            return httpx.Response(failure, request=httpx.Request("GET", SPEC["url"]))
        return httpx.Response(200, content=DATA, request=httpx.Request("GET", SPEC["url"]))
    monkeypatch.setattr(bootstrap.httpx, "get", download)
    monkeypatch.setattr(bootstrap.time, "sleep", sleeps.append)
    assert bootstrap.verified(SPEC) == DATA
    assert len(calls) == 2 and sleeps == [2]


def test_checksum_mismatch_is_never_retried(monkeypatch):
    calls = []
    def download(*args, **kwargs):
        calls.append(1)
        return httpx.Response(200, content=b"tampered", request=httpx.Request("GET", SPEC["url"]))
    monkeypatch.setattr(bootstrap.httpx, "get", download)
    monkeypatch.setattr(bootstrap.time, "sleep", lambda _: pytest.fail("Do not retry untrusted bytes"))
    with pytest.raises(ValueError, match="checksum mismatch"):
        bootstrap.verified(SPEC)
    assert len(calls) == 1


def test_download_retry_budget_is_bounded(monkeypatch):
    calls = []
    def download(*args, **kwargs):
        calls.append(1)
        return httpx.Response(504, request=httpx.Request("GET", SPEC["url"]))
    monkeypatch.setattr(bootstrap.httpx, "get", download)
    monkeypatch.setattr(bootstrap.time, "sleep", lambda _: None)
    with pytest.raises(httpx.HTTPStatusError):
        bootstrap.verified(SPEC)
    assert len(calls) == 4
