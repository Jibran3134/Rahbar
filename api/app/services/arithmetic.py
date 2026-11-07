"""Bounded literal comparisons; no policy interpretation or eligibility rules."""
import re
from decimal import Decimal

from ..schemas import Passage

MAX_QUESTION_VALUES = 3
MAX_EVIDENCE_VALUES = 8

# Deliberately limited to ordinary decimal notation, not dates, grouped amounts,
# scientific notation or dotted section paths. Do not guess ambiguous formats.
_DECIMAL=re.compile(r"(?<![\w.,])[-+]?\d{1,12}\.\d{1,6}(?!\w|\.\d|,\d)")


def _values(text: str, limit: int) -> list[str]:
    values: dict[Decimal,str]={}
    for match in _DECIMAL.finditer(text):
        literal=match.group()
        values.setdefault(Decimal(literal),literal)
        if len(values)>=limit:
            break
    return list(values.values())


def comparison_hints(question: str, passages: list[Passage]) -> str:
    """Compute only relations between literal question/evidence decimals.

    These are arithmetic aids, never cited evidence or an assertion that two
    quantities have the same unit, that a rule applies, or that a user is eligible.
    At most 3 * 8 comparisons; source metadata is never treated as a quantity.
    """
    question_values=_values(question,MAX_QUESTION_VALUES)
    if not question_values:
        return ""
    texts=[re.sub(r"^\s*"+re.escape(p.section)+r"\s+","",p.text) for p in passages]
    evidence_values=_values("\n".join(texts),MAX_EVIDENCE_VALUES)
    lines=[]
    for a in question_values:
        x=Decimal(a)
        for b in evidence_values:
            y=Decimal(b)
            relation=">" if x>y else "<" if x<y else "="
            lines.append(f"{a} {relation} {b} is true; {a} < {b} is {str(x<y).lower()}; "
                         f"{a} >= {b} is {str(x>=y).lower()}.")
    return "\n".join(lines)
