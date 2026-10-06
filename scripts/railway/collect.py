"""Read the reference machine's results from its Railway deployment log (see
deploy/railway-perf/run.sh) and write them to data/analysis/<version>/perf/.

    RAILWAY_TOKEN=... uv run python scripts/railway/collect.py [--service jtbd-perf]
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="jtbd-perf")
    parser.add_argument("--lines", default="5000")
    args = parser.parse_args()
    log = subprocess.run(["railway", "logs", "--service", args.service, "--deployment",
                          "--lines", args.lines], capture_output=True, text=True,
                         cwd="/tmp", check=True).stdout
    version = (ROOT / "benchmarks/current").read_text().strip()
    out = ROOT / "data/analysis" / version / "perf"
    out.mkdir(parents=True, exist_ok=True)
    found = re.findall(r"=== PERF_RESULT (\S+) ===\s*\n(\S+)\s*\n=== END \1 ===", log)
    for name, payload in found:
        data = json.loads(base64.b64decode(payload))
        (out / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(name, {k: data.get(k) for k in ("chunks_per_min", "latency_p50_ms",
                                              "peak_rss_mb", "peak_memory_mb")})
    for name in re.findall(r"=== PERF_ERROR (\S+) ===", log):
        print("error:", name)
    print("hardware:", re.search(r"=== HARDWARE ===\s*\n(.*)", log).group(1)
          if "=== HARDWARE ===" in log else None)
    print("done:", "=== ALL_DONE ===" in log)


if __name__ == "__main__":
    main()
