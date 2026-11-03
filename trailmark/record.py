"""Run the agent for real and write the trace. This is the only writer of traces/.

python -m trailmark.record --question "..." --start-url https://... [--out traces]
python -m trailmark.record --questions amd/questions.json --require-amd
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

from . import __version__, agent, config, gpu
from .extractive import ExtractiveBackend
from .fetcher import Fetcher
from .llm import LLMBackend
from .netguard import BlockedURL


def _git_commit() -> str | None:
    try:
        done = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5, cwd=config.ROOT)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def record_one(question, start_url, backend, limits, out_dir: Path, fetcher_factory=Fetcher) -> Path:
    result = agent.run(question, start_url, backend, limits, fetcher_factory=fetcher_factory)
    result["trace"]["generated_by"] = {
        "tool": "trailmark.record",
        "version": __version__,
        "git_commit": _git_commit(),
        "platform": platform.platform(),
    }
    result["trace"]["gpu_vram_after_run"] = gpu.vram_snapshot() if result["trace"]["gpu"] else None
    slug = re.sub(r"[^a-z0-9]+", "-", question.lower()).strip("-")[:48] or "question"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result['trace']['backend']}-{slug}-{result['trace']['run_id']}.json"
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", "utf-8")
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question")
    parser.add_argument("--start-url")
    parser.add_argument("--questions", type=Path, help="JSON list of {question, start_url}")
    parser.add_argument("--out", type=Path, default=config.TRACES_DIR)
    parser.add_argument("--require-amd", action="store_true", help="refuse unless the trace will really be rocm-*")
    parser.add_argument("--request-seconds", type=float, default=25.0)
    args = parser.parse_args(argv)

    if args.questions:
        items = json.loads(args.questions.read_text("utf-8"))
    elif args.question:
        items = [{"question": args.question, "start_url": args.start_url}]
    else:
        parser.error("give --question or --questions")

    if config.backend_choice() == "llm":
        settings = config.llm_settings()
        if not settings["base_url"] or not settings["model"]:
            parser.error("TRAILMARK_BACKEND=llm needs TRAILMARK_LLM_BASE_URL and TRAILMARK_LLM_MODEL")
        backend = LLMBackend.from_settings(settings)
    else:
        backend = ExtractiveBackend()
    if args.require_amd and not backend.name.startswith("rocm-"):
        print(f"Refusing to record: backend is {backend.name}, not an AMD-served model. GPU: {gpu.detect()['gpu']}", file=sys.stderr)
        return 3

    limits = config.Limits(request_seconds=args.request_seconds)
    failures = 0
    for item in items:
        try:
            path = record_one(item["question"], item.get("start_url"), backend, limits, args.out)
        except BlockedURL as exc:
            print(f"refused: {item['question']}: {exc}", file=sys.stderr)
            failures += 1
            continue
        data = json.loads(path.read_text("utf-8"))
        print(json.dumps({"file": str(path), "status": data["status"], "backend": data["trace"]["backend"], "wall_ms": data["trace"]["wall_ms"], "tokens": data["trace"]["tokens"], "gpu": data["trace"]["gpu"]}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
