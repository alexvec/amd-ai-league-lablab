#!/usr/bin/env python3
"""Download the model into a directory, and record which revision it was. Needs huggingface_hub and the network.

Run this on the GPU notebook or the image build machine. Never at evaluation. Never run on the build Mac.
UNTESTED: this has not been run anywhere.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_MODEL = "Qwen/Qwen3-4B-Instruct-2507"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    from huggingface_hub import HfApi, snapshot_download

    revision = HfApi().model_info(args.model).sha
    args.target.mkdir(parents=True, exist_ok=True)
    snapshot_download(args.model, revision=revision, local_dir=str(args.target), allow_patterns=["*.json", "*.safetensors", "*.txt", "*.jinja", "LICENSE*", "README*"])
    (args.target / "SOURCE.json").write_text(json.dumps({"model": args.model, "revision": revision}, indent=1) + "\n", "utf-8")
    print(json.dumps({"model": args.model, "revision": revision, "dir": str(args.target)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
