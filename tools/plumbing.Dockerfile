# PLUMBING ONLY, NOT THE ENTRY. A tiny non-ROCm image for testing the self-check's docker mode, the
# detached service under docker exec, and mode 000 under --cap-drop DAC_OVERRIDE. It has no GPU, no
# model and no weights, and it is not on the mandated base, so nothing it does is AMD evidence.
#   docker build -f tools/plumbing.Dockerfile -t trailmark-plumbing .
#   python tools/selfcheck_m4.py --docker trailmark-plumbing --backend fake
FROM python:3.14-slim
WORKDIR /app
COPY app/ /app/
COPY trailmark/ /app/trailmark/
RUN mkdir -p /app/corpus /app/output /app/index /app/run
CMD ["sleep", "infinity"]
