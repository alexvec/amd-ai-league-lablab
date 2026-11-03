#!/usr/bin/env python3
"""Entry point of the resident model service. Started detached by --index, one process per container."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# In the image trailmark/ sits next to this file. In the repo it sits one level up.
for entry in (HERE, HERE.parent):
    if (entry / "trailmark").is_dir() and str(entry) not in sys.path:
        sys.path.insert(0, str(entry))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import adapter  # noqa: E402
from trailmark import service  # noqa: E402

if __name__ == "__main__":
    sys.exit(service.main(adapter.load()))
