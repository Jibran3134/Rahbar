import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_eval import citation_validity,recall_at_k,summarise  # noqa: E402


def test_unique_recall_and_no_relevance():
    a=dict(source="a",section="1")
    b=dict(source="b",section="2")
    assert recall_at_k([a,a,b],[a,a,a,b],3)==.5
    assert recall_at_k([a,a,b],[a,a,a,b],5)==1
    assert recall_at_k([],[],5) is None


def test_citation_page_integrity_and_no_vacuous_grounded_pass():
    a=dict(source="a",section="1",page=1)
    assert citation_validity(dict(answered_from_context=True,citations=[],retrieved=[]))==0
    assert citation_validity(dict(answered_from_context=False,citations=[],retrieved=[])) is None
    assert citation_validity(dict(answered_from_context=True,citations=[a],retrieved=[dict(a,page=2)]))==0
    assert citation_validity(dict(answered_from_context=True,citations=[a]*5,retrieved=[a]))==1


def test_macro_denominators_abstention_and_by_type():
    a=dict(source="a",section="1",page=1)
    rows=[dict(id="q",type="ordinary",relevant=[a],must_abstain=False,response=dict(
        retrieved=[a],citations=[a],answered_from_context=True,confidence="high")),
        dict(id="n",type="abstain",relevant=[],must_abstain=True,response=dict(
        retrieved=[],citations=[],answered_from_context=False,confidence="low"))]
    result=summarise(rows)
    assert result["recall@5"]==result["citation_validity"]==result["abstention_correctness"]==1
    assert result["denominators"]["recall"]==1
    assert result["by_type"]["ordinary"]["recall@5"]==1
