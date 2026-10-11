"""Install lines in the README name a real, current version of a model (feature 013)."""

from __future__ import annotations

import re
from pathlib import Path

from mobility_model_zoo.release.registry import Registry, parse_version

ROOT = Path(__file__).resolve().parents[2]
LINE = re.compile(
    r'pip install "mobility-model-zoo\[(?P<extra>[a-z,]+)\] @ git\+https://github\.com/'
    r'mhabedank/mobility-model-zoo@(?P<model>[a-z0-9-]+)/v(?P<version>[0-9.]+)"'
)


def readme_lines() -> list[re.Match[str]]:
    return list(LINE.finditer((ROOT / "README.md").read_text(encoding="utf-8")))


def test_the_readme_shows_an_install_line():
    assert readme_lines(), "the README quickstart lost its install line"


def test_install_lines_name_a_version_with_a_record_and_do_not_lag_behind_a_release():
    reg = Registry(ROOT)
    for m in readme_lines():
        name, version = m["model"], m["version"]
        assert reg.record_path(name, version).exists(), (
            f"README names {name} v{version}: no release record"
        )
        published = reg.published_versions(name)
        newest = max(published, key=parse_version) if published else None
        assert newest is None or parse_version(version) >= parse_version(newest), (
            f"README names {name} v{version}, but v{newest} is published"
        )


def test_install_lines_name_the_extra_of_the_model_runtime():
    reg = Registry(ROOT)
    for m in readme_lines():
        expected = "edge" if reg.runtime(reg.model_raw(m["model"])) == "mcu" else "text"
        assert m["extra"] == expected, (
            f"README line for {m['model']} names [{m['extra']}], not [{expected}]"
        )
