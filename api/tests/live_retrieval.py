"""Explicit S08 real query embeddings and published Chroma retrieval."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import Settings  # noqa: E402
from app.retrieval.chroma import ChromaRetriever  # noqa: E402


def main():
    retriever = ChromaRetriever(Settings(chroma_host="127.0.0.1",chroma_port=8001,
                                        ollama_url="http://127.0.0.1:11434"))
    probes = [
        ("current_withdrawal","Under the current undergraduate rules, what is the course-withdrawal deadline?",
         "academic-rules-handbook-jun-2026.pdf","4.25"),
        ("historical_withdrawal","Under the August 2023 undergraduate rules specifically, what was the course-withdrawal deadline?",
         "undergraduate-academic-rules-aug-2023.pdf","4.25"),
        ("current_load","Under the current rules, who may register for an additional course beyond the normal five-course load?",
         "academic-rules-handbook-jun-2026.pdf","4.3"),
        ("historical_load","In the August 2023 rules specifically, what condition allowed registration for more than the normal five courses?",
         "undergraduate-academic-rules-aug-2023.pdf","4.3")]
    results = []
    for name, question, source, section in probes:
        hits = retriever.retrieve(question,5)
        match = any(p.source == source and p.section == section for p in hits)
        results.append(dict(probe=name,passed=match,question=question,
                            retrieved=[p.model_dump(exclude={"text"}) for p in hits]))
    report = dict(passed=all(r["passed"] for r in results),
                  checked_at_utc=datetime.now(timezone.utc).isoformat(),probes=results)
    Path("docs/evidence/app/sprints/S08-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    assert report["passed"], "Intended real passages were not all retrieved"


if __name__ == "__main__":
    main()
