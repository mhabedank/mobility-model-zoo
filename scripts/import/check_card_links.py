"""Check every link in the published scout-large cards (feature 005, SC-003).

    uv run python scripts/import/check_card_links.py [--versions 0.1.0 0.1.1 0.1.2]
"""

from __future__ import annotations

import argparse
import re
import sys

import httpx

REPO = "mobility-model-zoo/scout-large"


def links(card: str) -> list[str]:
    """Web links of a card; pip install URLs (`git+https://…@tag`) are not web pages."""
    found = re.findall(r"(?<!git\+)https?://[^\s)\"'<>\]{}]+", card)
    return sorted({m.rstrip(").,") for m in found})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", nargs="+", default=["0.1.0", "0.1.1", "0.1.2"])
    args = ap.parse_args(argv)
    broken = []
    with httpx.Client(follow_redirects=True, timeout=30,
                      headers={"User-Agent": "mobility-model-zoo-link-check"}) as client:
        for version in args.versions:
            card = client.get(f"https://huggingface.co/{REPO}/raw/v{version}/README.md").text
            for url in links(card):
                try:
                    status = client.head(url).status_code
                    if status >= 400:
                        status = client.get(url).status_code
                except httpx.HTTPError as exc:
                    status = f"error {exc.__class__.__name__}"
                if status not in (200, 202):  # 202: accepted by a bot-protection layer
                    broken.append(f"v{version}: {url} -> {status}")
            print(f"v{version}: {len(links(card))} links checked")
    for line in broken:
        print("BROKEN", line, file=sys.stderr)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
