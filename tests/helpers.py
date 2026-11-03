"""Runs the real CLI as a subprocess with the stub backend, in a short temp dir (socket paths are length-limited)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app" / "app.py"
SITE = ROOT / "fixtures" / "site"
SCRIPT = ROOT / "fixtures" / "fake_script.json"
QUESTIONS = json.loads((ROOT / "fixtures" / "questions.json").read_text("utf-8"))["queries"]


class Box:
    def __init__(self, fake=True):
        self.dir = Path(tempfile.mkdtemp(prefix="m4t", dir="/tmp"))
        self.corpus = self.dir / "corpus"
        self.env = {
            **os.environ,
            "MC4_OUTPUT_DIR": str(self.dir / "output"),
            "MC4_INDEX_DIR": str(self.dir / "index"),
            "MC4_RUN_DIR": str(self.dir / "run"),
        }
        for name in ("MC4_ALLOW_FAKE", "MC4_BACKEND", "MC4_FAKE_SCRIPT", "MC4_CONTRACT", "PYTHONPATH"):
            self.env.pop(name, None)
        if fake:
            self.env.update(MC4_BACKEND="fake", MC4_ALLOW_FAKE="1", MC4_FAKE_SCRIPT=str(SCRIPT))

    def copy_site(self, faults=True):
        shutil.copytree(SITE, self.corpus)
        if faults:
            (self.corpus / "archive").mkdir()
            os.chmod(self.corpus / "vendor" / "k7-unit-pricing.html", 0)

    def cli(self, *flags, env=None, timeout=60, python_flags=()):
        return subprocess.run([sys.executable, *python_flags, str(APP), *flags], env={**self.env, **(env or {})}, capture_output=True, text=True, timeout=timeout)

    def index(self, env=None):
        return self.cli("--index", str(self.corpus), env=env)

    def ask(self, query_id, question, env=None, timeout=60, python_flags=()):
        return self.cli("--corpus", str(self.corpus), "--query-id", query_id, "--query", question, env=env, timeout=timeout, python_flags=python_flags)

    def output(self, query_id):
        return self.dir / "output" / f"{query_id}_output.json"

    def payload(self, query_id):
        return json.loads(self.output(query_id).read_text("utf-8"))

    def service_info(self):
        path = self.dir / "run" / "service.json"
        return json.loads(path.read_text("utf-8")) if path.exists() else {}

    def close(self):
        pid = self.service_info().get("pid")
        if pid:
            try:
                os.kill(pid, 15)
            except OSError:
                pass
        target = self.corpus / "vendor" / "k7-unit-pricing.html"
        if target.exists():
            os.chmod(target, 0o644)
        shutil.rmtree(self.dir, ignore_errors=True)
