# PlatformIO pre-script: generate lib/modelzoo from the bench models before compiling.
# The sources are build output (not committed). Models: reference models, CUSTOM_DIR and the .npz files
# listed in $MMZ_EDGE_MODELS (see mobility_model_zoo.edge.bench.reference_models.ensure_sources).
import os
import subprocess

Import("env")  # noqa: F821  (SCons global)

root = os.path.abspath(os.path.join(env["PROJECT_DIR"], "..", ".."))  # noqa: F821
python = os.environ.get("MMZ_PYTHON", "uv run python").split()
subprocess.run(
    [*python, "-m", "mobility_model_zoo.edge.bench.reference_models", "--ensure"], cwd=root, check=True
)
