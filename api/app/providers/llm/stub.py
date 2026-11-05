"""A provider with no model and no network.

Use it for every unit test and for CI (section 6): your tests must never call a
real model. It is deterministic: the same input always gives the same output.
"""

from __future__ import annotations

import re

from ...schemas import Answer, Citation, Passage


class StubProvider:
    name = "stub"

    def generate(self, question: str, passages: list[Passage], *, feedback: str | None = None) -> Answer:
        if not passages:
            return Answer(
                reasoning="stub: nothing was retrieved",
                answer="(stub) No passages were retrieved for this question.",
                citations=[],
                answered_from_context=False,
                confidence="low",
            )
        top = passages[0]
        body = next((block.strip() for block in re.split(r"\n\s*\n",top.text)
                     if block.strip() and not block.lstrip().startswith("#")),top.text)
        sentences = re.split(r"(?<=[.!?])\s+", " ".join(body.split()))
        claims = [sentence for sentence in sentences if re.search(r"[A-Za-z]",sentence)][:4]
        return Answer(
            reasoning="stub: cites the first retrieved passage",
            answer="(stub) "+" ".join(f"{claim} [{top.source} / {top.section}]" for claim in claims),
            citations=[Citation(source=top.source, section=top.section, page=top.page)],
            answered_from_context=True,
            confidence="low",
        )
