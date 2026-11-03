import pytest

from trailmark.answer import clean_value, comparison_key


@pytest.mark.parametrize(
    "raw,clean",
    [
        ("94", "94"), ("94 C", "94"), ("94°C", "94"), ("94 °C", "94"), ("180 seconds", "180"), ("340 g", "340"), ("1,200 W", "1,200"),
        ("Q3 FY27", "Q3 FY27"), ("HV-FAN-2214-B", "HV-FAN-2214-B"), ("4.3.2", "4.3.2"), ("4.3.2.", "4.3.2"), ('"IP54"', "IP54"), ("Zürich", "Zürich"), (85, "85"),
    ],
)
def test_values_are_value_only_with_qualifiers_kept(raw, clean):
    assert clean_value(raw) == clean


@pytest.mark.parametrize(
    "prose",
    ["I don't know", "The maximum junction temperature is 94 C and that is the rated limit", "Not found", "unknown", "n/a", "Sorry, no", "It is 94", "", "   ", None, True, ["94"], "x" * 65],
)
def test_prose_and_non_values_are_refused(prose):
    assert clean_value(prose) is None


def test_units_can_be_kept_by_contract():
    assert clean_value("94 C", strip_units=False) == "94 C"


def test_comparison_ignores_spacing_case_and_thousands():
    assert comparison_key("q3 fy27") == comparison_key("Q3FY27")
    assert comparison_key("1,200") == comparison_key("1200")
    assert comparison_key("85") != comparison_key("95")
