from trailmark.robots import from_status, parse

TOKEN = "trailmarkbot"


def test_longest_match_wins_over_order():
    robots = parse("User-agent: *\nDisallow: /a/\nAllow: /a/public/\n", TOKEN)
    assert robots.allowed("/a/public/x") and not robots.allowed("/a/other")


def test_allow_wins_a_tie():
    assert parse("User-agent: *\nDisallow: /a\nAllow: /a\n", TOKEN).allowed("/a")


def test_wildcard_and_end_anchor():
    robots = parse("User-agent: *\nDisallow: /*.pdf$\nDisallow: /*?session=\n", TOKEN)
    assert not robots.allowed("/docs/x.pdf")
    assert robots.allowed("/docs/x.pdf.html")
    assert not robots.allowed("/page?session=1")


def test_specific_group_replaces_star_group():
    robots = parse("User-agent: *\nDisallow: /\n\nUser-agent: TrailmarkBot\nDisallow: /only/\n", TOKEN)
    assert robots.allowed("/x") and not robots.allowed("/only/x")


def test_grouped_agents_share_rules():
    robots = parse("User-agent: other\nUser-agent: *\nDisallow: /x\n", TOKEN)
    assert not robots.allowed("/x/y")


def test_empty_disallow_allows_all():
    assert parse("User-agent: *\nDisallow:\n", TOKEN).allowed("/anything")


def test_status_handling():
    assert from_status(404, "", TOKEN).allowed("/x")
    assert not from_status(500, "", TOKEN).allowed("/x")
    assert not from_status(403, "", TOKEN).allowed("/x")


def test_wildcards_and_end_anchor():
    rules = parse("User-agent: *\nDisallow: /a/*/b$\nDisallow: /*.pdf$\nDisallow: /x*y*z\n", TOKEN)
    assert not rules.allowed("/a/1/2/b") and rules.allowed("/a/1/b/c")
    assert not rules.allowed("/file.pdf") and rules.allowed("/file.pdf?x=1")
    assert not rules.allowed("/x1y2z3") and rules.allowed("/x1z2y")


def test_hostile_wildcards_do_not_backtrack():
    import time

    rules = parse("User-agent: *\nDisallow: /" + "*a" * 400 + "*b$\n", TOKEN)
    started = time.monotonic()
    assert rules.allowed("/" + "a" * 2000)
    assert time.monotonic() - started < 1
