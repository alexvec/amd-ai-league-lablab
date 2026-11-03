#!/usr/bin/env python
"""Walks part A of docs/demo-path.md in a real browser and fails if any step does not hold.

.venv/bin/python scripts/walk_demo.py --url https://amd-ai-league-lablab.vercel.app
Add --headed --slow-mo 600 --video-dir demo-recordings to record it.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request

from playwright.sync_api import expect, sync_playwright


def step(number: int, text: str) -> None:
    print(f"step {number} ok: {text}", flush=True)


def walk(page, base_url: str, health: dict) -> None:
    page.goto(base_url)
    statement = page.locator("#amd-statement")
    expect(statement).to_have_text(health["amd"]["statement"])
    step(1, f"statement matches /health: {health['amd']['statement']!r}")

    expect(page.locator("form, input, textarea, button")).to_have_count(0)
    expect(page.locator("#page-scope")).to_contain_text("runs no model and serves no answers")
    step(2, "no form or input; the page says it serves no answers")

    expect(page.locator("#build-state li")).to_have_count(4)
    expect(page.locator("#build-state")).to_contain_text("scripted stub")
    expect(page.locator("#build-state")).to_contain_text("never run")
    expect(page.locator("#build-state")).to_contain_text("never built")
    step(3, "the list separates stub-tested, never run and never built")

    if health["backend"] != "none" or health["answers_served"] is not False or health["model"] is not None:
        raise AssertionError(f"/health claims more than a status page: {health}")
    page.click("#health-link")
    expect(page.locator("body")).to_contain_text('"recorded_amd_runs"')
    step(4, f"/health: backend none, answers_served false, recorded_amd_runs {health['amd']['recorded_amd_runs']}")
    page.go_back()

    href = page.locator("#repo-link").get_attribute("href")
    if href != "https://github.com/alexvec/amd-ai-league-lablab":
        raise AssertionError(f"unexpected repo link: {href}")
    step(5, f"repo link: {href}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--slow-mo", type=int, default=0)
    parser.add_argument("--video-dir")
    args = parser.parse_args()
    base_url = args.url.rstrip("/")
    with urllib.request.urlopen(f"{base_url}/health", timeout=20) as response:
        health = json.load(response)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed, slow_mo=args.slow_mo)
        options = {"viewport": {"width": 1280, "height": 900}}
        if args.video_dir:
            options.update(record_video_dir=args.video_dir, record_video_size={"width": 1280, "height": 900})
        context = browser.new_context(**options)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            walk(page, base_url, health)
        finally:
            context.close()
            browser.close()
    if errors:
        print(f"page errors: {errors}", file=sys.stderr)
        return 1
    print(f"demo path part A walked against {base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
