#!/usr/bin/env python3
"""Local self-check, modelled on the Match 3 kit's selfcheck.py, same step order, extended.

    python tools/selfcheck_m4.py --local                  # stub model, invented pages, this machine
    python tools/selfcheck_m4.py --local --backend rocm --model-dir DIR --evidence-dir DIR   # GPU notebook
    python tools/selfcheck_m4.py --docker IMAGE           # kit flow plus fixtures and faults

This is our own harness and not AMD's evaluator. Passing it with the stub backend means the plumbing
behaves. The words ALL CHECKS PASSED appear only when step 8 measured VRAM in band on an AMD GPU with
the real backend. Anywhere else the best possible final line is the plumbing line.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "app"), str(ROOT / "tools")]

import adapter  # noqa: E402
import fixture_server  # noqa: E402
import vram_sampler  # noqa: E402
from trailmark.answer import comparison_key  # noqa: E402

PLUMBING_LINE = "PLUMBING CHECKS PASSED (no AMD GPU, no evidence)"
STUB_ON_AMD_LINE = "PLUMBING CHECKS PASSED (stub model, no evidence)"
STUB_NOTICE = (
    "STUB MODEL IN USE: backend fake replays a hand-written script. It is not a model, the required AMD "
    "capability did not run, and this is not a finished entry."
)
FAILED_LINE = "SOME CHECKS FAILED"
VRAM_FLOOR_GIB = 1.0
VRAM_CEILING_GIB = 48.0 * 1.01
IMAGE_LIMIT_GIB = 60.0
FIXTURES = ROOT / "fixtures"
GUARD_SITE = ROOT / "tools" / "guard_site"
UNREADABLE = "vendor/k7-unit-pricing.html"


class Report:
    def __init__(self, log_path: Path | None = None):
        self.failed = False
        self.lines: list[str] = []
        self.log_path = log_path

    def say(self, text: str = "") -> None:
        print(text, flush=True)
        self.lines.append(text)

    def step(self, text: str) -> None:
        self.say(text)

    def ok(self, text: str) -> None:
        self.say(f"  [PASS] {text}")

    def bad(self, text: str) -> None:
        self.failed = True
        self.say(f"  [FAIL] {text}")

    def skip(self, text: str) -> None:
        self.say(f"  SKIPPED: {text}")

    def warn(self, text: str) -> None:
        self.say(f"  [WARN] {text}")


def apply_faults(corpus: Path) -> None:
    """The two faults git cannot carry."""
    (corpus / "archive").mkdir(exist_ok=True)
    os.chmod(corpus / UNREADABLE, 0)


def clear_faults(corpus: Path) -> None:
    target = corpus / UNREADABLE
    if target.exists():
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)


def check_payload(report: Report, payload: object, where: str) -> bool:
    """Step 5, as the kit does it, with its warnings turned into failures."""
    if not isinstance(payload, dict):
        report.bad(f"{where}: the JSON must be an object")
    elif not isinstance(payload.get("answer"), str):
        report.bad(f"{where}: missing a string answer")
    elif not isinstance(payload.get("citations"), list) or not all(isinstance(item, str) for item in payload["citations"]):
        report.bad(f"{where}: citations must be a list of strings")
    elif any(item.startswith("/") for item in payload["citations"]):
        report.bad(f"{where}: citation is an absolute path")
    elif payload["answer"] and not payload["citations"]:
        report.bad(f"{where}: a non-empty answer with no citations")
    elif not payload["answer"] and payload["citations"]:
        report.bad(f"{where}: a refusal must have empty citations")
    else:
        return True
    return False


def score(query: dict, payload: dict, base_url: str = "") -> tuple[bool, str]:
    """Step 6. Both the answer and the exact citation set, no partial credit, as in the kit."""
    expected = {comparison_key(item) for item in [query["expected_answer"], *query.get("answer_aliases", [])] if item}
    wanted = {base_url + item for item in query["expected_citations"]}
    if not query["expected_answer"]:
        return (payload["answer"] == "" and payload["citations"] == [], "expected an exact refusal")
    if comparison_key(payload["answer"]) not in expected:
        return False, f"answer {payload['answer']!r}, expected {query['expected_answer']!r}"
    if set(payload["citations"]) != wanted:
        return False, f"citations {sorted(payload['citations'])}, expected {sorted(wanted)}"
    return True, ""


def patched_contract(path: Path, **changes) -> Path:
    """A copy of the contract with some values replaced, one per key."""
    text = (ROOT / "app" / "contract.toml").read_text("utf-8")
    for key, value in changes.items():
        text, count = re.subn(rf"(?m)^{re.escape(key)} = .*$", f"{key} = {json.dumps(value)}", text, count=1)
        if count != 1:
            raise KeyError(key)
    path.write_text(text, "utf-8")
    return path


class LocalRun:
    def __init__(self, args, report: Report, work: Path):
        self.args = args
        self.report = report
        self.work = work
        self.corpus = work / "corpus"
        self.guard_log = work / "guard.log"
        self.run_dir = work / "run"
        self.env = {
            **os.environ,
            "PYTHONPATH": str(GUARD_SITE),
            "MC4_GUARD_NET": "1",
            "MC4_GUARD_LOG": str(self.guard_log),
            "MC4_OUTPUT_DIR": str(work / "output"),
            "MC4_INDEX_DIR": str(work / "index"),
            "MC4_RUN_DIR": str(self.run_dir),
            "MC4_BACKEND": args.backend,
        }
        self.env.pop("MC4_CONTRACT", None)
        if args.backend == "fake":
            self.env.update(MC4_ALLOW_FAKE="1", MC4_FAKE_SCRIPT=str(FIXTURES / "fake_script.json"))
        else:
            self.env.pop("MC4_ALLOW_FAKE", None)
            if args.model_dir:
                self.env["MC4_MODEL_DIR"] = str(args.model_dir)

    def cli(self, *flags: str, env: dict | None = None, timeout: float = 60.0) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "app" / "app.py"), *flags], env={**self.env, **(env or {})}, capture_output=True, text=True, timeout=timeout)

    def query(self, query_id: str, question: str, env: dict | None = None, timeout: float = 60.0) -> tuple[float, subprocess.CompletedProcess]:
        started = time.monotonic()
        done = self.cli("--corpus", str(self.corpus), "--query-id", query_id, "--query", question, env={"MC4_GUARD_NO_TORCH": "1", **(env or {})}, timeout=timeout)
        return time.monotonic() - started, done

    def service_pid(self) -> int | None:
        try:
            return int(json.loads((self.run_dir / "service.json").read_text("utf-8"))["pid"])
        except (OSError, ValueError, KeyError):
            return None

    def stop_service(self) -> None:
        pid = self.service_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                return
            for _ in range(50):
                try:
                    os.kill(pid, 0)
                except OSError:
                    return
                time.sleep(0.05)


def step2_guard(run: LocalRun, report: Report) -> None:
    report.step("2. no network (local mode: a guard refuses non-loopback sockets in every process)")
    probe = "import socket\ntry:\n socket.socket().connect(('192.0.2.1',80))\nexcept PermissionError:\n print('refused')\n"
    done = subprocess.run([sys.executable, "-c", probe], env={**run.env, "MC4_GUARD_LOG": str(run.work / "guard-probe.log")}, capture_output=True, text=True, timeout=30)
    if done.stdout.strip() == "refused":
        report.ok("guard is active: a probe to 192.0.2.1 was refused before connecting")
    else:
        report.bad(f"guard did not refuse the probe: {done.stdout} {done.stderr[:200]}")


def step3_index(run: LocalRun, report: Report, as_root: bool, budget: float) -> bool:
    report.step("3. the corpus copies in, and the index pass runs")
    shutil.copytree(FIXTURES / "site", run.corpus)
    apply_faults(run.corpus)
    report.ok(f"copied fixtures/site and applied faults: {UNREADABLE} mode 000, empty archive/")
    if as_root:
        report.warn("running as root: mode 000 does not stop root, so the unreadable-file path is not exercised here. Use --docker with --cap-drop DAC_OVERRIDE.")
    started = time.monotonic()
    try:
        done = run.cli("--index", str(run.corpus), timeout=budget)
    except subprocess.TimeoutExpired:
        report.bad(f"--index did not finish within {budget:.0f}s")
        return False
    if done.returncode != 0:
        report.bad(f"--index exited {done.returncode}: {(done.stderr or done.stdout).strip()[:400]}")
        return False
    report.ok(f"indexed and service ready in {time.monotonic() - started:.1f}s (budget {budget:.0f}s)")
    failures = {item["ref"]: item["kind"] for item in json.loads((run.work / "index" / "failures.json").read_text("utf-8"))}
    expected = {"vendor/supplier-agreement.pdf": "corrupt_pdf", "vendor/telemetry.dat": "binary_or_unknown_type", "archive": "empty_directory"}
    if not as_root:
        expected[UNREADABLE] = "unreadable"
    for ref, kind in expected.items():
        if failures.get(ref) == kind:
            report.ok(f"recorded, nothing raised: {ref} ({kind})")
        else:
            report.bad(f"expected failure {kind} for {ref}, got {failures.get(ref)}")
    pages = (run.work / "index" / "pages.jsonl").read_text("utf-8")
    if '"ref": "zz-late/warranty.html"' in pages:
        report.ok("a page sorted after the faulty files was still indexed")
    else:
        report.bad("pages after the faulty files were lost")
    return True


def steps456_questions(run: LocalRun, report: Report, query_budget: float) -> tuple[list[dict], int, int]:
    report.step("4. each question runs as a new process, within budget, with torch imports refused")
    queries = json.loads((FIXTURES / "questions.json").read_text("utf-8"))["queries"]
    rows: list[dict] = []
    for query in queries:
        try:
            seconds, done = run.query(query["id"], query["query"], timeout=query_budget + 5)
        except subprocess.TimeoutExpired:
            report.bad(f"{query['id']}: over the {query_budget:.0f}s budget")
            rows.append({"id": query["id"], "seconds": None, "exit": None})
            continue
        rows.append({"id": query["id"], "seconds": round(seconds, 3), "exit": done.returncode})
        if done.returncode != 0:
            report.bad(f"{query['id']}: exited {done.returncode}: {done.stderr.strip()[:300]}")
        elif seconds > query_budget:
            report.bad(f"{query['id']}: {seconds:.2f}s is over the {query_budget:.0f}s budget")
    timed = [row["seconds"] for row in rows if row["seconds"] is not None]
    if timed and not report.failed:
        report.ok(f"{len(timed)} processes, slowest {max(timed):.2f}s (budget {query_budget:.0f}s). Stub timings say nothing about a model.")
    imports = [line for line in _guard_lines(run) if line.startswith("import")]
    if imports:
        report.bad(f"a query process tried to import a model library: {imports[:3]}")
    else:
        report.ok("no query process imported torch or transformers")

    report.step("5. the output file is where it should be, and the right shape")
    good: dict[str, dict] = {}
    for query in queries:
        path = run.work / "output" / f"{query['id']}_output.json"
        try:
            payload = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError) as exc:
            report.bad(f"{path.name}: {type(exc).__name__}")
            continue
        if check_payload(report, payload, path.name):
            good[query["id"]] = payload
    if len(good) == len(queries):
        report.ok(f"{len(good)} output files with the exact keys")

    report.step("6. answers and exact citation sets, compared with fixtures/questions.json")
    correct = 0
    for query in queries:
        payload = good.get(query["id"])
        if payload is None:
            continue
        right, why = score(query, payload)
        row = next(item for item in rows if item["id"] == query["id"])
        row.update(answer=payload["answer"], citations=payload["citations"], correct=right)
        if right:
            correct += 1
            report.ok(f"{query['id']} answer={payload['answer']!r} citations={payload['citations']}  [{query['category']}]")
        else:
            report.bad(f"{query['id']} {why}  [{query['category']}]")
    report.say(f"  {correct} of {len(queries)} fixture questions matched. These are invented fixtures, not the Match's questions.")
    return rows, correct, len(queries)


def _guard_lines(run: LocalRun) -> list[str]:
    try:
        return run.guard_log.read_text("utf-8").splitlines()
    except OSError:
        return []


def step7_faults(run: LocalRun, report: Report, args) -> None:
    report.step("7. fault injection: HTTP page source")
    _proxy_faults(run, report, args)


def _proxy_faults(run: LocalRun, report: Report, args) -> None:
    """The HTTP page source against a local server with faulty pages, under the same socket guard."""
    server = fixture_server.start(FIXTURES / "site", slow_seconds=6.0)
    try:
        port = server.server_address[1]
        base = f"http://127.0.0.1:{port}/"
        contract = patched_contract(
            run.work / "contract-proxy.toml",
            mode="proxy",
            allowed_hosts=[base.rstrip("/")],
            seeds=[f"{base}fault/index.html"],
            fetch_timeout_s=1.5,
            per_host_delay_s=0.0,
            max_bytes=200000,
        )
        env = {"MC4_CONTRACT": str(contract), "MC4_INDEX_DIR": str(run.work / "index-proxy"), "MC4_OUTPUT_DIR": str(run.work / "output-proxy"), "MC4_PAGES_MODE": "proxy"}
        started = time.monotonic()
        done = run.cli("--index", base + "fault/index.html", env=env, timeout=120)
        if done.returncode != 0:
            report.bad(f"proxy-mode index exited {done.returncode}: {(done.stderr or done.stdout)[:300]}")
            return
        failures = {item["ref"]: item for item in json.loads((run.work / "index-proxy" / "failures.json").read_text("utf-8"))}
        for name in ("500", "redirect-loop", "slow", "binary"):
            if base + f"fault/{name}" in failures:
                report.ok(f"HTTP fault {name}: recorded as {failures[base + f'fault/{name}']['kind']}, walk continued")
            else:
                report.bad(f"HTTP fault {name} was not recorded as a failure")
        pages = {}
        for line in (run.work / "index-proxy" / "pages.jsonl").read_text("utf-8").splitlines():
            page = json.loads(line)
            pages[page["ref"]] = page
        oversized = pages.get(base + "fault/oversized")
        if oversized and oversized["truncated"] and len(oversized["text"]) <= 200000:
            report.ok("HTTP fault oversized: capped and marked truncated")
        else:
            report.bad("oversized page was not capped")
        if base + "index.html" in pages:
            report.ok(f"good pages after the faults were indexed over HTTP in {time.monotonic() - started:.1f}s total")
        else:
            report.bad("good pages after the faults were lost")
        question = next(q for q in json.loads((FIXTURES / "questions.json").read_text("utf-8"))["queries"] if q["id"] == "q01")
        seconds, done = run.query("proxy01", question["query"], env=env, timeout=60)
        payload = json.loads((run.work / "output-proxy" / "proxy01_output.json").read_text("utf-8"))
        right, why = score(question, payload, base)
        if right:
            report.ok(f"proxy mode cites by URL: {payload['citations']} in {seconds:.2f}s")
        elif args.backend == "fake":
            report.bad(f"proxy-mode question: {why}")
        else:
            report.warn(f"proxy-mode question with the real model did not match: {why}")
    finally:
        server.shutdown()


def service_faults(run: LocalRun, report: Report) -> None:
    """Destructive, so these run last: they stop the service."""
    pid = run.service_pid()
    run.stop_service()
    if pid is None:
        report.bad("no service pid recorded")
    question = "What is the maximum operating temperature of the Kestrel K7?"
    seconds, done = run.query("deadservice", question, timeout=40)
    _expect_refusal(run, report, "dead service", "deadservice", seconds, done, 30.0)

    # A service that accepts the connection and then never answers: only the deadline can save the query.
    contract = patched_contract(run.work / "contract-short.toml", query_s=5, margin_s=2.0)
    socket_path = run.run_dir / "model.sock"
    try:
        socket_path.unlink()
    except FileNotFoundError:
        pass
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(socket_path))
    listener.listen(8)
    held: list[socket.socket] = []
    stopping = threading.Event()

    def hold() -> None:
        listener.settimeout(0.2)
        while not stopping.is_set():
            try:
                held.append(listener.accept()[0])
            except OSError:
                continue

    thread = threading.Thread(target=hold, daemon=True)
    thread.start()
    try:
        seconds, done = run.query("stuckservice", question, env={"MC4_CONTRACT": str(contract)}, timeout=20)
        _expect_refusal(run, report, "stuck service (5 s budget)", "stuckservice", seconds, done, 5.0)
    finally:
        stopping.set()
        thread.join(timeout=2)
        listener.close()
        for conn in held:
            conn.close()

    seconds, done = run.query("noindex", question, env={"MC4_INDEX_DIR": str(run.work / "no-such-index")}, timeout=40)
    _expect_refusal(run, report, "missing index", "noindex", seconds, done, 30.0)


def _expect_refusal(run: LocalRun, report: Report, name: str, query_id: str, seconds: float, done, budget: float) -> None:
    try:
        payload = json.loads((run.work / "output" / f"{query_id}_output.json").read_text("utf-8"))
    except (OSError, ValueError) as exc:
        report.bad(f"{name}: no output file ({type(exc).__name__}), exit {done.returncode}")
        return
    if payload == {"answer": "", "citations": [], "confidence": 0.0} and seconds < budget and done.returncode == 0:
        report.ok(f"{name}: clean refusal in {seconds:.2f}s (budget {budget:.0f}s)")
    else:
        report.bad(f"{name}: payload {payload}, {seconds:.2f}s, exit {done.returncode}")


def step8_vram(report: Report, sampler, backend: str) -> tuple[bool, float | None]:
    report.step("8. VRAM")
    if backend != "rocm":
        if vram_sampler.available():
            report.skip("stub backend, so nothing was on the GPU to measure")
        else:
            report.skip("no AMD GPU")
        return False, None
    if sampler is None:
        report.bad("backend rocm, but no amd-smi or rocm-smi on this machine, so VRAM cannot be measured")
        return False, None
    sampler.stop()
    peak = sampler.peak_gib
    if peak is None:
        report.bad("the VRAM tool produced nothing the parser understood. Read vram-raw.log and fix the parser.")
        return False, None
    if VRAM_FLOOR_GIB <= peak <= VRAM_CEILING_GIB:
        report.ok(f"peak {peak:.2f} GiB over {sampler.samples} samples from {sampler.command} (band {VRAM_FLOOR_GIB:.0f} to 48 GiB)")
        return True, peak
    report.bad(f"peak {peak:.2f} GiB is outside the band, from {sampler.samples} samples")
    return False, peak


def final_line(report: Report, backend: str, vram_ok: bool, gpu_name: str | None) -> str:
    if report.failed:
        return FAILED_LINE
    if backend == "rocm" and vram_ok and gpu_name:
        return "ALL CHECKS PASSED"
    if vram_sampler.available():
        return STUB_ON_AMD_LINE
    return PLUMBING_LINE


def write_evidence(run: LocalRun, report: Report, target: Path, rows: list[dict], correct: int, total: int, peak: float | None, sampler, seconds: float, final: str) -> None:
    """Raw files as produced. Nothing here is edited afterwards; the manifest makes an edit visible."""
    info = {}
    try:
        info = json.loads((run.run_dir / "service.json").read_text("utf-8"))
    except (OSError, ValueError):
        pass
    for source, name in ((run.work / "output", "outputs"), (run.run_dir / "traces", "traces")):
        if source.is_dir():
            shutil.copytree(source, target / name, dirs_exist_ok=True)
    for source in (run.run_dir / "service.log", run.run_dir / "service.json", run.work / "index" / "failures.json"):
        if source.is_file():
            shutil.copy(source, target / source.name)
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    summary = {
        "kind": "selfcheck_local_on_gpu",
        "note": "Our own harness on fixture questions we invented. Not AMD's evaluator, and not the Match's questions.",
        "backend": info.get("backend"),
        "model": info.get("model"),
        "model_revision": info.get("model_revision"),
        "gpu": info.get("gpu"),
        "hip": info.get("hip"),
        "torch": info.get("torch"),
        "load_s": info.get("load_s"),
        "warmup_s": info.get("warmup_s"),
        "torch_max_memory_allocated_bytes_at_ready": info.get("max_memory_allocated_bytes"),
        "vram_peak_gib": peak,
        "vram_samples": sampler.samples if sampler else 0,
        "vram_tool": sampler.command if sampler else None,
        "fixture_correct": correct,
        "fixture_total": total,
        "questions": rows,
        "total_seconds": round(seconds, 2),
        "git_commit": commit,
        "final_line": final,
        "checks_failed": report.failed,
    }
    (target / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", "utf-8")
    (target / "selfcheck.log").write_text("\n".join(report.lines) + "\n", "utf-8")


def run_local(args) -> int:
    report = Report()
    contract = adapter.load(env={})
    budget = {key: float(value) for key, value in contract.section("time").items()}
    as_root = os.geteuid() == 0
    work = Path(tempfile.mkdtemp(prefix="m4", dir="/tmp"))  # short path: unix socket paths have a low length limit
    run = LocalRun(args, report, work)
    if args.backend == "fake":
        report.say(STUB_NOTICE)
    report.say("Our own harness, not AMD's evaluator. Fixture pages and questions are invented.")
    started = time.monotonic()
    sampler = None
    rows, correct, total = [], 0, 0
    gpu_name = None
    peak = None
    vram_ok = False
    final_evidence_seconds = 0.0
    try:
        report.step("1. image history")
        report.skip("local mode, no image")
        step2_guard(run, report)
        if args.backend == "rocm" and vram_sampler.available():
            sampler = vram_sampler.Sampler(args.evidence_dir).start()
        if step3_index(run, report, as_root, budget["startup_s"]):
            rows, correct, total = steps456_questions(run, report, budget["query_s"])
            step7_faults(run, report, args)
            try:
                gpu_name = json.loads((run.run_dir / "service.json").read_text("utf-8")).get("gpu")
            except (OSError, ValueError):
                gpu_name = None
            vram_ok, peak = step8_vram(report, sampler, args.backend)
            report.step("7, continued. fault injection: service (this stops the service, so it runs after VRAM)")
            final_evidence_seconds = time.monotonic() - started
            service_faults(run, report)
        else:
            vram_ok, peak = step8_vram(report, sampler, args.backend)
            final_evidence_seconds = time.monotonic() - started
        network = [line for line in _guard_lines(run) if not line.startswith("import")]
        report.step("2, continued. no process opened a non-loopback socket")
        if network:
            report.bad(f"non-loopback attempts: {network[:5]}")
        else:
            report.ok("the guard log is empty for the whole run")
    finally:
        if sampler is not None:
            sampler.stop()
        run.stop_service()
        clear_faults(run.corpus)
    report.say()
    if args.backend == "fake":
        report.say(STUB_NOTICE)
    final = final_line(report, args.backend, vram_ok, gpu_name)
    if args.evidence_dir:
        write_evidence(run, report, args.evidence_dir, rows, correct, total, peak, sampler, final_evidence_seconds, final)
    report.say(final)
    if args.evidence_dir:
        (args.evidence_dir / "selfcheck.log").write_text("\n".join(report.lines) + "\n", "utf-8")
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 1 if report.failed else 0


def docker(*command: str, timeout: float = 120.0) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *command], capture_output=True, text=True, timeout=timeout)


def run_docker(args) -> int:
    """The kit's flow plus steps 6 and 7. Never run against the mandated base from this repo so far."""
    report = Report()
    image = args.docker
    budget = {key: float(value) for key, value in adapter.load(env={}).section("time").items()}
    name = f"selfcheck-m4-{os.getpid()}"
    env_flags: list[str] = []
    if args.backend == "fake":
        report.say(STUB_NOTICE)
        env_flags = ["-e", "MC4_ALLOW_FAKE=1", "-e", "MC4_BACKEND=fake", "-e", "MC4_FAKE_SCRIPT=/tmp/fake_script.json"]
    report.say("Our own harness, not AMD's evaluator. Fixture pages and questions are invented.")

    report.step("1. image history and size")
    # The limit is uncompressed. The size `docker images` and `image inspect` print can be compressed,
    # as the kit warns, so this sums the layer sizes from the image history instead.
    history = docker("history", "--no-trunc", "--human=false", "--format", "{{.Size}}", image)
    if history.returncode != 0:
        report.bad(f"could not read image history: {history.stderr.strip()}")
        report.say(FAILED_LINE)
        return 1
    size_gib = sum(int(line) for line in history.stdout.split() if line.isdigit()) / 1024**3
    if size_gib <= 0:
        report.bad(f"could not read layer sizes from the history: {history.stdout[:200]}")
    elif size_gib <= IMAGE_LIMIT_GIB:
        report.ok(f"{size_gib:.2f} GiB, sum of layer sizes in the image history (limit {IMAGE_LIMIT_GIB:.0f} GiB uncompressed)")
    else:
        report.bad(f"{size_gib:.2f} GiB is over the limit")
    if args.base:
        def layers(reference):
            found = docker("image", "inspect", "--format", "{{json .RootFS.Layers}}", reference)
            return json.loads(found.stdout) if found.returncode == 0 else None

        base, built = layers(args.base), layers(image)
        if base and built and built[: len(base)] == base:
            report.ok("the image's lower layers are the base image's layers")
        else:
            report.bad("the image's lower layers do not match the base image")
    else:
        report.skip("no --base given, so the base layer identity was not compared")

    report.step("2. the container starts with no network and without DAC_OVERRIDE")
    flags = ["run", "-d", "--network", "none", "--cap-drop", "DAC_OVERRIDE", "--name", name, *env_flags]
    if args.backend == "rocm":
        flags += ["--device", "/dev/kfd", "--device", "/dev/dri"]
    up = docker(*flags, image)
    if up.returncode != 0:
        report.bad(f"container did not start: {up.stderr.strip()[:300]}")
        report.say(FAILED_LINE)
        return 1
    report.ok("started")
    sampler = vram_sampler.Sampler(args.evidence_dir).start() if args.backend == "rocm" and vram_sampler.available() else None
    vram_ok, gpu_name = False, None
    try:
        report.step("3. the corpus copies in, and the index pass runs")
        docker("exec", name, "mkdir", "-p", "/app/corpus", "/app/output", timeout=60)
        copied = docker("cp", f"{FIXTURES / 'site'}/.", f"{name}:/app/corpus", timeout=600)
        if copied.returncode != 0:
            report.bad(f"could not copy the corpus in: {copied.stderr.strip()[:300]}")
        if args.backend == "fake":
            docker("cp", str(FIXTURES / "fake_script.json"), f"{name}:/tmp/fake_script.json")
        docker("exec", name, "mkdir", "-p", "/app/corpus/archive")
        docker("exec", name, "chmod", "000", f"/app/corpus/{UNREADABLE}")
        started = time.monotonic()
        try:
            done = docker("exec", *env_flags, name, "python3", "/app/app.py", "--index", "/app/corpus", timeout=budget["startup_s"])
            if done.returncode != 0:
                report.bad(f"--index exited {done.returncode}: {(done.stderr or done.stdout).strip()[:400]}")
            else:
                report.ok(f"indexed in {time.monotonic() - started:.1f}s (budget {budget['startup_s']:.0f}s)")
        except subprocess.TimeoutExpired:
            report.bad("--index went over the startup budget")
        failures = docker("exec", name, "cat", "/app/index/failures.json")
        kinds = {item["ref"]: item["kind"] for item in json.loads(failures.stdout)} if failures.returncode == 0 else {}
        if kinds.get(UNREADABLE) == "unreadable":
            report.ok("chmod 000 raised for real inside the container and was recorded")
        else:
            report.bad(f"unreadable file was not recorded as unreadable: {kinds.get(UNREADABLE)}")

        report.step("4, 5, 6. one new process per question, output shape, exact answers")
        queries = json.loads((FIXTURES / "questions.json").read_text("utf-8"))["queries"]
        correct = 0
        for query in queries:
            started = time.monotonic()
            try:
                done = docker("exec", *env_flags, name, "python3", "/app/app.py", "--corpus", "/app/corpus", "--query-id", query["id"], "--query", query["query"], timeout=budget["query_s"])
            except subprocess.TimeoutExpired:
                report.bad(f"{query['id']}: over the per-question budget")
                continue
            if done.returncode != 0:
                report.bad(f"{query['id']}: exit {done.returncode}: {done.stderr.strip()[:200]}")
                continue
            shown = docker("exec", name, "cat", f"/app/output/{query['id']}_output.json")
            try:
                payload = json.loads(shown.stdout)
            except ValueError:
                report.bad(f"{query['id']}: output is not JSON")
                continue
            if not check_payload(report, payload, query["id"]):
                continue
            right, why = score(query, payload)
            correct += right
            if right:
                report.ok(f"{query['id']} in {time.monotonic() - started:.2f}s answer={payload['answer']!r} citations={payload['citations']}")
            else:
                report.bad(f"{query['id']} {why}")
        report.say(f"  {correct} of {len(queries)} fixture questions matched. These are invented fixtures, not the Match's questions.")

        ready = docker("exec", name, "cat", "/app/run/service.json")
        info = json.loads(ready.stdout) if ready.returncode == 0 else {}
        gpu_name = info.get("gpu")
        vram_ok, _ = step8_vram(report, sampler, args.backend)

        report.step("7. fault injection: dead service")
        # Python rather than the kill binary, which slim images do not have.
        stopped = docker("exec", name, "python3", "-c", f"import os; os.kill({int(info.get('pid', 0))}, 15)") if info.get("pid") else None
        if stopped is None or stopped.returncode != 0:
            report.bad(f"could not stop the service for this check: {stopped.stderr.strip()[:200] if stopped else 'no pid recorded'}")
        time.sleep(1)
        started = time.monotonic()
        done = docker("exec", *env_flags, name, "python3", "/app/app.py", "--corpus", "/app/corpus", "--query-id", "dead", "--query", "What is the maximum operating temperature of the Kestrel K7?", timeout=budget["query_s"])
        shown = docker("exec", name, "cat", "/app/output/dead_output.json")
        if shown.stdout.strip() == '{"answer": "", "citations": [], "confidence": 0.0}':
            report.ok(f"clean refusal in {time.monotonic() - started:.2f}s")
        else:
            report.bad(f"expected a refusal, got {shown.stdout[:200]} (exit {done.returncode})")
    finally:
        if sampler is not None:
            sampler.stop()
        docker("rm", "-f", name)
    report.say()
    if args.backend == "fake":
        report.say(STUB_NOTICE)
    final = final_line(report, args.backend, vram_ok, gpu_name)
    report.say(final)
    if args.evidence_dir:
        (args.evidence_dir / "selfcheck-docker.log").write_text("\n".join(report.lines) + "\n", "utf-8")
    return 1 if report.failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local", action="store_true", help="run on this machine with invented pages")
    mode.add_argument("--docker", metavar="IMAGE", help="run the kit-style flow against a built image")
    parser.add_argument("--backend", choices=("fake", "rocm"), default=None, help="default: fake for --local, rocm for --docker")
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--evidence-dir", type=Path, help="where raw evidence goes. Only with the rocm backend.")
    parser.add_argument("--base", help="base image to compare lower layers with (docker mode)")
    parser.add_argument("--keep", action="store_true", help="keep the temporary work directory")
    args = parser.parse_args(argv)
    if args.backend is None:
        args.backend = "fake" if args.local else "rocm"
    if args.evidence_dir:
        if args.backend != "rocm":
            parser.error("--evidence-dir needs --backend rocm: a stub run is never evidence")
        args.evidence_dir.mkdir(parents=True, exist_ok=True)
    return run_local(args) if args.local else run_docker(args)


if __name__ == "__main__":
    sys.exit(main())
