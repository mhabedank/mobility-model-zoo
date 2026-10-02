"""Child process of `jtbd perf --backend span` (research R13). Base install only.

Reads a JSON job from argv[1], prints one JSON line with load time, latencies on the fixed text,
throughput over the chunk texts and the process's own peak RSS.
"""

from __future__ import annotations

import json
import resource
import statistics
import sys
import time


def main() -> None:
    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    import torch

    torch.set_num_threads(int(job["threads"]))
    from mobility_model_zoo.productdev.jtbd.span.extractor import SpanExtractor

    start = time.perf_counter()
    model = SpanExtractor.from_pretrained(job["model_dir"])
    load_time = time.perf_counter() - start
    text = job["text"]
    model.extract(text)  # warm-up
    latencies = []
    for _ in range(int(job["repeats"])):
        start = time.perf_counter()
        model.extract(text)
        latencies.append(time.perf_counter() - start)
    start = time.perf_counter()
    for chunk in job["chunks"]:
        model.extract(chunk)
    wall = time.perf_counter() - start
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    maxrss_mb = maxrss / (1024 * 1024) if sys.platform == "darwin" else maxrss / 1024
    print(json.dumps({
        "load_time_s": round(load_time, 4),
        "latency_9k_chars_s": round(statistics.median(latencies), 4),
        "latencies_s": [round(v, 4) for v in latencies],
        "text_chars": len(text),
        "n_chunks": len(job["chunks"]),
        "chunks_wall_s": round(wall, 4),
        "chunks_per_min": round(len(job["chunks"]) / wall * 60, 4) if wall else None,
        "ru_maxrss_mb": round(maxrss_mb, 1),
        "threads": torch.get_num_threads(),
    }))


if __name__ == "__main__":
    main()
