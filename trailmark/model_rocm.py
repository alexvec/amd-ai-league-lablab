"""The real model on the AMD GPU through ROCm. UNTESTED: this has never run with a model or a GPU.

Only the refusal paths have been exercised, on a Mac with no torch and with a stub torch module.
The generation path has not been run anywhere. Imported only by the service process.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .backends import BackendRefused


class GpuRequired(BackendRefused):
    exit_code = 3


def assert_rocm(torch_module) -> dict:
    """Refuse unless torch sees a GPU through ROCm. A CPU run is not AMD evidence, so none is allowed."""
    if not torch_module.cuda.is_available():
        raise GpuRequired("torch.cuda.is_available() is false: no GPU visible. Refusing to run on the CPU.")
    hip = getattr(torch_module.version, "hip", None)
    if hip is None:
        raise GpuRequired("torch.version.hip is None: this torch is not a ROCm build. Refusing to run.")
    return {"gpu": torch_module.cuda.get_device_name(0), "hip": str(hip), "torch": str(torch_module.__version__)}


class RocmBackend:
    name = "rocm"

    def __init__(self, model_dir: str, model_name: str):
        try:
            import torch
        except ImportError as exc:
            raise GpuRequired(f"torch is not importable ({exc}). The rocm backend needs the mandated base image.") from exc
        self.gpu_info = assert_rocm(torch)
        path = Path(model_dir)
        if not (path / "config.json").is_file():
            raise GpuRequired(f"no model weights at {path}. The image must ship them; nothing is downloaded at run time.")
        # Before the import: these libraries read the flags when they load.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.model_name = model_name
        self.model_dir = str(path)
        started = time.monotonic()
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_dir, torch_dtype=torch.bfloat16, local_files_only=True).to("cuda")
        self.model.eval()
        device = next(self.model.parameters()).device.type
        if device != "cuda":
            raise GpuRequired(f"weights landed on {device}, not the GPU.")
        self.load_s = round(time.monotonic() - started, 2)
        self.warmup_s: float | None = None
        self._revision = self._read_revision(path)

    @staticmethod
    def _read_revision(path: Path) -> str | None:
        marker = path / "SOURCE.json"
        if marker.is_file():
            try:
                return json.loads(marker.read_text("utf-8")).get("revision")
            except ValueError:
                return None
        return None

    def info(self) -> dict:
        return {
            "backend": self.name,
            "model": self.model_name,
            "model_revision": self._revision,
            "is_stub": False,
            **self.gpu_info,
            "load_s": self.load_s,
            "warmup_s": self.warmup_s,
            "max_memory_allocated_bytes": int(self.torch.cuda.max_memory_allocated()),
        }

    def warmup(self) -> None:
        """A real generation, so readiness means the model has answered on the GPU. Not a dummy buffer."""
        started = time.monotonic()
        self.generate("warmup", [{"role": "user", "content": "Reply with the single word ready."}], {}, 16, 120.0)
        self.warmup_s = round(time.monotonic() - started, 2)

    def generate(self, kind: str, messages: list[dict], meta: dict, max_new_tokens: int, max_time_s: float) -> dict:
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        inputs = self.tokenizer([prompt], return_tensors="pt").to("cuda")
        with self.torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=int(max_new_tokens), do_sample=False, max_time=float(max_time_s))
        new_tokens = output[0][inputs["input_ids"].shape[1] :]
        return {
            "text": self.tokenizer.decode(new_tokens, skip_special_tokens=True),
            "tokens_in": int(inputs["input_ids"].shape[1]),
            "tokens_out": int(new_tokens.shape[0]),
        }
