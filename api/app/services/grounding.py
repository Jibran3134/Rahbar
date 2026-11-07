"""Bounded citation/claim-format validation, not semantic entailment proof."""
import re

from pydantic import ValidationError

from ..providers.llm.base import ProviderError, ProviderFailureKind
from ..schemas import Answer, Passage
from .relevance import abstention

_TAG = re.compile(r"\[([^\[\]\r\n]+?) / ([^\[\]\r\n]+?)\]")
_MARKER = "\ufff0"


def validate_grounding(answer: Answer, passages: list[Passage], *, question: str | None = None) -> Answer:
    """Accept only request-local citation triples and cited prose sentences.

    False-groundedness output is canonicalized to a refusal, preventing uncited
    provider claims from escaping disguised as an abstention. Every prose line
    is conservatively treated as claim-bearing; headers may require a retry.
    """
    if not isinstance(answer, Answer):
        raise ProviderError(ProviderFailureKind.INVALID_SCHEMA)
    try:
        answer = Answer.model_validate(answer.model_dump(), strict=True)
    except ValidationError:
        raise ProviderError(ProviderFailureKind.INVALID_SCHEMA) from None

    def invalid() -> None:
        raise ProviderError(ProviderFailureKind.INVALID_CITATION)

    if not answer.answer.strip() or any(c in answer.answer for c in ("\ufff0","\ufff2")):
        invalid()
    if not answer.answered_from_context:
        if answer.citations:
            raise ProviderError(ProviderFailureKind.INCONSISTENT_ANSWER)
        if (answer.confidence != "low" or "[" in answer.answer
                or not re.search(r"cannot determine|unable to answer|(?:do|does) not provide|"
                                 r"not enough information|insufficient (?:evidence|information)|"
                                 r"not (?:available|specified|provided)", answer.answer, re.I)):
            invalid()
        return abstention().model_copy(update={"reasoning":"Provider reported insufficient evidence."})
    # A supported conditional may explain that personal records are unavailable.
    # Reject a leading global refusal, rather than rejecting that phrase anywhere
    # in otherwise cited prose. This remains a format check, not entailment proof.
    if re.match(r"\s*(?:(?:the )?supplied documents do not provide|"
                r"(?:I (?:am )?)?(?:cannot determine|unable to answer))",answer.answer,re.I):
        raise ProviderError(ProviderFailureKind.INCONSISTENT_ANSWER)
    if question and answer.answered_from_context:
        for facility in ("hostel", "transport", "cafeteria"):
            if facility in question.lower():
                cited_passages = [
                    p for p in passages
                    if any((p.source == c.source and p.section == c.section) for c in answer.citations)
                ]
                if not any(facility in (p.text or "").lower() or facility in (p.section or "").lower() for p in cited_passages):
                    raise ProviderError(ProviderFailureKind.INCONSISTENT_ANSWER)
    available = {(p.source,p.section,p.page) for p in passages}
    cited = [(c.source,c.section,c.page) for c in answer.citations]
    if not available or not cited or len(set(cited)) != len(cited) or any(c not in available for c in cited):
        invalid()
    tags = list(_TAG.finditer(answer.answer))
    pairs = {(m.group(1),m.group(2)) for m in tags}
    if pairs != {(c.source,c.section) for c in answer.citations}:
        invalid()
    masked = _TAG.sub(_MARKER,answer.answer)
    if "[" in masked or "]" in masked:
        invalid()
    # Accept either "claim [tag]." or "claim. [tag]" by moving the
    # latter tag ahead of punctuation before sentence-boundary detection.
    masked = re.sub(r"([.!?])\s*(\ufff0(?:\s*\ufff0)*)", r" \2\1", masked)
    masked = re.sub(r"\b(?:Rs|Dr|Mr|Ms|Prof)\.",lambda m:m.group()[:-1] + "\ufff2",masked)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+",masked) if s.strip()]
    if not sentences or not any(re.search(r"[A-Za-z0-9]",s.replace(_MARKER,"")) for s in sentences):
        invalid()
    if any(not re.search(r"\ufff0(?:\s*\ufff0)*\s*[.!?]?$",sentence) for sentence in sentences):
        invalid()
    return answer
