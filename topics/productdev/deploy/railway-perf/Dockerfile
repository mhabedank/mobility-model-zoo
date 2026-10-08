# Reference machine for performance runs (001 T074, 004 T042; research R6 as amended 2026-10-06).
# A temporary Railway service limited to 4 vCPU and 8 GB RAM, no GPU. The build context is staged
# by scripts/railway/stage.sh: the repository at HEAD plus the benchmark chunks and run manifests.
FROM ollama/ollama:latest

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}" \
    OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_HOST_VM=http://127.0.0.1:11434 \
    UV_LINK_MODE=copy

WORKDIR /app
COPY . /app
RUN uv sync --extra jtbd --no-dev

# The container runs the jobs named in PERF_MODELS / PERF_SPAN at start (run.sh) and keeps
# Ollama serving afterwards, so Railway does not restart it.
ENTRYPOINT []
CMD ["bash", "deploy/railway-perf/run.sh"]
