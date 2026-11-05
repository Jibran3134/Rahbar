"""Explicit S06 native Ollama audit; never collected by pytest."""
import hashlib
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.config import get_settings  # noqa: E402
from pipeline.embed import embed  # noqa: E402


def main():
    settings = replace(get_settings(), ollama_url="http://127.0.0.1:11434")
    texts = ["The course withdrawal deadline is the last day of makeup week.",
             "Students must pass the prerequisite before taking a course.",
             "The refundable admission security deposit is Rs 20,000."]
    vectors = embed(texts, settings, batch_size=2)
    repeated = embed(texts[:1], settings)
    assert len(vectors) == 3 and all(len(v) == len(vectors[0]) for v in vectors)
    assert all(abs(a-b) < 1e-5 for a, b in zip(vectors[0], repeated[0], strict=True))
    tags = httpx.get(settings.ollama_url + "/api/tags", timeout=10).json()
    report = {"passed": True, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "model": settings.embed_model, "dimension": len(vectors[0]), "vectors": len(vectors),
              "batch_size": 2, "document_prefix": "search_document: ", "truncate": False,
              "repeat_vector_max_difference": max(abs(a-b) for a,b in zip(vectors[0],repeated[0])),
              "model_inventory": tags,
              "vectors_sha256": hashlib.sha256(json.dumps(vectors).encode()).hexdigest()}
    Path("docs/evidence/app/sprints/S06-live.json").write_text(json.dumps(report, indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k != "model_inventory"}, indent=2))


if __name__ == "__main__":
    main()
