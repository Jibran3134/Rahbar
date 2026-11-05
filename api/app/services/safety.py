"""Conservative quarantine for observed assistant-directed instruction blocks.

Not universal attack detection; ambiguous blocks can cause false refusals. Source
documents remain unchanged and original citation identity remains authoritative.
"""
import re

from ..schemas import Passage

_OVERRIDE=re.compile(r"(?:ignore|disregard).{0,80}(?:previous|earlier|system).{0,40}instructions|"
                     r"(?:reveal|print|output|disclose).{0,40}(?:system prompt|hidden prompt|secret)|"
                     r"^\s*(?:system|assistant)\s*:",re.I)


def quarantine(question: str,passages: list[Passage]) -> tuple[str,list[Passage],int]:
    removed=0
    kept_questions=[]
    for sentence in re.split(r"(?<=[.!?])\s+|\n+",question):
        if _OVERRIDE.search(" ".join(sentence.split())):
            removed+=1
        else:
            kept_questions.append(sentence)
    kept=[]
    for passage in passages:
        blocks=[]
        for block in re.split(r"\n\s*\n",passage.text):
            if _OVERRIDE.search(" ".join(block.split())):
                removed+=1
            elif block.strip():
                blocks.append(block)
        if blocks:
            kept.append(passage.model_copy(update={"text":"\n\n".join(blocks)}))
    return " ".join(kept_questions).strip(),kept,removed
