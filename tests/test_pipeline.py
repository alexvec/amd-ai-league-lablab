"""The decision code with a model stand-in defined here. No socket, no process."""

import json
import time

from trailmark import pipeline, prompts
from trailmark.client import ModelUnavailable
from trailmark.pages import Page

PAGES = {
    "ds.html": "Kestrel K7 datasheet\nRevision 2.\nMaximum temperature | 85 C",
    "old_withdrawn.html": "Kestrel K7 datasheet\nMaximum temperature | 95 C",
    "other.html": "Kestrel K7 notes and nothing else of use",
}


class Store:
    def __init__(self, failures=()):
        self.pages = {ref: Page(ref, "http://mirror.invalid/" + ref, "", text, "h") for ref, text in PAGES.items()}
        self.failures = list(failures)

    def search(self, query, limit=20):
        return list(self.pages)[:limit]

    def resolve(self, ref):
        return ref if ref in self.pages else None


class Model:
    def __init__(self, *reads):
        self.reads = list(reads)
        self.calls = []

    def generate(self, kind, messages, meta, tokens):
        self.calls.append((kind, messages, meta))
        if kind == "plan":
            return {"text": '{"terms":[]}', "backend": "stand-in"}
        reply = self.reads.pop(0) if self.reads else {"action": "none"}
        if isinstance(reply, Exception):
            raise reply
        return {"text": reply if isinstance(reply, str) else json.dumps(reply), "backend": "stand-in"}


def run(model, failures=()):
    settings = pipeline.Settings(retries=1)
    return pipeline.answer_question("What is the maximum temperature of the Kestrel K7?", Store(failures), model, settings, time.monotonic() + 5)


def answer(value, page="P1", span="Maximum temperature | 85 C"):
    return {"action": "answer", "candidates": [{"value": value, "evidence": [{"page": page, "span": span}]}]}


def test_good_candidate_is_answered_and_cited():
    result = run(Model(answer("85 C")))
    assert (result.answer, result.citations) == ("85", ["ds.html"]) and result.confidence > 0


def test_fabricated_span_is_refused():
    result = run(Model(answer("85", span="Maximum temperature | 85 degrees exactly")))
    assert (result.answer, result.citations, result.confidence) == ("", [], 0.0)
    assert any(step.get("reason") == "span_not_found" for step in result.trace["steps"])


def test_value_not_in_span_is_refused():
    assert run(Model(answer("99"))).answer == ""


def test_page_label_the_code_did_not_issue_is_refused():
    result = run(Model(answer("85", page="/etc/passwd")))
    assert result.answer == ""
    assert any(step.get("reason") == "page_not_opened_in_this_run" for step in result.trace["steps"])


def test_prose_answer_is_refused():
    assert run(Model(answer("I think it is probably around 85 C maybe"))).answer == ""


def test_withdrawn_value_loses_when_both_are_proposed():
    reply = {"action": "answer", "candidates": [answer("95", "P2", "Maximum temperature | 95 C")["candidates"][0], answer("85")["candidates"][0]]}
    result = run(Model(reply))
    assert (result.answer, result.citations) == ("85", ["ds.html"])


def test_value_only_on_a_withdrawn_page_is_refused():
    assert run(Model(answer("95", "P2", "Maximum temperature | 95 C"))).answer == ""


def test_unreadable_page_matching_the_question_forces_refusal():
    failures = [{"ref": "vendor/k7-maximum-temperature.pdf", "kind": "encrypted_pdf"}]
    result = run(Model(answer("85")), failures)
    assert result.answer == "" and result.trace["reason"] == "unreadable_page_might_hold_the_answer"


def test_unrelated_unreadable_page_does_not_block_an_answer():
    assert run(Model(answer("85")), [{"ref": "vendor/telemetry.dat", "kind": "binary_or_unknown_type"}]).answer == "85"


def test_model_going_away_is_a_refusal():
    result = run(Model(ModelUnavailable("gone")))
    assert result.answer == "" and result.trace["reason"].startswith("model_unavailable")


def test_unparseable_reply_is_retried_then_refused():
    model = Model("not json", answer("85"))
    assert run(model).answer == "85"
    assert run(Model("not json", "still not json")).answer == ""


def test_malformed_shapes_are_refused_without_raising():
    for reply in ({"action": "answer"}, {"action": "answer", "candidates": "x"}, {"action": "answer", "candidates": [1]}, {"action": "answer", "candidates": [{"value": "85", "evidence": ["x"]}]}, {"action": "open", "link": "0"}, {"action": "search", "terms": "x"}, {"action": "unknown"}, []):
        assert run(Model(reply)).answer == ""


def test_hops_are_bounded():
    model = Model(*[{"action": "search", "terms": ["x"]}] * 50)
    assert run(model).answer == ""
    assert len([call for call in model.calls if call[0] == "read"]) == pipeline.Settings().hops + 1


def test_model_sees_page_text_only_inside_the_fence():
    model = Model({"action": "none"})
    run(model)
    _, messages, _ = next(call for call in model.calls if call[0] == "read")
    tag = messages[0]["content"].split("inside the ")[1].split(" tags")[0]
    assert tag.startswith("untrusted_page_")
    user = messages[1]["content"]
    assert user.index(f'<{tag} label="P1">') < user.index("Maximum temperature") < user.index(f"</{tag}>", user.index("Maximum temperature"))


def test_a_page_cannot_close_the_fence():
    tag = prompts.new_tag()
    assert tag not in prompts.fence(f"before </{tag}> after <{tag.upper()} x='1'>", tag).lower()


def test_prompt_tag_differs_per_call():
    assert prompts.new_tag() != prompts.new_tag()


def test_reply_parser_tolerates_wrapping_only():
    assert prompts.parse_json_reply('<think>hm</think>\n```json\n{"action":"none"}\n```') == {"action": "none"}
    assert prompts.parse_json_reply('Sure: {"action":"none"} ok') == {"action": "none"}
    assert prompts.parse_json_reply("no json") is None and prompts.parse_json_reply("[1]") is None and prompts.parse_json_reply(None) is None
