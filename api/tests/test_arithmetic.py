"""Literal arithmetic assistance must not invent policy applicability."""
import pytest

from app.schemas import Passage


def evidence(text="5.4 Minimum required value is 2.00."):
    return [Passage(chunk_id="a",source="p.pdf",section="5.4",page=1,text=text,score=.8)]


@pytest.mark.parametrize("value,relation", [("3.6",">"),("1.6","<"),("2.00","="),
                                            ("-1.6","<"),("+3.6",">")])
def test_actual_decimal_order_and_equality(value,relation):
    from app.services.arithmetic import comparison_hints
    hints=comparison_hints(f"My value is {value}.",evidence())
    assert f"{value} {relation} 2.00 is true" in hints
    assert "5.4" not in hints  # Section labels are not measured quantities.
    assert "academic warning" not in hints and "eligible" not in hints


def test_high_precision_decimal_comparison_does_not_round_through_float():
    from app.services.arithmetic import comparison_hints
    hints=comparison_hints("My value is 999999999999.000001.",evidence("Value is 999999999999.000002."))
    assert "999999999999.000001 < 999999999999.000002 is true" in hints


@pytest.mark.parametrize("question", ["What is the policy?", "The 2026 rules?",
                                     "Value 1,000.00?", "Value 1.2.3?", "Value 1.2345678?"])
def test_absent_or_ambiguous_decimal_notation_produces_no_hint(question):
    from app.services.arithmetic import comparison_hints
    assert comparison_hints(question,evidence())==""


def test_duplicate_quantities_and_work_are_bounded():
    from app.services.arithmetic import comparison_hints
    question="Values "+" ".join(f"{i}.0" for i in range(20))
    hints=comparison_hints(question,evidence("Values "+" ".join(f"{i}.00" for i in range(30))))
    assert len(hints.splitlines())<=24
    assert len(hints)<3000
