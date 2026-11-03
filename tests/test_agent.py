"""Core path with the real extractive backend, on a fake web."""

import json

import pytest

from trailmark import agent
from trailmark.config import Limits
from trailmark.extractive import ExtractiveBackend
from trailmark.netguard import BlockedURL

HOME = """<html><title>Rivers of Example</title><body><nav><a href="/lengths">River lengths</a><a href="/about">About us</a></nav>
<p>Welcome to the gazetteer. It lists waterways.</p></body></html>"""
LENGTHS = """<html><title>River lengths</title><body><p>The Alder river is 251 km long and rises in the northern hills.</p>
<p>Fishing permits are sold locally.</p></body></html>"""


def run(web, question="How long is the Alder river?", start="https://site.example/", **kwargs):
    return agent.run(question, start, ExtractiveBackend(), Limits(), fetcher_factory=web.factory, **kwargs)


@pytest.fixture
def site(web):
    web.add("https://site.example/", HOME)
    web.add("https://site.example/lengths", LENGTHS)
    web.add("https://site.example/about", "<p>About.</p>")
    return web


def test_navigates_by_link_and_returns_verified_quote(site):
    result = run(site)
    assert result["status"] == "answered"
    assert "251 km" in result["answer"]
    assert result["sources"] == ["https://site.example/lengths"]
    claim = result["claims"][0]
    assert claim["verified"] and claim["match"] == "exact"
    stored = result["snapshots"][0]["text"]
    assert stored[claim["start"] : claim["end"]] == claim["quote"]
    assert any(step["type"] == "follow_link" for step in result["trace"]["steps"])


def test_trace_labels_backend_honestly(site):
    trace = run(site)["trace"]
    assert trace["backend"] == "extractive-no-llm"
    assert trace["model"] is None
    assert trace["inference_on_amd"] is False
    assert trace["mode"] == "live"


def test_no_match_gives_no_answer_rather_than_a_guess(site):
    result = run(site, question="Quantum chromodynamics lattice gauge coupling?")
    assert result["status"] == "no_answer" and result["answer"] is None and result["sources"] == []


def test_private_start_url_is_refused(site):
    with pytest.raises(BlockedURL):
        run(site, start="http://10.0.0.1/")


def test_private_url_inside_question_is_refused(site):
    with pytest.raises(BlockedURL):
        run(site, question="What is on http://169.254.169.254/latest/meta-data/ today?", start=None)


def test_robots_denied_start_page_gives_no_answer(site):
    site.add("https://site.example/private/a", "<p>The Alder river is 251 km long.</p>")
    result = run(site, start="https://site.example/private/a")
    assert result["status"] == "no_answer"
    assert any(step["type"] == "fetch_denied_by_robots" for step in result["trace"]["steps"])


def test_page_cap_is_enforced(web):
    links = "".join(f'<a href="/river{i}">river alder length {i}</a>' for i in range(30))
    web.add("https://site.example/", f"<p>Nothing useful.</p>{links}")
    for i in range(30):
        web.add(f"https://site.example/river{i}", f"<p>Page {i} has no facts.</p>")
    result = agent.run("How long is the Alder river?", "https://site.example/", ExtractiveBackend(), Limits(max_pages=3), fetcher_factory=web.factory)
    assert sum(1 for step in result["trace"]["steps"] if step["type"] == "fetch") == 3


def test_step_cap_stops_the_run(site):
    result = agent.run("How long is the Alder river?", "https://site.example/", ExtractiveBackend(), Limits(max_steps=2), fetcher_factory=site.factory)
    assert any("step limit" in note for note in result["notes"])
    assert len(result["trace"]["steps"]) <= 2


def test_only_same_site_links_are_followed(web):
    web.add("https://site.example/", '<p>Index.</p><a href="https://other.example/alder-river-length">Alder river length</a>')
    result = run(web)
    assert not [url for url, _ in web.calls if "other.example" in url]
    assert result["status"] == "no_answer"


def test_search_step_when_no_start_url(web):
    body = json.dumps({"pages": [{"key": "Alder_river"}]})
    web.add("https://api.wikimedia.org/robots.txt", "", status=404)
    web.add("https://en.wikipedia.org/robots.txt", "", status=404)
    web.add(agent.SEARCH_ENDPOINT + "long%20Alder%20river", body, ctype="application/json")
    web.add("https://en.wikipedia.org/wiki/Alder_river", "<title>Alder river</title><p>The Alder river is 251 km long.</p>")
    result = run(web, start=None)
    assert result["status"] == "answered"
    assert result["trace"]["steps"][1]["type"] == "search"


def test_demo_switch_alters_a_quote_and_verifier_catches_it(site):
    result = run(site, inject_fabricated=True)
    bad = [c for c in result["claims"] if c["injected_for_demo"]]
    assert len(bad) == 1 and not bad[0]["verified"] and not bad[0]["in_answer"]
    assert bad[0]["claim"] not in result["answer"]
    assert any(step["type"] == "demo_injection" for step in result["trace"]["steps"])
