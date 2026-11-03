"""The packet must describe this product and must not claim what has not happened."""

import re

import pytest
from fastapi.testclient import TestClient

from trailmark import server

from .helpers import ROOT

PACKET = ["docs/submission.md", "docs/slides.md", "docs/demo-script.md"]
VOIDED_APP = ["extractive", "keyword", "rfc 2119", "wikimedia", "find it", "void", "/ask"]


def read(path):
    return (ROOT / path).read_text("utf-8")


def test_readme_says_it_plainly():
    text = read("README.md")
    assert "No real model and no AMD GPU has run this code. The stub only tests plumbing." in text
    assert "not registered for the hackathon" in text
    assert "## AI tool disclosure" in text and "Claude" in text
    assert "No AMD account exists" not in text


@pytest.mark.parametrize("path", [*PACKET, "docs/demo-path.md", "README.md", "amd/README.md"])
def test_nothing_describes_the_voided_app(path):
    text = read(path).lower()
    assert not [word for word in VOIDED_APP if word in text]


@pytest.mark.parametrize("path", PACKET)
def test_packet_is_marked_a_draft_on_its_first_line(path):
    first = read(path).splitlines()[0]
    assert "DRAFT, pending the AMD run" in first and "No real model and no AMD GPU has run this code" in first


def test_submission_field_counts_are_true():
    text = read("docs/submission.md")
    sections = re.findall(r"## [^\n]*?\((\d+) characters\)\n\n([^\n]+)\n", text)
    assert len(sections) == 3
    for stated, body in sections:
        assert int(stated) == len(body)
    title, short, long = [len(body) for _, body in sections]
    assert 5 <= title <= 50 and 50 <= short <= 255 and 600 <= long <= 2000


def test_the_walk_script_finds_what_it_looks_for():
    """No browser here. The elements and phrases scripts/walk_demo.py asserts are on the page."""
    script = read("scripts/walk_demo.py")
    page = TestClient(server.app).get("/").text
    for element in re.findall(r'"#([a-z-]+)', script):
        assert f'id="{element}"' in page, element
    assert page.split('id="build-state"')[1].split("</ul>")[0].count("<li>") == 4
    for phrase in ("runs no model and serves no answers", "scripted stub", "never run", "never built"):
        assert phrase in page


def test_state_does_not_tick_build():
    text = read("STATE.md")
    assert "- [ ] build" in text and "blocked on the notebook allowlist" in text
