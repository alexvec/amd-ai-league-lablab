"""PRD acceptance tests 6 and the Mac-testable part of 10: no torch in the client, refusal when the service is absent."""

import os
import re
import socket
import subprocess
import sys
import textwrap
import time

import pytest

from trailmark import model_rocm
from trailmark.backends import BackendRefused, FakeBackend, load_backend
from trailmark.client import ModelUnavailable, ServiceClient

from .helpers import QUESTIONS, ROOT, Box

REFUSAL = {"answer": "", "citations": [], "confidence": 0.0}


@pytest.fixture
def box():
    instance = Box()
    instance.copy_site(faults=False)
    yield instance
    instance.close()


def test_acceptance_6_client_never_imports_torch(box):
    assert box.index().returncode == 0
    done = box.ask("q", QUESTIONS[0]["query"], python_flags=("-X", "importtime"))
    assert done.returncode == 0 and box.payload("q")["answer"]
    imported = {line.rsplit("|", 1)[-1].strip().split(".")[0] for line in done.stderr.splitlines() if "|" in line}
    assert "trailmark" in imported, "importtime output did not parse, so this test proves nothing"
    assert not imported & {"torch", "transformers", "numpy", "safetensors"}


def test_acceptance_6_absent_service_refuses_before_the_deadline(box):
    (box.dir / "run").mkdir()
    assert box.index(env={"MC4_BACKEND": "no-such"}).returncode != 0  # stores an index, has no service
    started = time.monotonic()
    done = box.ask("q", QUESTIONS[0]["query"])
    assert done.returncode == 0 and box.payload("q") == REFUSAL
    assert time.monotonic() - started < 10


def test_stuck_service_refuses_at_the_deadline(box, tmp_path):
    assert box.index().returncode == 0
    os.kill(box.service_info()["pid"], 15)
    time.sleep(0.3)
    path = box.dir / "run" / "model.sock"
    if path.exists():
        path.unlink()
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    listener.listen(8)
    text = (ROOT / "app" / "contract.toml").read_text().replace("query_s = 30", "query_s = 4").replace("margin_s = 4.0", "margin_s = 2.0")
    contract = tmp_path / "short.toml"
    contract.write_text(text)
    started = time.monotonic()
    done = box.ask("stuck", QUESTIONS[0]["query"], env={"MC4_CONTRACT": str(contract)})
    elapsed = time.monotonic() - started
    listener.close()
    assert done.returncode == 0 and box.payload("stuck") == REFUSAL
    assert 1.5 < elapsed < 4


def test_service_stays_up_across_processes(box):
    assert box.index().returncode == 0
    pid = box.service_info()["pid"]
    for number in range(3):
        box.ask(f"p{number}", QUESTIONS[1]["query"])
    os.kill(pid, 0)
    assert box.service_info()["pid"] == pid


def test_index_reuses_a_live_service(box):
    assert box.index().returncode == 0
    pid = box.service_info()["pid"]
    assert box.index().returncode == 0
    assert box.service_info()["pid"] == pid


def test_socket_is_private_to_the_user(box):
    assert box.index().returncode == 0
    assert oct((box.dir / "run").stat().st_mode)[-3:] == "700"
    assert oct((box.dir / "run" / "model.sock").stat().st_mode)[-3:] == "600"


def test_service_answers_a_bad_request_and_keeps_going(box):
    assert box.index().returncode == 0
    path = box.dir / "run" / "model.sock"
    conn = socket.socket(socket.AF_UNIX)
    conn.connect(str(path))
    conn.sendall(b"not json\n")
    conn.close()
    client = ServiceClient(path, time.monotonic() + 5)
    assert client.ping()["backend"] == "fake"
    with pytest.raises(ModelUnavailable):
        client.call({"op": "no-such-op"})
    assert client.ping()["is_stub"] is True


def test_respawn_flag_is_off_by_default_and_works_when_set(box, tmp_path):
    assert box.index().returncode == 0
    os.kill(box.service_info()["pid"], 15)
    time.sleep(0.3)
    box.ask("off", QUESTIONS[1]["query"])
    assert box.payload("off") == REFUSAL
    text = (ROOT / "app" / "contract.toml").read_text().replace("respawn_on_missing = false", "respawn_on_missing = true")
    contract = tmp_path / "respawn.toml"
    contract.write_text(text)
    box.ask("on", QUESTIONS[1]["query"], env={"MC4_CONTRACT": str(contract)})
    assert box.payload("on")["answer"] == "Q3 FY27"


def test_fake_backend_is_blocked_without_the_variable(monkeypatch):
    monkeypatch.delenv("MC4_ALLOW_FAKE", raising=False)
    with pytest.raises(BackendRefused):
        FakeBackend()


def test_cli_with_fake_backend_refuses_to_start_without_the_variable(box):
    done = box.index(env={"MC4_ALLOW_FAKE": ""})
    assert done.returncode != 0 and "no model is available" in done.stderr
    assert "needs MC4_ALLOW_FAKE=1" in (box.dir / "run" / "service.log").read_text()
    assert not box.service_info()


def test_default_backend_is_the_real_one():
    import adapter

    assert adapter.load(env={}).section("service")["backend"] == "rocm"


def test_unknown_backend_is_refused():
    with pytest.raises(BackendRefused):
        load_backend("cpu", {})


class StubCuda:
    def __init__(self, available):
        self.available = available

    def is_available(self):
        return self.available

    def get_device_name(self, _):
        return "Stub GPU for a test"


class StubTorch:
    __version__ = "0"

    def __init__(self, available, hip):
        self.cuda = StubCuda(available)
        self.version = type("V", (), {"hip": hip})


def test_gpu_check_refuses_no_gpu():
    with pytest.raises(model_rocm.GpuRequired, match="no GPU"):
        model_rocm.assert_rocm(StubTorch(False, "6.0"))


def test_gpu_check_refuses_a_non_rocm_build():
    with pytest.raises(model_rocm.GpuRequired, match="not a ROCm build"):
        model_rocm.assert_rocm(StubTorch(True, None))


def test_gpu_check_reports_what_it_found():
    found = model_rocm.assert_rocm(StubTorch(True, "6.0"))
    assert found["gpu"] == "Stub GPU for a test" and found["hip"] == "6.0"


@pytest.mark.parametrize(
    "stub,code,message",
    [
        (None, 3, "torch is not importable"),
        ("class cuda:\n    is_available=staticmethod(lambda: False)\nclass version:\n    hip='6'\n", 3, "no GPU visible"),
        ("class cuda:\n    is_available=staticmethod(lambda: True)\nclass version:\n    hip=None\n", 3, "not a ROCm build"),
    ],
)
def test_real_service_process_refuses_without_a_rocm_gpu(box, tmp_path, stub, code, message):
    """Part of acceptance test 10, on the Mac only. On the AMD machine it still has to be run."""
    env = dict(box.env)
    env.pop("MC4_ALLOW_FAKE")
    env["MC4_BACKEND"] = "rocm"
    if stub is not None:
        (tmp_path / "torch.py").write_text(stub)
        env["PYTHONPATH"] = str(tmp_path)
    elif _torch_installed():
        pytest.skip("this machine has torch")
    done = subprocess.run([sys.executable, str(ROOT / "app" / "service_main.py")], env=env, capture_output=True, text=True, timeout=30)
    assert done.returncode == code and message in done.stderr
    assert not (box.dir / "run" / "model.sock").exists()


def _torch_installed():
    import importlib.util

    return importlib.util.find_spec("torch") is not None


def test_rocm_backend_refuses_when_weights_are_absent(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", StubTorch(True, "6.0"))
    with pytest.raises(model_rocm.GpuRequired, match="no model weights"):
        model_rocm.RocmBackend(str(tmp_path), "m")


def test_model_code_never_downloads():
    source = (ROOT / "trailmark" / "model_rocm.py").read_text()
    assert source.count("local_files_only=True") == 2 and "snapshot_download" not in source


def test_model_code_is_stamped_untested():
    assert "UNTESTED" in textwrap.dedent((ROOT / "trailmark" / "model_rocm.py").read_text()).splitlines()[0]


def test_nothing_outside_the_service_path_imports_torch():
    for path in (ROOT / "trailmark").glob("*.py"):
        if path.name != "model_rocm.py":
            assert not re.search(r"(?m)^\s*(import|from)\s+(torch|transformers)\b", path.read_text()), path.name
