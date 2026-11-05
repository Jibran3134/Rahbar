"""Unsupported evidence must never reach the generation provider."""
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.schemas import Answer, Passage
from app.services.answer import answer_question


def hit(score):
    return Passage(chunk_id="one",text="A policy rule.",source="a.pdf",section="1.1",page=1,score=score)


@pytest.mark.parametrize("passages", [[],[hit(.44)],[hit(float("nan"))],[hit(2)],
    [hit(.9).model_copy(update={"source":""})], [hit(.9).model_copy(update={"page":0})]])
def test_no_usable_evidence_abstains_without_generation(passages):
    def forbidden(*args):
        raise AssertionError("Provider must not run")
    result = answer_question("Question",SimpleNamespace(name="fake",retrieve=lambda q,k:passages),
                             SimpleNamespace(name="spy",generate=forbidden),Settings())
    assert not result.answered_from_context and result.citations == [] and result.confidence == "low"
    assert result.retrieved == []


@pytest.mark.parametrize("score", [.45,.46])
def test_floor_is_inclusive_and_valid_top_k_context_is_preserved(score):
    seen = []
    def generate(question, passages):
        seen.extend(passages)
        return Answer(reasoning="private",answer="Cannot determine.",citations=[],
                      answered_from_context=False,confidence="low")
    result = answer_question("Question", SimpleNamespace(name="fake",retrieve=lambda q,k:[hit(.4),hit(score)]),
                             SimpleNamespace(name="spy",generate=generate), Settings(relevance_floor=.45))
    assert len(seen) == 2 and seen[-1].score == score and len(result.retrieved) == 2
