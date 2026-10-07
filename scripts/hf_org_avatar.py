"""Generate a Hugging Face organization avatar candidate through OpenRouter.

Usage: uv run python scripts/hf_org_avatar.py <model> <out.png> "<prompt>"
Reads OPENROUTER_API_KEY from the environment and prints the cost OpenRouter reports.
"""

import base64
import json
import os
import sys
import urllib.request

model, out, prompt = sys.argv[1:4]
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/chat/completions",
    data=json.dumps(
        {
            "model": model,
            "modalities": ["image", "text"],
            "usage": {"include": True},
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode(),
    headers={
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "Content-Type": "application/json",
    },
)
resp = json.load(urllib.request.urlopen(req, timeout=180))
images = resp["choices"][0]["message"].get("images", [])
if not images:
    sys.exit("no image returned")
with open(out, "wb") as f:
    f.write(base64.b64decode(images[0]["image_url"]["url"].split(",", 1)[1]))
print(out, "cost:", resp.get("usage", {}).get("cost"))
