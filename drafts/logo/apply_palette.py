"""Write the checked palette into the worktree's tokens.css, generated from the same values."""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from palette import DARK, LIGHT  # noqa: E402

WT = pathlib.Path(sys.argv[1])
T = WT / "src/mobility_model_zoo/site/static/css/tokens.css"

ORDER = ["bg", "surface", "surface-2", "text", "muted", "border", "border-strong", "link",
         "link-hover", "focus", "accent", "on-accent", "mark", "code-bg", "job-bg", "job-ink",
         "pain-bg", "pain-ink", "gain-bg", "gain-ink", "s-a", "s-b", "s-c"]


def block(p: dict, indent: str) -> str:
    return "".join(f"{indent}--{k}:{p[k]};\n" for k in ORDER)


light = (
    "  color-scheme: light dark;\n"
    "  /* Feature 023: one identity, taken from the website imagery. Day print on paper.\n"
    "     The warm accent stays rare on purpose, so that it keeps meaning 'this matters';\n"
    "     links are a deep blue-green instead. */\n"
    + block(LIGHT, "  ")
    + "  /* The inks of the screenprint, shared by both schemes: plates and the mark are\n"
      "     printed surfaces, not page surfaces, and do not turn over with the scheme. */\n"
      "  --poster-navy: #062544;\n"
      "  --poster-cream: #FBEED0;\n"
      "  --poster-mint: #A5DBC6;\n"
      "  --poster-orange: #ED9B20;\n"
      "  /* The mark does turn over: dark ground on paper, paper ground on dark. */\n"
      "  --mark-ground: var(--poster-navy);\n"
      "  --mark-ink: var(--poster-cream);\n"
      "  --mark-accent: var(--poster-orange);\n"
)
dark = (
    "    /* Night print: the same inks, the paper turned over. */\n"
    + block(DARK, "    ")
    + "    --mark-ground: var(--poster-cream);\n"
      "    --mark-ink: var(--poster-navy);\n"
)

s = T.read_text(encoding="utf-8")
s = re.sub(r"(:root \{\n).*?(\n\})", lambda m: m.group(1) + light.rstrip("\n") + m.group(2), s,
           count=1, flags=re.S)
s = re.sub(r"(@media \(prefers-color-scheme: dark\) \{\n  :root \{\n).*?(\n  \}\n\})",
           lambda m: m.group(1) + dark.rstrip("\n") + m.group(2), s, count=1, flags=re.S)
assert "--poster-navy" in s and s.count("--bg:") == 2, "replacement did not land"
assert "brand-blue" not in s, "the dead brand tokens should be gone"
T.write_text(s, encoding="utf-8")
print(f"tokens.css written, {len(ORDER)} tokens per scheme")
