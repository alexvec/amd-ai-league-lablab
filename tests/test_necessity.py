"""PRD acceptance test 2: citations are a necessity set, not the retrieval list."""

from trailmark.necessity import EvidenceSpan as S
from trailmark.necessity import necessary_pages


def test_page_that_only_repeats_the_value_is_dropped():
    spans = [S("datasheet", "Maximum operating temperature | 85 C", 121), S("overview", "rated for a maximum of 85 C", 101)]
    assert necessary_pages(spans, "85", "What is the maximum operating temperature?") == ["datasheet"]


def test_lowest_authority_goes_first_whatever_the_order():
    spans = [S("overview", "rated for a maximum of 85 C", 101), S("datasheet", "Maximum | 85 C", 121)]
    assert necessary_pages(spans, "85", "max?") == ["datasheet"]


def test_both_pages_of_a_two_hop_chain_are_kept():
    spans = [S("incident", "Defect tracked as ticket HV-3310.", 100), S("tickets", "HV-3310 | Build 5.2.1", 110)]
    assert necessary_pages(spans, "5.2.1", "Which build fixed the September incident?") == ["incident", "tickets"]


def test_a_three_hop_chain_survives_whole():
    spans = [S("a", "Incident links to ticket HV-1.", 100), S("b", "HV-1 was traced to change CH-9.", 100), S("c", "CH-9 shipped in 7.1.0", 100)]
    assert necessary_pages(spans, "7.1.0", "Which release fixed the incident?") == ["a", "b", "c"]


def test_first_hop_is_not_needed_when_the_question_names_the_identifier():
    spans = [S("incident", "Defect tracked as ticket HV-3310.", 100), S("tickets", "HV-3310 | Build 5.2.1", 110)]
    assert necessary_pages(spans, "5.2.1", "Which build fixed ticket HV-3310?") == ["tickets"]


def test_navigation_page_with_no_link_is_dropped():
    spans = [S("listing", "Kestrel K7 | see details", 100), S("detail", "Kestrel K7 warranty period: 36 months", 110)]
    assert necessary_pages(spans, "36", "How long is the Kestrel K7 warranty?") == ["detail"]


def test_two_pages_repeating_a_value_and_an_id_do_not_count_as_a_chain():
    spans = [S("a", "HV-K7 maximum 85", 120), S("b", "HV-K7 maximum 85", 100)]
    assert necessary_pages(spans, "85", "max of the current model?") == ["a"]


def test_two_spans_on_one_page_is_one_citation():
    spans = [S("p", "Ticket HV-1 opened.", 100), S("p", "HV-1 closed in 2.0.1", 100)]
    assert necessary_pages(spans, "2.0.1", "which build?") == ["p"]


def test_no_span_holding_the_value_gives_no_citations():
    assert necessary_pages([S("p", "Nothing relevant here", 100)], "85", "q?") == []
