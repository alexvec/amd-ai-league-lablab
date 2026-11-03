#!/usr/bin/env python3
"""Write MANIFEST.sha256 over every file in a run's evidence folder, so a later edit shows."""

import hashlib
import sys
from pathlib import Path

folder = Path(sys.argv[1])
names = sorted(path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file() and path.name != "MANIFEST.sha256")
lines = [f"{hashlib.sha256((folder / name).read_bytes()).hexdigest()}  {name}" for name in names]
(folder / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", "utf-8")
print(f"{len(names)} files listed in {folder / 'MANIFEST.sha256'}")
