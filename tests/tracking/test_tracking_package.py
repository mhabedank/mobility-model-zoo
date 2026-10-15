"""The tracking package imports nothing heavy at import time (feature 017, FR-011)."""

import subprocess
import sys


def test_importing_tracking_does_not_import_mlflow():
    code = (
        "import sys, mobility_model_zoo.tracking as t; "
        "assert 'mlflow' not in sys.modules, 'mlflow imported eagerly'; "
        "assert 'datasets' in t.EXPERIMENTS"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
