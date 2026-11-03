# The Match 4 image, per the Match 3 kit's programme-wide contract. NOT YET BUILT: the base is about
# 29.2 GiB, and building needs a machine with Docker and at least 60 GiB free. See amd/README.md.
FROM rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0

WORKDIR /app

# Weights ship in the image: there is no outbound network at grading. Put them in models/qwen3-4b
# before building, with tools/fetch_weights.py. They count against the 60 GiB uncompressed limit.
COPY models/ /models/

ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1

COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/
COPY trailmark/ /app/trailmark/

RUN mkdir -p /app/corpus /app/output /app/index /app/run

# No service at build time, no port and no entrypoint script. The harness execs into this container.
# --index starts the resident model service on a unix socket under /app/run.
CMD ["sleep", "infinity"]
