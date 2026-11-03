"""PRD acceptance test 5: per-page failure tolerance, in-process. test_cli.py covers it through the CLI."""

import os
import shutil

import pytest

from trailmark.pages import HTTPSource, MirrorSource, Page, PageError, PageFailure, decode_bytes, open_source

from .helpers import SITE


def walk(root):
    items = list(MirrorSource(root).walk())
    return {i.ref: i for i in items if isinstance(i, Page)}, {i.ref: i.kind for i in items if isinstance(i, PageFailure)}


@pytest.fixture
def corpus(tmp_path):
    root = tmp_path / "c"
    shutil.copytree(SITE, root)
    (root / "archive").mkdir()
    os.chmod(root / "vendor/k7-unit-pricing.html", 0)
    yield root
    os.chmod(root / "vendor/k7-unit-pricing.html", 0o644)


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses mode 000")
def test_every_fault_is_recorded_and_later_pages_survive(corpus):
    pages, failures = walk(corpus)
    assert failures["vendor/k7-unit-pricing.html"] == "unreadable"
    assert failures["vendor/supplier-agreement.pdf"] == "corrupt_pdf"
    assert failures["vendor/telemetry.dat"] == "binary_or_unknown_type"
    assert failures["archive"] == "empty_directory"
    assert "zz-late/warranty.html" in pages


def test_truncated_html_and_wrong_encoding_are_still_read(corpus):
    pages, _ = walk(corpus)
    assert "IP54" in pages["notes/enclosure-truncated.html"].text
    assert "Zürich" in pages["notes/calibration-wrong-encoding.html"].text
    assert "encoding_fallback_cp1252" in pages["notes/calibration-wrong-encoding.html"].notes


def test_hidden_text_never_reaches_the_stored_page(corpus):
    pages, _ = walk(corpus)
    assert "777" not in pages["notes/injection.html"].text


def test_links_map_to_corpus_relative_refs(corpus):
    pages, _ = walk(corpus)
    refs = {link["ref"] for link in pages["products/accessories.html"].links}
    assert "accessories/ax-220.html" in refs


def test_symlink_out_of_the_root_is_refused(tmp_path):
    root = tmp_path / "c"
    root.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret value here")
    (root / "link.txt").symlink_to(secret)
    (root / "z.txt").write_text("a later page")
    pages, failures = walk(root)
    assert failures["link.txt"] == "symlink_refused" and "z.txt" in pages


@pytest.mark.parametrize("ref", ["../secret.txt", "/etc/passwd", "a/../../secret.txt"])
def test_read_cannot_leave_the_root(tmp_path, ref):
    with pytest.raises(PageError):
        MirrorSource(tmp_path).read(ref)


def test_links_cannot_leave_the_root(tmp_path):
    # URL resolution clamps ".." at the root, as a browser does, so this names root/etc/passwd.
    (tmp_path / "a.html").write_text('<p>body</p><a href="../../etc/passwd">x</a><a href="https://other.example/">y</a><a href="b.html">z</a>')
    page = MirrorSource(tmp_path).read("a.html")
    refs = [link["ref"] for link in page.links]
    assert refs == ["etc/passwd", "b.html"]
    assert not any(ref.startswith(("/", "..")) for ref in refs)
    with pytest.raises(PageError):
        MirrorSource(tmp_path).read("etc/passwd")


def test_oversized_file_is_capped_and_marked(tmp_path):
    (tmp_path / "big.txt").write_text("word " * 10000)
    page = MirrorSource(tmp_path, max_bytes=1000).read("big.txt")
    assert page.truncated and len(page.text) <= 1000 and "oversized_truncated" in page.notes


def test_fifo_does_not_hang_the_walk(tmp_path):
    os.mkfifo(tmp_path / "pipe.txt")
    (tmp_path / "z.txt").write_text("a later page")
    pages, failures = walk(tmp_path)
    assert failures["pipe.txt"] == "not_a_regular_file" and "z.txt" in pages


def test_unexpected_exception_in_one_page_does_not_stop_the_walk(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("first page")
    (tmp_path / "b.txt").write_text("second page")
    source = MirrorSource(tmp_path)
    real = source.read
    monkeypatch.setattr(source, "read", lambda ref: (_ for _ in ()).throw(MemoryError("boom")) if ref == "a.txt" else real(ref))
    items = list(source.walk())
    assert [type(item).__name__ for item in items] == ["PageFailure", "Page"]


def test_decode_prefers_bom_and_never_raises():
    assert decode_bytes(b"\xef\xbb\xbfhello")[0] == "hello"
    assert decode_bytes(b'<meta charset="latin-1">caf\xe9')[0].endswith("café")
    assert decode_bytes(b'<meta charset="no-such-codec">ok')[0].endswith("ok")


def test_proxy_mode_refuses_a_proxy_that_is_not_http():
    with pytest.raises(ValueError):
        HTTPSource([], [], "socks5://x:1", None, 1, 1.0)


def contract_with(tmp_path, **changes):
    import adapter

    contract = adapter.load(env={})
    data = {section: dict(values) for section, values in contract.data.items()}
    data["pages"].update(changes)
    return adapter.Contract(data, "test")


def test_open_source_picks_each_mode(tmp_path):
    assert open_source(contract_with(tmp_path), str(tmp_path)).mode == "mirror"
    assert open_source(contract_with(tmp_path, mode="proxy", allowed_hosts=["http://pages.internal:8080"]), None).mode == "proxy"
    assert open_source(contract_with(tmp_path, mode="proxy", proxy="http://proxy.internal:3128"), None).mode == "proxy"
    assert open_source(contract_with(tmp_path, mode="live"), None).mode == "live"


@pytest.mark.parametrize("changes", [{"mode": "live", "proxy": "http://p.internal:1"}, {"mode": "live", "allowed_hosts": ["http://p.internal:1"]}, {"mode": "ftp"}, {"mode": "mirror", "root": ""}])
def test_open_source_refuses_bad_config(tmp_path, changes):
    with pytest.raises(ValueError):
        open_source(contract_with(tmp_path, **changes), None)


def test_live_mode_still_refuses_private_addresses(tmp_path):
    source = open_source(contract_with(tmp_path, mode="live"), None)
    with pytest.raises(PageError, match="BlockedURL"):
        source.read("http://169.254.169.254/latest/meta-data/")
