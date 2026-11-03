#!/usr/bin/env python
"""Walks docs/demo-path.md in a real browser and fails if any step does not hold.

.venv/bin/python scripts/walk_demo.py --url https://amd-ai-league-lablab.vercel.app
Add --headed --slow-mo 600 --video-dir demo-recordings to record it.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request

from playwright.sync_api import expect, sync_playwright

QUESTION_TIMEOUT = 45_000
METADATA_URL = "http://169.254.169.254/latest/meta-data/"


def step(number: int, text: str) -> None:
    print(f"step {number} ok: {text}", flush=True)


def walk(page, base_url: str, health: dict) -> None:
    page.goto(base_url)
    expect(page.locator("#health-backend")).to_have_text(health["backend"])
    expect(page.locator("#health-deployment")).to_have_text(health["deployment"])
    expect(page.locator("#health-amd")).to_have_text(health["amd"]["statement"])
    step(1, f"header shows backend {health['backend']} and deployment {health['deployment']} from /health")

    page.click("#example")
    page.click("#ask")
    expect(page.locator("#result")).to_be_visible(timeout=QUESTION_TIMEOUT)
    expect(page.locator("#result-backend")).to_have_text(health["backend"])
    expect(page.locator("#answer")).not_to_have_class("answer empty")
    verified = page.locator("#claims li.claim.ok")
    expect(verified.first).to_be_visible()
    mark = page.locator("#page mark")
    expect(mark).to_be_visible()
    expect(page.locator("#steps li.step-fetch").first).to_be_visible()
    expect(page.locator("#steps li.step-verify").first).to_be_visible()
    step(2, f"{verified.count()} verified claims, quote highlighted: {mark.inner_text()[:70]!r}")

    page.check("#inject")
    page.click("#ask")
    bad = page.locator("#claims li.claim.bad")
    expect(bad).to_have_count(1, timeout=QUESTION_TIMEOUT)
    expect(bad.locator(".badge.demo")).to_be_visible()
    altered = bad.locator(".claim-text").inner_text()
    answer = page.locator("#answer").inner_text()
    if altered in answer:
        raise AssertionError("the altered claim reached the answer")
    step(3, f"altered quote flagged and absent from the answer: {altered[:70]!r}")
    page.uncheck("#inject")

    page.fill("#start-url", METADATA_URL)
    page.click("#ask")
    expect(page.locator("#error")).to_contain_text("URL refused", timeout=QUESTION_TIMEOUT)
    step(4, f"refused: {page.locator('#error').inner_text()}")

    options = page.locator("#trace-select option")
    if options.count() == 0 or page.locator("#replay").is_disabled():
        raise AssertionError("no recorded run to replay")
    page.select_option("#trace-select", index=0)
    label = options.first.inner_text()
    page.click("#replay")
    expect(page.locator("#replay-notice")).to_be_visible(timeout=QUESTION_TIMEOUT)
    expect(page.locator("#replay-notice")).to_contain_text("Replay of a run recorded")
    expect(page.locator("#trace-meta")).to_contain_text("Mode replay")
    step(5, f"replay labelled: {label[:90]!r}; backend in trace {page.locator('#result-backend').inner_text()}")


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
        console_errors = []
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        try:
            walk(page, base_url, health)
        finally:
            context.close()
            browser.close()
    if console_errors:
        print(f"page errors: {console_errors}", file=sys.stderr)
        return 1
    print(f"demo path walked against {base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
