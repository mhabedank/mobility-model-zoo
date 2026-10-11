# Reference machine for `jtbd cluster perf` (feature 009, tasks T057; decision D-railway-perf).
# A temporary Railway service in EU West (Amsterdam), limited to 4 vCPU and 8 GB RAM, no GPU. The
# build context is staged by topics/productdev/scripts/railway/stage_cluster.sh: the repository at
# HEAD plus the redacted benchmark pool of cluster-v1, nothing else from data/.
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}" UV_LINK_MODE=copy

WORKDIR /app
COPY . /app
RUN uv sync --extra jtbd --extra cluster --no-dev

ENTRYPOINT []
CMD ["bash", "topics/productdev/deploy/railway-cluster-perf/run.sh"]
