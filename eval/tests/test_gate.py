import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_eval import gate  # noqa: E402


def metrics():
    return {"dataset_id":"real","recall@5":.85,"citation_validity":.95,"abstention_correctness":1.0}


def test_gate_exact_boundaries_wrong_and_missing_baseline():
    baseline={**metrics(),"recall@5":.9}
    assert gate(metrics(),baseline)==[]
    assert gate({**metrics(),"recall@5":.849},baseline)
    assert gate(metrics(),None)
    assert gate(metrics(),{**baseline,"dataset_id":"fixture"})


@pytest.mark.parametrize("key,value",[("citation_validity",.949),("abstention_correctness",.5),
    ("recall@5",float("nan")),("citation_validity",None),("recall@5",float("inf"))])
def test_absolute_nonfinite_and_undefined_metrics_fail_closed(key,value):
    assert gate({**metrics(),key:value},metrics())
