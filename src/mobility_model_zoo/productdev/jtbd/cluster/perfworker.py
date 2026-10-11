"""Child process of `jtbd cluster perf`: one stage run, then time, peak RSS and counts as JSON.

Usage: python -m mobility_model_zoo.productdev.jtbd.cluster.perfworker <settings.yaml> <bundle>
"""

from __future__ import annotations

import json
import resource
import sys
import time


def main(settings_path: str, bundle_path: str) -> None:
    from mobility_model_zoo.productdev.jtbd.cluster.bundle import read_bundle
    from mobility_model_zoo.productdev.jtbd.cluster.stage import ClusterStage

    start = time.monotonic()
    stage = ClusterStage.from_settings(settings_path)
    result = stage.run(read_bundle(bundle_path))
    elapsed = time.monotonic() - start
    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # ru_maxrss is in bytes on macOS and in kilobytes on Linux.
    maxrss_mb = maxrss / 2**20 if sys.platform == "darwin" else maxrss / 1024
    print(json.dumps({"stage_s": round(elapsed, 2), "ru_maxrss_mb": round(maxrss_mb, 1),
                      "groups": len(result["groups"]), "clusters": len(result["clusters"]),
                      "threads": result["settings"]["encoder"].get("threads")}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
