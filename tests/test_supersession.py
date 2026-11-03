"""PRD acceptance test 3: prefer the current page, refuse when it cannot be determined."""

from datetime import date

import pytest

from trailmark.supersession import Group, PageStatus, is_comment_line, page_status, pick


def status(stale=False, revision=None, when=None):
    return PageStatus(stale, "x" if stale else "", revision, when)


def group(value, *statuses, comments=False):
    return Group(value, [], list(statuses), comments)


def test_current_page_beats_withdrawn():
    winner, reason = pick([group("95", status(stale=True)), group("85", status())])
    assert winner.value == "85" and reason == "conflict_resolved_by_status"


def test_higher_revision_wins():
    winner, reason = pick([group("1", status(revision=1)), group("2", status(revision=2))])
    assert winner.value == "2" and reason == "conflict_resolved_by_revision_label"


def test_later_date_wins():
    winner, reason = pick([group("1", status(when=date(2026, 1, 1))), group("2", status(when=date(2025, 1, 1)))])
    assert winner.value == "1" and reason == "conflict_resolved_by_date_label"


def test_refuses_when_nothing_says_which_is_current():
    assert pick([group("4.2", status()), group("4.6", status())]) == (None, "conflict_not_determinable")


def test_refuses_when_labels_tie():
    assert pick([group("1", status(revision=2)), group("2", status(revision=2))])[0] is None


def test_refuses_when_only_withdrawn_pages_hold_the_value():
    assert pick([group("95", status(stale=True))]) == (None, "only_withdrawn_or_superseded_pages_hold_the_value")


def test_refuses_with_no_candidates():
    assert pick([]) == (None, "no_verified_candidate")


def test_value_in_a_comment_loses_to_the_real_one():
    winner, _ = pick([group("60", status(), comments=True), group("180", status())])
    assert winner.value == "180"


def test_comment_alone_still_stands():
    assert pick([group("60", status(), comments=True)])[0].value == "60"


@pytest.mark.parametrize(
    "ref,title,text",
    [
        ("a/datasheet_WITHDRAWN.html", "", "Body"),
        ("a/x.html", "Datasheet (withdrawn)", "Body"),
        ("a/x.html", "WITHDRAWN: Datasheet", "Body"),
        ("a/x.html", "", "WITHDRAWN. Do not use.\nBody"),
        ("a/x.html", "", "Status: Superseded\nBody"),
        ("a/x.html", "", "This datasheet has been withdrawn.\nBody"),
        ("a/x.html", "", "Superseded by revision 3.\nBody"),
    ],
)
def test_stale_markers(ref, title, text):
    assert page_status(ref, title, text).stale


@pytest.mark.parametrize(
    "title,text",
    [
        ("Datasheet revision 2", "Revision 2. Published 2026-03-02. Supersedes revision 1.\nBody"),
        ("Datasheet", "This replaces the withdrawn revision 1.\nBody"),
        ("Datasheet", "\n".join(["line"] * 20) + "\nA customer's old unit was withdrawn from service."),
        ("Deprecated APIs guide", "Body"),
        ("Datasheet", "Obsolete parts are listed below.\nBody"),
    ],
)
def test_pointing_at_or_mentioning_a_stale_page_does_not_make_this_page_stale(title, text):
    assert not page_status("a/x.html", title, text).stale


def test_revision_and_date_are_this_pages_not_the_one_it_replaces():
    found = page_status("a/x.html", "", "Revision 2. Published 2026-03-02. Supersedes revision 1 of 2025-06-10.\nBody")
    assert found.revision == 2 and found.date == date(2026, 3, 2)


def test_revision_from_a_file_name_and_letters():
    assert page_status("specs/tq40_r2.html", "", "Body").revision == 2
    assert page_status("a/x.html", "Rev. C", "Body").revision == 3


def test_comment_lines():
    assert is_comment_line("# was 60") and is_comment_line("  // was 60") and not is_comment_line("TIMEOUT = 180")
