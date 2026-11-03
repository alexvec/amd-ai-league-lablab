#!/usr/bin/env python3
"""The contract CLI. The harness execs this; nothing here listens on a port.

    python3 /app/app.py --index /app/corpus
    python3 /app/app.py --corpus /app/corpus --query-id query_01 --query "..."

Output: /app/output/<query-id>_output.json with answer, citations and confidence, written whole.
A failure of any kind inside a query is a refusal in that file, never a missing file. This process
never imports torch; the model lives in the resident service behind a unix socket.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
# In the image trailmark/ sits next to this file. In the repo it sits one level up.
for entry in (HERE, HERE.parent):
    if (entry / "trailmark").is_dir() and str(entry) not in sys.path:
        sys.path.insert(0, str(entry))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import adapter  # noqa: E402
from trailmark import indexer, runner  # noqa: E402


def build_parser(contract: adapter.Contract) -> argparse.ArgumentParser:
    cli = contract.section("cli")
    parser = argparse.ArgumentParser(description="Trailmark contract CLI")
    parser.add_argument(cli["index_flag"], dest="index", help="build the index over this source, start the model service, exit")
    parser.add_argument(cli["corpus_flag"], dest="corpus", help="corpus root for a query")
    parser.add_argument(cli["query_id_flag"], dest="query_id", help="output stem assigned by the harness")
    parser.add_argument(cli["query_flag"], dest="query", help="the question")
    parser.add_argument(cli["start_url_flag"], dest="start_url", help="optional starting page")
    return parser


def run_query(contract: adapter.Contract, args) -> int:
    output = contract.output_path(args.query_id)
    lock = threading.Lock()
    written = threading.Event()

    def write(answer: str, citations: list[str], confidence: float) -> None:
        with lock:
            if written.is_set():
                return
            adapter.write_whole(output, contract.payload(answer, citations, confidence))
            written.set()

    def out_of_time() -> None:
        # A stuck socket or fetch must not cost the question its file. Exit hard: threads may be stuck.
        write("", [], 0.0)
        runner.record_trace(contract, args.query_id, {"question": args.query, "outcome": "refused", "reason": "deadline"})
        os._exit(0)

    budget = contract.query_seconds()
    watchdog = threading.Timer(budget, out_of_time)
    watchdog.daemon = True
    watchdog.start()
    try:
        result = runner.answer(contract, args.query, args.start_url, budget)
    except Exception as exc:  # noqa: BLE001 - any failure is a refusal, recorded in the trace
        result = runner.refusal({"question": args.query}, f"internal_error: {type(exc).__name__}: {exc}")
    finally:
        watchdog.cancel()
    write(result.answer, result.citations, result.confidence)
    runner.record_trace(contract, args.query_id, result.trace)
    return 0


def main(argv: list[str] | None = None) -> int:
    contract = adapter.load()
    parser = build_parser(contract)
    args = parser.parse_args(argv)
    if args.index is not None:
        return indexer.run_index(contract, args.index)
    if args.query is None or not args.query_id:
        parser.error("a query needs the corpus, query id and query flags")
    try:
        return run_query(contract, args)
    except adapter.BadQueryId as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
