"""Explicit S07: real vectors, two publications, injected partial failed build."""
import hashlib
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.config import get_settings  # noqa: E402
from pipeline.embed import embed  # noqa: E402
from pipeline.models import Chunk  # noqa: E402
from pipeline.store import get_client, store  # noqa: E402


def main():
    settings = replace(get_settings(), chroma_host="127.0.0.1", chroma_port=8001,
                       ollama_url="http://127.0.0.1:11434")
    path = Path("corpus/raw/_s05-chunks/chunks-400-50.jsonl")
    chunks = [Chunk(**json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines()]
    cache = Path("corpus/raw/_s07-vectors.json")
    text_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    saved = json.loads(cache.read_text()) if cache.exists() else {}
    if saved.get("chunks_sha256") == text_hash and saved.get("model") == settings.embed_model:
        vectors = saved["vectors"]
    else:
        vectors = embed([c.text for c in chunks], settings)
        cache.write_text(json.dumps({"chunks_sha256":text_hash,"model":settings.embed_model,
                                     "vectors":vectors}),encoding="utf-8")
    client = get_client(settings)
    first_count = store(chunks[:3], vectors[:3], settings, client=client)
    first = dict(client.get_collection("rahbar_active").metadata)
    second_count = store(chunks, vectors, settings, client=client)
    second = dict(client.get_collection("rahbar_active").metadata)
    assert first != second and client.get_collection(first["collection"]).count() == first_count

    class BrokenClient:
        def __getattr__(self, name):
            return getattr(client, name)
        def create_collection(self, **kwargs):
            collection = client.create_collection(**kwargs)
            if "__g_" in kwargs["name"]:
                class BrokenCollection:
                    def __getattr__(self, name):
                        return getattr(collection,name)
                    def add(self, **batch):
                        collection.add(**{key:value[:1] for key,value in batch.items()})
                        raise RuntimeError("deliberate S07 partial write failure")
                return BrokenCollection()
            return collection
    try:
        store(chunks[:3],vectors[:3],settings,client=BrokenClient())
    except RuntimeError as exc:
        assert "deliberate S07" in str(exc)
    else:
        raise AssertionError("Failed build unexpectedly succeeded")
    after = dict(client.get_collection("rahbar_active").metadata)
    assert after == second
    query = client.get_collection(second["collection"]).query(
        query_embeddings=[vectors[0]], n_results=1, include=["documents"])
    assert query["ids"][0][0] == chunks[0].id
    report = {"passed":True,"checked_at_utc":datetime.now(timezone.utc).isoformat(),
              "first":first,"second":second,"first_count":first_count,"second_count":second_count,
              "failed_build_preserved_active":after == second,"old_generation_retained":True,
              "query_after_failed_build":query["ids"],"dimension":len(vectors[0]),
              "chunks_sha256":text_hash,"endpoint":"127.0.0.1:8001"}
    Path("docs/evidence/app/sprints/S07-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
