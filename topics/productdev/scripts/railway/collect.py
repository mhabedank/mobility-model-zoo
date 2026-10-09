"""Read the reference machine's results from its Railway deployment log (see
topics/productdev/deploy/railway-perf/run.sh) and write them to data/analysis/<version>/perf/.

    RAILWAY_TOKEN=... uv run python topics/productdev/scripts/railway/collect.py [--service jtbd-perf]
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="jtbd-perf")
    parser.add_argument("--lines", default="5000")
    parser.add_argument("--deployment-id", default=None,
                        help="read this deployment (default: Railway's latest successful one, "
                             "which is the previous one while a new deployment builds)")
    args = parser.parse_args()
    cmd = ["railway", "logs", "--service", args.service, "--deployment", "--lines", args.lines]
    if args.deployment_id:
        cmd.insert(2, args.deployment_id)
    log = subprocess.run(cmd, capture_output=True, text=True, cwd="/tmp", check=True).stdout
    version = (ROOT / "topics/productdev/benchmarks/current").read_text().strip()
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
