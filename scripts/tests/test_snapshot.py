import hashlib
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location("snapshot", Path(__file__).parents[1] / "fetch_snapshot.py")
assert spec and spec.loader
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


def inputs(tmp_path):
    sources = tmp_path / "sources.yaml"
    sources.write_text('documents:\n- name: Public policy\n  url: https://example.org/policy\n  doc_version: "2026"\n')
    manifest = tmp_path / "manifest.md"
    digest = hashlib.sha256(b"policy").hexdigest()
    manifest.write_text(f"| Public policy | 2026 | no | `policy.txt` | 6 | `{digest}` | <https://example.org/policy> |\n")
    return sources, manifest, tmp_path / "data"


def test_cached_snapshot_verified_without_network(tmp_path, monkeypatch):
    sources, manifest, destination = inputs(tmp_path)
    destination.mkdir()
    (destination / "policy.txt").write_bytes(b"policy")
    monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: pytest.fail("Cached verified bytes must not download"))
    snapshot.provision(sources, manifest, destination)
    entry = json.loads((destination / "_index.json").read_text())[0]
    assert entry["doc_version"] == "2026" and entry["superseded"] is False


def test_changed_remote_source_cannot_publish_index(tmp_path, monkeypatch):
    sources, manifest, destination = inputs(tmp_path)
    monkeypatch.setattr(httpx.Client, "get", lambda *a, **k: httpx.Response(
        200, content=b"changed", request=httpx.Request("GET", "https://example.org/policy")))
    with pytest.raises(ValueError, match="Source changed"):
        snapshot.provision(sources, manifest, destination)
    assert not (destination / "_index.json").exists()
    assert not (destination / "policy.txt").exists()
