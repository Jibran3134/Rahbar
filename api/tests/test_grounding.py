"""Grounding format/integrity tests do not claim semantic entailment."""
import pytest

from app.providers.llm.base import ProviderError
from app.schemas import Answer, Citation, Passage


def passages():
    return [Passage(chunk_id="a",text="Deadline is makeup week.",source="policy.pdf",
                    section="4.25",page=23,score=.9)]


def valid():
    return Answer(reasoning="private reasoning",answer="Deadline is makeup week [policy.pdf / 4.25].",
        citations=[Citation(source="policy.pdf",section="4.25",page=23)],
        answered_from_context=True,confidence="high")


@pytest.mark.parametrize("change", ["source","section","page","no_citations","no_inline",
    "number_inline","uncited_sentence","unused_object","duplicate","false_with_citations",
    "false_high","empty_answer"])
def test_reject_fabrication_missing_claim_citations_and_contradictions(change):
    from app.services.grounding import validate_grounding
    answer = valid()
    if change in {"source","section","page"}:
        setattr(answer.citations[0],change,{"source":"invented.pdf","section":"9.9","page":99}[change])
    if change == "no_citations":
        answer.citations = []
    if change == "no_inline":
        answer.answer = "Deadline is makeup week."
    if change == "number_inline":
        answer.answer = "Deadline is makeup week.[1/4.25]"
    if change == "uncited_sentence":
        answer.answer = "Fees are waived. Deadline is makeup week [policy.pdf / 4.25]."
    if change == "unused_object":
        answer.citations.append(Citation(source="another.pdf",section="2",page=1))
    if change == "duplicate":
        answer.citations *= 2
    if change == "false_with_citations":
        answer.answered_from_context = False
    if change == "false_high":
        answer = Answer(reasoning="x",answer="Cannot determine.",citations=[],
                        answered_from_context=False,confidence="high")
    if change == "empty_answer":
        answer.answer = ""
    with pytest.raises(ProviderError):
        validate_grounding(answer,passages())


@pytest.mark.parametrize("text", ["Deadline is makeup week [policy.pdf / 4.25].",
    "Deadline is makeup week. [policy.pdf / 4.25]",
    "Deadline is makeup week [policy.pdf / 4.25]. Fees are Rs. 2.00 [policy.pdf / 4.25]."])
def test_valid_citation_forms_and_decimals(text):
    from app.services.grounding import validate_grounding
    answer = valid()
    answer.answer = text
    assert validate_grounding(answer,passages()).answer == text


def test_abstention_is_canonicalized_and_html_requires_null_page():
    from app.services.grounding import validate_grounding
    answer = Answer(reasoning="private",answer="Cannot determine from evidence.",citations=[],
                    answered_from_context=False,confidence="low")
    assert not validate_grounding(answer,passages()).answered_from_context
    p = Passage(chunk_id="html",text="Fee.",source="fee.html",section="Fees",page=None,score=.9)
    answer = Answer(reasoning="x",answer="Fee is Rs. 12,000 [fee.html / Fees].",
                    citations=[Citation(source="fee.html",section="Fees",page=None)],
                    answered_from_context=True,confidence="high")
    assert validate_grounding(answer,[p]).citations[0].page is None
    answer.citations[0].page = 1
    with pytest.raises(ProviderError):
        validate_grounding(answer,[p])


def test_false_groundedness_cannot_leak_extra_factual_claims():
    from app.services.grounding import validate_grounding
    answer = Answer(reasoning="private",answer="Cannot determine. All fees are waived.",
                    citations=[],answered_from_context=False,confidence="low")
    result = validate_grounding(answer,passages())
    assert "waived" not in result.answer and not result.citations


def test_unused_valid_object_empty_evidence_and_forged_marker_are_rejected():
    from app.services.grounding import validate_grounding
    with pytest.raises(ProviderError):
        validate_grounding(valid(),[])
    extra = Passage(chunk_id="b",text="Second rule.",source="b.pdf",section="2",page=1,score=.8)
    answer = valid()
    answer.citations.append(Citation(source="b.pdf",section="2",page=1))
    with pytest.raises(ProviderError):
        validate_grounding(answer,passages()+[extra])
    answer = valid()
    answer.answer = "Uncited fact \ufff0. " + answer.answer
    with pytest.raises(ProviderError):
        validate_grounding(answer,passages())


def test_numeric_fact_with_valid_citation_is_a_claim():
    from app.services.grounding import validate_grounding
    answer=valid()
    answer.answer="100% [policy.pdf / 4.25]"
    assert validate_grounding(answer,passages()).answered_from_context


def test_supported_conditional_can_explain_missing_personal_records():
    from app.services.grounding import validate_grounding
    answer=valid()
    answer.answer=("If this is your cumulative value, it exceeds the documented minimum "
                   "[policy.pdf / 4.25]. Semester results alone cannot determine your cumulative "
                   "standing [policy.pdf / 4.25].")
    assert validate_grounding(answer,passages()).answered_from_context


@pytest.mark.parametrize("text,grounded", [
    ("The supplied documents do not provide that information [policy.pdf / 4.25].", True),
    ("I cannot determine the answer [policy.pdf / 4.25].", True),
    ("The documented deadline is makeup week [policy.pdf / 4.25].", False),
])
def test_contradictory_groundedness_has_specific_safe_failure(text,grounded):
    from app.services.grounding import validate_grounding
    answer=valid().model_copy(update={"answer":text,"answered_from_context":grounded})
    with pytest.raises(ProviderError) as error:
        validate_grounding(answer,passages())
    assert error.value.kind.value=="inconsistent_answer"
