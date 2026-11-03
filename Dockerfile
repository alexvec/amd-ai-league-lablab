# Artifact shape: agent plus optional local model server, on a ROCm base.
#
# The base tag the Match 4 evaluator requires, if any, is UNVERIFIED: no official source states it.
# Both tags below were confirmed to exist through the Docker Hub tags API on 2026-11-03. Neither has
# been pulled or built from, so this file has never been built on a ROCm base.
#   rocm/dev-ubuntu-22.04:7.2.4 (default, compressed size 1.09 GB as reported by Docker Hub)
#   rocm/vllm:rocm10.1.0_ubuntu24.04_py3.14-pytorch_2.13.0_vllm-0.29.0 (31.3 GB as reported by Docker Hub;
#     also listed in AMD's vLLM page, and larger than the notebook's roughly 25 GB of storage)
# To serve a model in the container, pass the second one as --build-arg ROCM_BASE=...
# Model weights are not included. Serving a model from this image is untested.
ARG ROCM_BASE=rocm/dev-ubuntu-22.04:7.2.4
FROM ${ROCM_BASE}

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TRAILMARK_DEPLOYMENT=container

# ensurepip is the part Debian and Ubuntu leave out of python3 without python3-venv.
RUN command -v python3 >/dev/null && python3 -c "import ensurepip" >/dev/null 2>&1 \
    || (apt-get update && apt-get install -y --no-install-recommends python3 python3-venv && rm -rf /var/lib/apt/lists/*)
RUN python3 -m venv --system-site-packages /opt/trailmark-venv

WORKDIR /opt/trailmark
COPY requirements.txt ./
RUN /opt/trailmark-venv/bin/pip install -r requirements.txt uvicorn==0.54.0
COPY trailmark ./trailmark
COPY traces ./traces
COPY docker/start.sh ./start.sh
RUN chmod +x start.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD /opt/trailmark-venv/bin/python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=4)"
ENTRYPOINT ["/opt/trailmark/start.sh"]
