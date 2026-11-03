"""PRD acceptance test 7. Static checks only: this Dockerfile has not been built."""

import re
from pathlib import Path

from .helpers import ROOT

DOCKERFILE = (ROOT / "Dockerfile").read_text()
MANDATED = "FROM rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0"
LINES = [line.strip() for line in DOCKERFILE.splitlines() if line.strip() and not line.strip().startswith("#")]


def test_exact_mandated_from_is_the_only_from():
    assert [line for line in LINES if line.upper().startswith("FROM")] == [MANDATED]
    assert not [line for line in LINES if line.upper().startswith("ARG")]


def test_old_base_tags_are_gone_from_the_repo_build_files():
    for path in ("Dockerfile", "README.md", "amd/README.md", "amd/run_on_amd.sh"):
        text = (ROOT / path).read_text()
        assert "rocm/dev-ubuntu" not in text and "rocm/vllm" not in text, path


def test_fake_backend_is_never_enabled():
    assert "MC4_ALLOW_FAKE" not in DOCKERFILE and "MC4_BACKEND" not in DOCKERFILE and "fake" not in DOCKERFILE.lower()


def test_weights_are_copied_in():
    assert "COPY models/ /models/" in LINES
    assert '"models"' not in (ROOT / ".dockerignore").read_text() and "!models/**" in (ROOT / ".dockerignore").read_text()


def test_no_port_no_entrypoint_and_the_contract_cmd():
    upper = [line.upper() for line in LINES]
    assert not any(line.startswith(("EXPOSE", "ENTRYPOINT", "HEALTHCHECK")) for line in upper)
    assert LINES[-1] == 'CMD ["sleep", "infinity"]'


def test_nothing_is_downloaded_at_run_time_config():
    assert "HF_HUB_OFFLINE=1" in DOCKERFILE and "TRANSFORMERS_OFFLINE=1" in DOCKERFILE


def test_image_gets_the_cli_and_not_the_status_server():
    assert "COPY app/ /app/" in LINES and "COPY trailmark/ /app/trailmark/" in LINES
    ignored = (ROOT / ".dockerignore").read_text()
    assert "trailmark/server.py" in ignored and "trailmark/web" in ignored


def test_image_layout_finds_the_service_entry_point():
    from trailmark import indexer

    assert re.search(r"sibling = .*service_main\.py", Path(indexer.__file__).read_text())


def test_code_needed_in_the_image_does_not_use_fastapi():
    for path in (ROOT / "trailmark").glob("*.py"):
        if path.name != "server.py":
            assert "fastapi" not in path.read_text(), path.name
