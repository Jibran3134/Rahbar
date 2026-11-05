"""Explicit S10 real generation with an inspected original clause."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings  # noqa: E402
from app.providers.llm.ollama import OllamaProvider  # noqa: E402
from app.schemas import Passage  # noqa: E402


def main():
    records = [json.loads(line) for line in Path(
        "corpus/raw/_s05-chunks/chunks-400-50.jsonl").read_text(encoding="utf-8").splitlines()]
    c = next(c for c in records if c["source"] == "academic-rules-handbook-jun-2026.pdf"
             and c["section"] == "4.25" and c["page"] == 23)
    passage = Passage(chunk_id=c["id"], text=c["text"], source=c["source"], section=c["section"],
                      page=c["page"], score=.9)
    settings = Settings(ollama_url="http://127.0.0.1:11434",
                        llm_model=os.environ.get("LLM_MODEL", "llama3.2:3b"))
    result = OllamaProvider(settings).generate(
        "Under the current undergraduate rules, what is the course-withdrawal deadline?", [passage])
    passed = result.answered_from_context and "makeup" in result.answer.lower()
    passed = bool(passed and result.citations and all((c.source,c.section,c.page) == (
        passage.source,passage.section,passage.page) for c in result.citations))
    report = {"passed": passed, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "model": settings.llm_model, "answer": result.model_dump(exclude={"reasoning"}),
              "source_chunk_id": passage.chunk_id, "scope": "Real constrained provider; S11 validation separate"}
    Path("docs/evidence/app/sprints/S10-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    assert passed, "Real provider source check failed; inspect saved answer"


if __name__ == "__main__":
    main()
