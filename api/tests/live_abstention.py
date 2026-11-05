"""S09 real score separation and no-generation decision, not final calibration."""
import json
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import Settings  # noqa: E402
from app.providers.llm.stub import StubProvider  # noqa: E402
from app.retrieval.chroma import ChromaRetriever  # noqa: E402
from app.services.answer import answer_question  # noqa: E402


def main():
    settings = Settings(chroma_host="127.0.0.1",chroma_port=8001,ollama_url="http://127.0.0.1:11434")
    questions = [
        ("answerable","Under the current undergraduate rules, what is the course-withdrawal deadline?"),
        ("absent_deadline","What is the hostel-room allotment application deadline for the Peshawar campus?"),
        ("absent_deposit","How much is the refundable hostel-room security deposit at the Chiniot-Faisalabad campus?")]
    retriever = ChromaRetriever(settings)
    scores = {name:retriever.retrieve(question,5) for name,question in questions}
    maximum = {name:max((p.score for p in hits),default=-1) for name,hits in scores.items()}
    absent_max = max(maximum["absent_deadline"],maximum["absent_deposit"])
    floor = (maximum["answerable"] + absent_max)/2
    separated = absent_max < maximum["answerable"]
    # A selected-pair provisional runtime profile; do not change the code default
    # or claim general calibration from these three probes.
    class CountingProvider(StubProvider):
        def __init__(self):
            self.calls = 0
        def generate(self, question, passages):
            self.calls += 1
            return super().generate(question,passages)
    provider = CountingProvider()
    results = []
    class SavedRetrieval:
        name = "real-captured"
        def retrieve(self, question, k):
            return next(scores[name] for name,q in questions if q == question)
    for name,question in questions:
        before = provider.calls
        result = answer_question(question,SavedRetrieval(),provider,replace(settings,relevance_floor=floor))
        results.append(dict(probe=name,max_similarity=maximum[name],
                            generator_calls=provider.calls-before,
                            answered_from_context=result.answered_from_context,citations=len(result.citations)))
    passed = separated and results[0]["generator_calls"] == 1 and all(
        r["generator_calls"] == 0 and not r["answered_from_context"] and not r["citations"]
        for r in results[1:])
    report = dict(passed=passed,checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  configured_default=settings.relevance_floor,provisional_live_floor=floor,
                  selected_score_separation=separated,probes=results,
                  scope="Real captured retrieval; counting stub tests gate only, not real answer correctness")
    Path("docs/evidence/app/sprints/S09-live.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    assert passed, "Selected real absent/answerable scores did not separate"


if __name__ == "__main__":
    main()
