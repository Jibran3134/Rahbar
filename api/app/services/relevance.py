"""Conservative integrity and provisional similarity threshold gate."""
import math
from pathlib import Path

from ..schemas import Answer, Passage


def usable_passages(passages: list[Passage], floor: float) -> list[Passage]:
    valid = []
    for passage in passages:
        html = Path(passage.source).suffix.lower() in {".html",".htm"}
        if (all(isinstance(s,str) and s.strip() for s in (
                passage.chunk_id,passage.text,passage.source,passage.section))
                and type(passage.score) in (int,float) and math.isfinite(passage.score)
                and -1 <= passage.score <= 1 and passage.score >= floor
                and ((html and passage.page is None) or (not html and type(passage.page) is int
                                                        and passage.page > 0))):
            valid.append(passage)
    return valid


def abstention() -> Answer:
    return Answer(reasoning="No usable retrieved evidence cleared the configured relevance floor.",
                  answer="The supplied documents do not provide enough information to answer this question.",
                  citations=[],answered_from_context=False,confidence="low")
