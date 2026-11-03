"""PRD acceptance tests 1 and 2."""

from types import SimpleNamespace

from trailmark.extract import sha256_text
from trailmark.verifier import MIN_QUOTE_CHARS, normalize, verify_claim, verify_quote

PAGE = "The river is 251 km long.\nIt rises in the  northern\n\thills and flows south."


def snap(text=PAGE):
    return {"https://a.example/": SimpleNamespace(text=text, sha256=sha256_text(text))}


def test_accepts_quote_present_in_snapshot():
    verdict = verify_quote("The river is 251 km long.", PAGE)
    assert verdict.verified and verdict.match == "exact"
    assert PAGE[verdict.start : verdict.end] == "The river is 251 km long."


def test_rejects_altered_quote():
    assert not verify_quote("The river is 252 km long.", PAGE).verified
    assert verify_quote("The river is 252 km long.", PAGE).reason == "quote_not_found"


def test_rejects_appended_words():
    assert not verify_quote("The river is 251 km long and wide.", PAGE).verified


def test_whitespace_normalised_match_maps_back_to_original_offsets():
    verdict = verify_quote("It rises in the northern hills and flows south.", PAGE)
    assert verdict.verified and verdict.match == "whitespace_normalized"
    assert normalize(PAGE[verdict.start : verdict.end]) == "It rises in the northern hills and flows south."


def test_zero_width_and_soft_hyphen_are_ignored_on_both_sides():
    assert verify_quote("the quick brown fox", "See the qui­ck bro​wn fox run").match == "whitespace_normalized"


def test_case_is_never_folded():
    assert not verify_quote("the river is 251 km long.", PAGE).verified


def test_short_and_empty_quotes_rejected():
    assert verify_quote("x" * (MIN_QUOTE_CHARS - 1), "x" * 50).reason == "quote_too_short"
    assert verify_quote("   ", PAGE).reason == "empty_quote"


def test_ellipsis_is_not_a_wildcard():
    assert not verify_quote("The river ... long.", PAGE).verified


def test_claim_on_page_never_fetched_fails():
    verdict = verify_claim("c", "The river is 251 km long.", "https://other.example/", snap())
    assert verdict.reason == "source_not_fetched"


def test_claim_number_absent_from_quote_fails():
    verdict = verify_claim("The river is 900 km long.", "The river is 251 km long.", "https://a.example/", snap())
    assert not verdict.verified and verdict.reason == "number_not_in_quote"


def test_claim_number_with_thousands_separator_passes():
    page = "It holds 1,200 people in total."
    verdict = verify_claim("Capacity is 1200.", "It holds 1,200 people in total.", "https://a.example/", snap(page))
    assert verdict.verified


def test_tampered_snapshot_fails_hash_check():
    pages = {"https://a.example/": SimpleNamespace(text=PAGE + " extra", sha256=sha256_text(PAGE))}
    verdict = verify_claim("c", "The river is 251 km long.", "https://a.example/", pages)
    assert verdict.reason == "snapshot_hash_mismatch"
