"""PRD acceptance tests 4 and 5 through the real CLI as new processes. Stub backend throughout."""

import json
import os
import stat

import pytest

from .helpers import APP, QUESTIONS, Box


@pytest.fixture(scope="module")
def box():
    instance = Box()
    instance.copy_site()
    done = instance.index()
    assert done.returncode == 0, done.stderr
    yield instance
    instance.close()


@pytest.mark.parametrize("query", QUESTIONS, ids=[q["id"] for q in QUESTIONS])
def test_fixture_question_end_to_end_with_stub(box, query):
    done = box.ask(query["id"], query["query"])
    assert done.returncode == 0, done.stderr
    payload = box.payload(query["id"])
    if query["expected_answer"]:
        assert payload["answer"] == query["expected_answer"]
        assert sorted(payload["citations"]) == sorted(query["expected_citations"])
    else:
        assert payload == {"answer": "", "citations": [], "confidence": 0.0}


def test_acceptance_4_exact_schema_at_the_id_derived_path(box):
    box.ask("query_01", QUESTIONS[0]["query"])
    assert set(box.payload("query_01")) == {"answer", "citations", "confidence"}
    assert not list((box.dir / "output").glob(".tmp-*"))
    assert stat.S_IMODE(box.output("query_01").stat().st_mode) == 0o644


def test_output_stem_is_the_given_id_not_derived_from_the_question(box):
    box.ask("whatever-id.7", QUESTIONS[1]["query"])
    assert box.output("whatever-id.7").exists()


@pytest.mark.parametrize("bad", ["../escape", "a/b", "/etc/x", ".hidden", ""])
def test_query_id_cannot_leave_the_output_dir(box, bad):
    done = box.ask(bad, "question")
    assert done.returncode != 0
    assert not (box.dir / "escape_output.json").exists()


def test_acceptance_5_index_finishes_and_records_failures(box):
    meta = json.loads((box.dir / "index" / "meta.json").read_text())
    failures = {item["ref"]: item["kind"] for item in json.loads((box.dir / "index" / "failures.json").read_text())}
    assert meta["pages"] >= 20
    assert {"vendor/supplier-agreement.pdf", "vendor/telemetry.dat", "archive"} <= set(failures)
    if os.geteuid() != 0:
        assert failures["vendor/k7-unit-pricing.html"] == "unreadable"
    assert '"ref": "zz-late/warranty.html"' in (box.dir / "index" / "pages.jsonl").read_text()


def test_the_unreadable_value_never_reaches_any_output(box):
    question = next(q["query"] for q in QUESTIONS if q["id"] == "q09")
    box.ask("q09b", question)
    assert "6412" not in box.output("q09b").read_text()
    assert "6412" not in (box.dir / "index" / "pages.jsonl").read_text()


def test_trace_is_stamped_with_the_fake_backend(box):
    box.ask("stamp", QUESTIONS[0]["query"])
    trace = json.loads((box.dir / "run" / "traces" / "stamp.json").read_text())
    assert trace["backend"] == "fake"
    assert box.service_info()["is_stub"] is True


def test_output_never_carries_a_backend_or_trace_key(box):
    box.ask("keys", QUESTIONS[0]["query"])
    assert "backend" not in box.output("keys").read_text()


def test_query_with_no_index_refuses_cleanly():
    instance = Box()
    try:
        instance.corpus.mkdir()
        done = instance.ask("x", "anything at all")
        assert done.returncode == 0 and instance.payload("x") == {"answer": "", "citations": [], "confidence": 0.0}
    finally:
        instance.close()


def test_output_keys_and_flags_come_from_the_contract(tmp_path):
    text = (APP.parent / "contract.toml").read_text()
    text = text.replace('answer = "answer"', 'answer = "result"').replace('citations = "citations"', 'citations = "sources"').replace('query_flag = "--query"', 'query_flag = "--question"').replace('filename = "{query_id}_output.json"', 'filename = "{query_id}.json"')
    contract = tmp_path / "c.toml"
    contract.write_text(text)
    instance = Box()
    try:
        instance.corpus.mkdir()
        done = instance.cli("--corpus", str(instance.corpus), "--query-id", "x", "--question", "anything", env={"MC4_CONTRACT": str(contract)})
        assert done.returncode == 0, done.stderr
        assert json.loads((instance.dir / "output" / "x.json").read_text()) == {"result": "", "sources": [], "confidence": 0.0}
    finally:
        instance.close()


def test_start_url_opens_that_page_first_in_a_mirror(box):
    done = box.cli("--corpus", str(box.corpus), "--query-id", "start", "--query", QUESTIONS[1]["query"], "--start-url", "notes/injection.html")
    assert done.returncode == 0
    trace = json.loads((box.dir / "run" / "traces" / "start.json").read_text())
    assert trace["opened"]["P1"] == "notes/injection.html"


def test_start_url_outside_a_mirror_is_ignored_not_fetched(box):
    done = box.cli("--corpus", str(box.corpus), "--query-id", "ext", "--query", QUESTIONS[1]["query"], "--start-url", "http://169.254.169.254/latest/meta-data/")
    assert done.returncode == 0 and box.payload("ext")["answer"] == "Q3 FY27"
    trace = json.loads((box.dir / "run" / "traces" / "ext.json").read_text())
    assert not any("169.254" in ref for ref in trace["opened"].values())
