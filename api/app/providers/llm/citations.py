"""Render supplied citation objects consistently across generation transports."""

import re

from ...schemas import Answer, Passage


def normalize_inline_citations(answer: Answer, passages: list[Passage]) -> Answer:
    """Preserve the existing prefix and verified single-source rendering rules."""
    for p in passages:
        label = f"[{p.source} / {p.section}]"
        if answer.answer.startswith(label + " "):
            answer = answer.model_copy(
                update={"answer": answer.answer[len(label) :].strip() + " " + label}
            )
            break
    triples = {(p.source, p.section, p.page) for p in passages}
    cited = {(c.source, c.section, c.page) for c in answer.citations}
    pairs = {(c.source, c.section) for c in answer.citations}
    if (
        answer.answered_from_context
        and cited
        and cited <= triples
        and len(pairs) == 1
        and "[" not in answer.answer
        and "]" not in answer.answer
    ):
        source, section = next(iter(pairs))
        label = f"[{source} / {section}]"
        protected = re.sub(
            r"\b(?:Rs|Dr|Mr|Ms|Prof)\.", lambda m: m.group()[:-1] + "\ufff2", answer.answer
        )
        sentences = [
            s.strip().replace("\ufff2", ".")
            for s in re.split(r"(?<=[.!?])\s+|\n+", protected)
            if s.strip()
        ]
        answer = answer.model_copy(update={"answer": " ".join(s + " " + label for s in sentences)})
    return answer
