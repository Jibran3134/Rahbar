"""Stub must quote sufficient retrieved content, without memorized golden truth."""
from app.providers.llm.stub import StubProvider
from app.schemas import Passage
from app.services.grounding import validate_grounding


def test_repeat_policy_second_sentence_and_poison_are_handled_as_data():
    text="## 3. Repeating a course\n\n3.1 A course may be repeated. Only the most recent attempt counts."
    p=Passage(chunk_id="a",source="owned.md",section="3. Repeating a course",page=1,text=text,score=.9)
    answer=StubProvider().generate("Which attempt counts?",[p])
    assert "most recent" in answer.answer
    validate_grounding(answer,[p])
